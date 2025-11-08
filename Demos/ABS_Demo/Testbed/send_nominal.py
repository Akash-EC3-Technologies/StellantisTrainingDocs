"""
Nominal sweep & latency toggle generator.
"""
import time, can, itertools
from common import build_cmd, CMD_PERIOD_S, CAN_CHANNEL

def main():
    bus = can.Bus(interface="socketcan", channel=CAN_CHANNEL)
    period = CMD_PERIOD_S  # 100 ms
    counter = 0
    # Sweep
    for level in [0, 10, 50, 90, 100]:
        t_end = time.monotonic() + 0.6 # for each step run tests for 0.6 seconds
        while time.monotonic() < t_end:
            bus.send(build_cmd(level, counter))
            counter = (counter + 1) & 0x0F
            time.sleep(period)
    # Toggle for latency/jitter
    for _ in range(10):
        level = 10 if (_ % 2 == 0) else 90
        bus.send(build_cmd(level, counter))
        counter = (counter + 1) & 0x0F
        time.sleep(period*3)
    bus.shutdown()
if __name__ == "__main__":
    main()
