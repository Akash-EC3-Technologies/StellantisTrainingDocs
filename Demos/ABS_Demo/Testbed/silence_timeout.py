"""
Send for a while and then be silent to trigger timeout.
"""
import time, can
from common import build_cmd, CMD_PERIOD_S, CAN_CHANNEL, TIMEOUT_S

def main():
    bus = can.Bus(interface="socketcan", channel=CAN_CHANNEL)
    period = CMD_PERIOD_S # 100ms
    counter = 0
    # Run test for 2 seconds
    t_end = time.monotonic() + 2
    while time.monotonic() < t_end:
        bus.send(build_cmd(50, counter))
        counter = (counter + 1) & 0x0F
        time.sleep(period)
    print("Silencing bus for 0.08 s...")
    time.sleep(TIMEOUT_S+0.2)  # > 500 ms
    # Resume
    for _ in range(20):
        bus.send(build_cmd(60, counter))
        counter = (counter + 1) & 0x0F
        time.sleep(period)
    bus.shutdown()
    print("Done.")

if __name__ == "__main__":
    main()
