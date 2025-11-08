import can, logging, threading, time
from typing import Optional, Callable

log = logging.getLogger("ABS.CAN")

class CanInterface:
    """
    Thin wrapper around python-can / SocketCAN.
    - Receives frames via a background thread calling a user callback.
    - Provides send() utility.
    """
    def __init__(self, channel: str):
        self.bus = can.interface.Bus(bustype="socketcan", channel=channel)
        self._rx_cb: Optional[Callable[[can.Message], None]] = None
        self._stop = threading.Event()
        self._thr = threading.Thread(target=self._rx_loop, name="can-rx", daemon=True)
        self._thr.start()

    def on_receive(self, callback: Callable[[can.Message], None]):
        self._rx_cb = callback

    def send(self, can_id: int, data: bytes, is_extended_id: bool=False):
        msg = can.Message(arbitration_id=can_id, is_extended_id=is_extended_id, data=data)
        self.bus.send(msg)

    def _rx_loop(self):
        while not self._stop.is_set():
            msg = self.bus.recv(timeout=0.01)  # 10 ms tick
            if msg is None:
                continue
            if self._rx_cb:
                try:
                    self._rx_cb(msg)
                except Exception as e:
                    log.exception("RX callback error: %s", e)

    def shutdown(self):
        self._stop.set()
        try:
            self._thr.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.bus.shutdown()
        except Exception:
            pass
