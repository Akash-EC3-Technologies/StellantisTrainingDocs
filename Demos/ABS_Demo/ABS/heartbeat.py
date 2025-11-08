import time
import logging
import threading
import can

log = logging.getLogger("ABS.Heartbeat")

class Heartbeat:
    def __init__(self, can_send_fn, can_id: int, period_s: float, *, daemon: bool = True):
        self._send = can_send_fn
        self._can_id = can_id
        self._period = float(period_s)
        self._alive = 0
        self._last = 0.0
        self.fault_bits = 0

        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None
        self._daemon = daemon
        self._lock = threading.Lock()

    def tick(self, now: float):
        """Send a heartbeat if the period has elapsed."""
        if (now - self._last) >= self._period:
            data = bytearray(8)
            data[0] = self._alive & 0xFF
            data[1] = self.fault_bits & 0xFF
            self._send(self._can_id, data)
            self._alive = (self._alive + 1) & 0xFF
            self._last = now

    def start(self):
        """Start the background heartbeat thread (idempotent)."""
        if self._thread and self._thread.is_alive():
            return  # already running

        self._stop_evt.clear()
        name = f"Heartbeat-{self._can_id:03X}"
        self._thread = threading.Thread(target=self._run, name=name, daemon=self._daemon)
        self._thread.start()
        log.debug("Started %s", name)

    def stop(self, timeout: float | None = None):
        """Signal the thread to stop and join it."""
        self._stop_evt.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)
        self._thread = None
        log.debug("Stopped Heartbeat %03X", self._can_id)

    def is_running(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())

    # ---------- Internal loop ----------
    def _run(self):
        """
        Background loop: call tick() and sleep until the next due time.
        Uses an Event wait to be responsive to stop().
        """
        try:
            while not self._stop_evt.is_set():
                now = time.monotonic()
                try:
                    with self._lock:
                        self.tick(now)
                except Exception:
                    log.exception("Heartbeat send failed")

                # sleep until the next due time, but wake early if stopping
                next_due = self._last + self._period
                sleep_for = max(0.0, next_due - time.monotonic())

                # Event.wait returns early if stop is requested
                # Use a tiny floor to avoid hot-spinning when period is ~0
                self._stop_evt.wait(max(0.001, sleep_for))
        finally:
            pass
