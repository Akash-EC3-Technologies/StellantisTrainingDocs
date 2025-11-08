"""
Alternate valid/invalid checksum frames.
"""
import time, can
from common import build_cmd, CAN_CHANNEL, CMD_PERIOD_S

def main():
    bus = can.Bus(interface="socketcan", channel=CAN_CHANNEL)
    period = CMD_PERIOD_S
    counter = 0
    for _ in range(20):
        # valid 70%
        bus.send(build_cmd(70, counter, bad_checksum=False))
        counter = (counter + 1) & 0x0F
        time.sleep(period)
        # invalid 20%
        bus.send(build_cmd(20, counter, bad_checksum=True))
        counter = (counter + 1) & 0x0F
        time.sleep(period)
    bus.shutdown()
    print("Done.")
    
if __name__ == "__main__":
    main()
