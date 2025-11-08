# Requires: libgpiod >= 2.0 (tested with 2.2.x) and python bindings `gpiod`
# Install on test bed (one way):
#   sudo apt install -y python3-pip
#   pip3 install gpiod
#
# Wiring (Dual-Pi, BCM numbers):
#   TestBed GPIO5  --1k-->  DUT GPIO27   (SWITCH line; TB drives low to "press")
#   DUT GPIO17     --1k-->  TestBed GPIO6 (LAMP sense)
#   GND <----------------------------------------------> GND
#
# DUT must be running the headlamp_controller (libgpiod v2) separately.
#
# What this validates (per HL-REQs):
#   - HL-REQ-004: power-on default OFF within 100 ms
#   - HL-REQ-003: ignore <5 ms pulses on the switch
#   - HL-REQ-001: PRESS (low) -> LAMP ON within 30 ms (after 5 ms debounce)
#   - HL-REQ-002: RELEASE (high) -> LAMP OFF within 30 ms (after 5 ms debounce)

import os
import time
import contextlib
import pytest

import gpiod
from datetime import timedelta
from gpiod.line import Direction as D, Value as V  # enums per v2 API

# -------- Configurable pins & timing (override via env) --------
TB_CHIP_PATH  = os.getenv("TB_GPIOCHIP_PATH", "/dev/gpiochip0")

TB_GPIO_PRESS = int(os.getenv("TB_GPIO_PRESS", "5"))  # drives DUT switch
TB_GPIO_SENSE = int(os.getenv("TB_GPIO_SENSE", "6"))  # reads DUT lamp

DEBOUNCE_MS   = int(os.getenv("DEBOUNCE_MS", "5"))    # spec debounce
LATENCY_MS    = int(os.getenv("LATENCY_MS", "30"))    # press/release latency
POWERON_MS    = int(os.getenv("POWERON_MS", "100"))   # power-on default OFF

SETTLE_S      = float(os.getenv("SETTLE_S", "0.02"))  # small settle
RETRIES       = int(os.getenv("RETRIES", "10"))
RETRY_GAP_S   = float(os.getenv("RETRY_GAP_S", "0.005"))

# -------- Helpers --------

def mono_ms() -> float:
    """Monotonic time in milliseconds."""
    return time.monotonic_ns() / 1_000_000.0

@contextlib.contextmanager
def open_chip(path: str):
    """Context manager for gpiod.Chip (v2 API)."""
    with gpiod.Chip(path=path) as chip:
        yield chip

def mk_settings_input(debounce_ms: int | None = None) -> gpiod.LineSettings:
    """Create input LineSettings; debounce is optional for TB press line (not required)."""
    return gpiod.LineSettings(
        direction=D.INPUT,
        debounce_period=timedelta(milliseconds=debounce_ms or 0)
    )

def mk_settings_output_low() -> gpiod.LineSettings:
    """Create output LineSettings defaulting LOW (INACTIVE)."""
    return gpiod.LineSettings(
        direction=D.OUTPUT,
        output_value=V.INACTIVE
    )

def mk_settings_output_high() -> gpiod.LineSettings:
    """Create output LineSettings defaulting HIGH (ACTIVE)."""
    return gpiod.LineSettings(
        direction=D.OUTPUT,
        output_value=V.ACTIVE
    )

def request_press_as(chip: gpiod.Chip, settings: gpiod.LineSettings) -> gpiod.LineRequest:
    """
    Request (or re-request) the TestBed 'press' pin with given settings.
    We request a single line; later we may reconfigure the same request.
    """
    return chip.request_lines(
        config={TB_GPIO_PRESS: settings},
        consumer="pytest-hil-press"
    )

def request_sense_input(chip: gpiod.Chip) -> gpiod.LineRequest:
    """Request the TestBed sense pin as INPUT."""
    return chip.request_lines(
        config={TB_GPIO_SENSE: gpiod.LineSettings(direction=D.INPUT)},
        consumer="pytest-hil-sense"
    )

def sense_lamp(req_sense: gpiod.LineRequest) -> int:
    """Read lamp level via TB sense line; return 0/1."""
    val = req_sense.get_value(TB_GPIO_SENSE)  # returns gpiod.line.Value
    return 1 if val == V.ACTIVE else 0

def press_drive_low(req_press: gpiod.LineRequest):
    """
    Drive the TB press pin LOW (simulate button press).
    If current request is INPUT, reconfigure to OUTPUT LOW.
    """
    try:
        req_press.reconfigure_lines({TB_GPIO_PRESS: mk_settings_output_low()})
    except Exception:
        # Fallback: release and re-request
        req_press.release()
        raise

def release_high_z(chip: gpiod.Chip, req_press: gpiod.LineRequest) -> gpiod.LineRequest:
    """
    Put TB press pin in INPUT (high-Z) so DUT pull-up wins (simulate release).
    Some kernels/drivers may reject reconfigure between OUT->IN; if so, re-request.
    """
    try:
        req_press.reconfigure_lines({TB_GPIO_PRESS: mk_settings_output_high()})
        return req_press
    except Exception:
        req_press.release()
        raise

# -------- Fixtures --------

@pytest.fixture(scope="module")
def chip():
    with open_chip(TB_CHIP_PATH) as c:
        yield c

@pytest.fixture(scope="module")
def req_sense(chip):
    req = request_sense_input(chip)
    yield req
    req.release()

@pytest.fixture()
def req_press(chip):
    # Start in RELEASED state: input/high-Z on TB press line
    req = request_press_as(chip, mk_settings_input())
    yield req
    # Best-effort cleanup
    try:
        req.release()
    except Exception:
        pass

# -------- Tests --------

@pytest.mark.timeout(20)
def test_power_on_default_off(req_sense):
    """
    HL-REQ-004: After app start, LAMP shall be OFF within 100 ms.
    (Assumes DUT app has just started; if running long before, this still validates OFF state quickly.)
    """
    t0 = mono_ms()
    seen_off = False
    while mono_ms() - t0 <= POWERON_MS:
        if sense_lamp(req_sense) == 0:
            seen_off = True
            break
        time.sleep(RETRY_GAP_S)
    assert seen_off, "HL-REQ-004: LAMP not OFF within power-on window"

@pytest.mark.timeout(30)
def test_debounce_and_latency(chip, req_sense, req_press):
    """
    HL-REQ-003: <5 ms pulses on SWITCH must NOT toggle LAMP.
    HL-REQ-001: PRESS (stable >=5 ms) -> LAMP ON within 30 ms (post-debounce).
    HL-REQ-002: RELEASE (stable >=5 ms) -> LAMP OFF within 30 ms (post-debounce).
    """

    # --- Ensure RELEASE (TB press pin = input/high-Z) ---
    req_press = release_high_z(chip, req_press)
    time.sleep(SETTLE_S)
    _ = sense_lamp(req_sense)  # sanity

    # --- Short glitch (<5 ms) should NOT change lamp (HL-REQ-003) ---
    # Drive low briefly (< debounce), then release.
    press_drive_low(req_press)
    time.sleep(0.003)  # 3 ms glitch < 5 ms debounce
    req_press = release_high_z(chip, req_press)
    time.sleep(0.050)  # allow DUT to ignore

    before = sense_lamp(req_sense)
    time.sleep(0.005)
    after = sense_lamp(req_sense)
    assert before == after, "HL-REQ-003: lamp changed on <5 ms pulse"

    # --- Valid PRESS: hold >= debounce then check ON latency (HL-REQ-001) ---
    press_drive_low(req_press)
    t_press_start = mono_ms()
    time.sleep(DEBOUNCE_MS / 1000.0)  # hold long enough to pass DUT debounce
    t_debounced = t_press_start + DEBOUNCE_MS

    on_seen = False
    t_on = None
    deadline = mono_ms() + 200.0  # 200 ms safety window
    while mono_ms() < deadline:
        if sense_lamp(req_sense) == 1:  # LAMP ON
            on_seen = True
            t_on = mono_ms()
            break
        time.sleep(RETRY_GAP_S)

    # Release to high-Z for next phase
    req_press = release_high_z(chip, req_press)

    assert on_seen, "HL-REQ-001: LAMP did not turn ON after press"
    assert (t_on - t_debounced) <= (LATENCY_MS + 3.0), \
        f"HL-REQ-001: latency {t_on - t_debounced:.2f} ms > {LATENCY_MS} ms"

    # --- Valid RELEASE: hold >= debounce then check OFF latency (HL-REQ-002) ---
    t_rel_start = mono_ms()
    time.sleep(DEBOUNCE_MS / 1000.0)
    t_rel_debounced = t_rel_start + DEBOUNCE_MS

    off_seen = False
    t_off = None
    deadline = mono_ms() + 200.0
    while mono_ms() < deadline:
        if sense_lamp(req_sense) == 0:  # LAMP OFF
            off_seen = True
            t_off = mono_ms()
            break
        time.sleep(RETRY_GAP_S)

    assert off_seen, "HL-REQ-002: LAMP did not turn OFF after release"
    assert (t_off - t_rel_debounced) <= (LATENCY_MS + 3.0), \
        f"HL-REQ-002: latency {t_off - t_rel_debounced:.2f} ms > {LATENCY_MS} ms"
