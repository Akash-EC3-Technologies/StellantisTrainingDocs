"""
pytest suite for ABS ECU verification using heartbeat FaultBits only.
Each test docstring lists the linked requirement IDs.

Run:
    pytest -q
"""
import time
import statistics
import threading
import pytest
import can

from conftest import (
    CMD_PERIOD_S, HEARTBEAT_PERIOD_S,
    TIMEOUT_S, RANGE_FAULT_HOLD_S,
    TIMEOUT_BIT, CHKFAIL_BIT, RANGE_BIT,
    build_cmd
)

HB_WAIT = HEARTBEAT_PERIOD_S * 6 + 0.5
MARGIN = 0.25  # seconds of timing slack for Linux scheduling


# ----------------------------------------------------------------------
# F-6: Heartbeat periodicity and alive counter
# ----------------------------------------------------------------------
def test_heartbeat_presence_and_period(bus, hb):
    """REQ: F-6 — Heartbeat 0x280 present, correct period, alive counter stable."""
    items = hb.get_many(min_count=6, timeout_s=HB_WAIT)
    assert len(items) >= 3, "No heartbeat frames received"
    periods = [items[i+1][0] - items[i][0] for i in range(len(items)-1)]
    avg = sum(periods) / len(periods)
    stdev = statistics.pstdev(periods) if len(periods) > 1 else 0.0
    assert 0.3 * HEARTBEAT_PERIOD_S <= avg <= 3.0 * HEARTBEAT_PERIOD_S, f"Unexpected heartbeat period {avg:.3f}s"
    assert stdev <= 0.5 * HEARTBEAT_PERIOD_S, f"Heartbeat jitter too high (stdev={stdev:.3f}s)"

    # Alive counter monotonic (mod 256)
    alive = [a for _, a, _, _ in items]
    for i in range(len(alive) - 1):
        diff = (alive[i+1] - alive[i]) & 0xFF
        assert diff in (0, 1), f"Alive counter jump: {alive[i]} -> {alive[i+1]}"


# ----------------------------------------------------------------------
# S-3: Checksum fault assertion & clearing
# ----------------------------------------------------------------------
def test_checksum_rejection_sets_and_clears_chkfail(bus, hb, fresh_counter):
    """REQ: S-3 — Bad checksum raises CHKFAIL and clears within hold window."""
    for _ in range(3):
        bus.send(build_cmd(70, fresh_counter()))
        time.sleep(CMD_PERIOD_S)

    # Burst of bad checksum frames
    for _ in range(5):
        bus.send(build_cmd(20, fresh_counter(), bad_checksum=True))
        time.sleep(CMD_PERIOD_S)

    asserted = hb.get_until(lambda ts, a, f, m: f & CHKFAIL_BIT, HEARTBEAT_PERIOD_S + MARGIN)
    assert asserted, "CHKFAIL not observed after bad frames"

    # Send valid frames to recover
    for _ in range(3):
        bus.send(build_cmd(50, fresh_counter()))
        time.sleep(CMD_PERIOD_S)

    cleared = hb.get_until(lambda ts, a, f, m: not (f & CHKFAIL_BIT),
                           RANGE_FAULT_HOLD_S + HEARTBEAT_PERIOD_S + MARGIN)
    assert cleared, "CHKFAIL did not clear within hold window"


# ----------------------------------------------------------------------
# S-2: Range fault assertion & clearing
# ----------------------------------------------------------------------
def test_range_sets_and_clears_range_bit(bus, hb, fresh_counter):
    """REQ: S-2 — Out-of-range (>100) sets RANGE and clears within hold window."""
    for _ in range(5):
        bus.send(build_cmd(130, fresh_counter()))
        time.sleep(CMD_PERIOD_S)

    asserted = hb.get_until(lambda ts, a, f, m: f & RANGE_BIT, HEARTBEAT_PERIOD_S + MARGIN)
    assert asserted, "RANGE bit not asserted"

    # Valid values to clear
    for _ in range(5):
        bus.send(build_cmd(80, fresh_counter()))
        time.sleep(CMD_PERIOD_S)

    cleared = hb.get_until(lambda ts, a, f, m: not (f & RANGE_BIT),
                           RANGE_FAULT_HOLD_S + HEARTBEAT_PERIOD_S + MARGIN)
    assert cleared, "RANGE bit did not clear"


# ----------------------------------------------------------------------
# S-1: Timeout assertion & recovery
# ----------------------------------------------------------------------
def test_timeout_asserts_and_recovers(bus, hb, fresh_counter):
    """REQ: S-1 — Timeout sets TIMEOUT bit and clears after valid frame."""
    for _ in range(5):
        bus.send(build_cmd(60, fresh_counter()))
        time.sleep(CMD_PERIOD_S)

    t_silence = time.monotonic()
    time.sleep(TIMEOUT_S + 0.05)

    asserted = hb.get_until(lambda ts, a, f, m: f & TIMEOUT_BIT, HEARTBEAT_PERIOD_S + MARGIN)
    assert asserted, "TIMEOUT not observed"
    latency = asserted[0] - t_silence
    assert latency >= TIMEOUT_S, f"Timeout asserted too early ({latency:.3f}s)"
    assert latency <= TIMEOUT_S + HEARTBEAT_PERIOD_S + MARGIN, f"Timeout asserted too late ({latency:.3f}s)"

    # Recovery
    bus.send(build_cmd(50, fresh_counter()))
    cleared = hb.get_until(lambda ts, a, f, m: not (f & TIMEOUT_BIT), HEARTBEAT_PERIOD_S + MARGIN)
    assert cleared, "TIMEOUT did not clear after recovery"


# ----------------------------------------------------------------------
# S-4: Rolling counter discontinuity
# ----------------------------------------------------------------------
def test_counter_jump_non_latching(bus, hb):
    """REQ: S-4 — Counter jump tolerated, no CHK/RANGE faults latched."""
    bus.send(build_cmd(10, 0))
    time.sleep(CMD_PERIOD_S)
    bus.send(build_cmd(20, 1))
    time.sleep(CMD_PERIOD_S)
    bus.send(build_cmd(30, 7))  # discontinuity

    observed = hb.get_many(3, timeout_s=HEARTBEAT_PERIOD_S * 2 + 0.5)
    for _, _, faults, _ in observed:
        assert not (faults & (CHKFAIL_BIT | RANGE_BIT)), "Unexpected CHK/RANGE due to counter jump"


# ----------------------------------------------------------------------
# P-4: Robustness under bus load
# ----------------------------------------------------------------------
def test_no_false_faults_under_load(bus, hb, fresh_counter):
    """REQ: P-4 — No RANGE/CHKFAIL under moderate background load."""
    stop = threading.Event()

    def background():
        fps = 600.0  # ~60–70% bus utilization
        period = 1.0 / fps
        next_t = time.monotonic()
        aid = 0x300
        while not stop.is_set():
            msg = can.Message(arbitration_id=aid, data=b"12345678", is_extended_id=False)
            try:
                bus.send(msg)
            except can.CanError:
                pass
            aid = 0x300 + ((aid + 1) & 0x7F)
            next_t += period
            time.sleep(max(0, next_t - time.monotonic()))

    t = threading.Thread(target=background, daemon=True)
    t.start()

    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        bus.send(build_cmd(80, fresh_counter()))
        hb_item = hb.get_until(lambda ts, a, f, m: True, HEARTBEAT_PERIOD_S + 0.2)
        assert hb_item, "Missing heartbeat under load"
        faults = hb_item[2]
        assert not (faults & (RANGE_BIT | CHKFAIL_BIT)), f"Unexpected fault bits under load: 0x{faults:02X}"
        time.sleep(CMD_PERIOD_S)

    stop.set()
    t.join(timeout=1.0)
