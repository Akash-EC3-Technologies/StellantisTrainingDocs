import socket
import threading
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 5005
DISTANCE_TIMEOUT = 1.0  # seconds

class DistanceReceiver:
    def __init__(self):
        self.distance_mm = None
        self.last_update = 0
        self.lock = threading.Lock()

        t = threading.Thread(target=self._listen, daemon=True)
        t.start()

    def _listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
        sock.settimeout(1.0)

        while True:
            try:
                data, _ = sock.recvfrom(128)
                s = data.decode("utf-8").strip()
                d = int(s)
                with self.lock:
                    self.distance_mm = d
                    self.last_update = time.time()
            except:
                pass

    def get_distance(self):
        with self.lock:
            if (time.time() - self.last_update) > DISTANCE_TIMEOUT:
                return None
            return self.distance_mm
