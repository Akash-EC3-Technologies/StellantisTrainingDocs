"""
Pytest fixtures & helpers for ABS ECU requirement tests using only CAN heartbeat fault bits.
Uses python-can / SocketCAN.
"""
import threading
import time
import queue
import can
import pytest

# ---- Constants ----
CAN_CHANNEL = "can0"              # SocketCAN interface name
CMD_CAN_ID = 0x180                # Brake_Req_Level
HEARTBEAT_CAN_ID = 0x280          # ABS heartbeat
CMD_PERIOD_S = 0.100              # nominal 100 ms producer period
HEARTBEAT_PERIOD_S = 0.200        # 200 ms heartbeat
TIMEOUT_S = 0.500                 # 500 ms without valid command -> safe state
RANGE_FAULT_HOLD_S = 0.500        # 500 ms latch window for Range/Chk faults

# ---- Fault bitfield ----
TIMEOUT_BIT = 1 << 0
CHKFAIL_BIT = 1 << 1
RANGE_BIT   = 1 << 2
BUSOFF_BIT  = 1 << 3

# ---- Helpers ----
def make_checksum(level: int, counter: int) -> int:
    """Checksum = 0xFF - ((Level + (Counter & 0x0F)) & 0xFF)."""
    return (0xFF - ((int(level) + (int(counter) & 0x0F)) & 0xFF)) & 0xFF

def build_cmd(level: int, counter: int, *, bad_checksum: bool=False) -> can.Message:
    """Build command frame to ABS ECU."""
    level = max(0, min(255, int(level)))
    ctr = counter & 0x0F
    cks = make_checksum(level, ctr)
    if bad_checksum:
        cks ^= 0x5A  # corrupt
    data = bytearray(8)
    data[0] = level & 0xFF
    data[1] = ctr
    data[2] = cks
    return can.Message(arbitration_id=CMD_CAN_ID, is_extended_id=False, data=data)

# ---- Heartbeat watcher ----
class HeartbeatWatcher:
    """Collect heartbeats (0x280) with timestamps in a background thread."""
    def __init__(self, bus: can.Bus, hb_id: int):
        self.bus = bus
        self.hb_id = hb_id
        self.q = queue.Queue()
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._run, daemon=True)
        self._thr.start()

    def _run(self):
        while not self._stop.is_set():
            msg = self.bus.recv(timeout=0.05)
            if msg is None:
                continue
            if msg.arbitration_id == self.hb_id and len(msg.data) >= 2:
                ts = time.monotonic()
                alive = msg.data[0]
                faults = msg.data[1]
                self.q.put((ts, alive, faults, msg))

    def get_many(self, min_count: int, timeout_s: float):
        """Return at least `min_count` heartbeats within timeout."""
        items = []
        t_end = time.monotonic() + timeout_s
        while len(items) < min_count and time.monotonic() < t_end:
            try:
                items.append(self.q.get(timeout=0.05))
            except queue.Empty:
                pass
        return items

    def get_until(self, predicate, timeout_s: float):
        """Return first heartbeat satisfying predicate(ts, alive, faults, msg)."""
        t_end = time.monotonic() + timeout_s
        while time.monotonic() < t_end:
            try:
                item = self.q.get(timeout=0.05)
                if predicate(*item):
                    return item
            except queue.Empty:
                pass
        return None

    def stop(self):
        self._stop.set()
        try:
            self._thr.join(timeout=1.0)
        except Exception:
            pass


# ---- Pytest fixtures ----
@pytest.fixture(scope="session")
def bus():
    """SocketCAN bus for tests (requires can0 up and ABS ECU running)."""
    b = can.Bus(interface="socketcan", channel=CAN_CHANNEL)
    yield b
    try:
        b.shutdown()
    except Exception:
        pass


@pytest.fixture()
def hb(bus):
    """Heartbeat watcher fixture (auto-stops after each test)."""
    watcher = HeartbeatWatcher(bus, HEARTBEAT_CAN_ID)
    yield watcher
    watcher.stop()


@pytest.fixture()
def fresh_counter():
    """Simple rolling counter generator 0..15."""
    ctr = 0
    def next_ctr():
        nonlocal ctr
        c = ctr
        ctr = (ctr + 1) & 0x0F
        return c
    return next_ctr
