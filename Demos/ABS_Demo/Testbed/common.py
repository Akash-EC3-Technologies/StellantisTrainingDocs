"""
Shared helpers for the testbed (message building/checksum).
"""
import can, time, itertools, random
from typing import Iterable

CAN_CHANNEL = "can0"              # SocketCAN interface name
CMD_CAN_ID = 0x180                # Brake_Req_Level
HEARTBEAT_CAN_ID = 0x280          # ABS heartbeat
CMD_PERIOD_S = 0.100              # nominal 100 ms producer period (info only)
HEARTBEAT_PERIOD_S = 0.200         # 1000 ms
TIMEOUT_S = 0.500                 # 500 ms without valid command -> safe state
RANGE_FAULT_HOLD_S = 0.500         # 500 ms latch window for Range/Chk faults

PWM_FREQ_HZ = 500                 # demo LED PWM target
GPIO_CHIP = "/dev/gpiochip0"      # adjust as needed
GPIO_LINE = 17                    # adjust to your LED GPIO offset

def make_checksum(level: int, counter: int) -> int:
    return (0xFF - ((int(level) + (int(counter) & 0x0F)) & 0xFF)) & 0xFF

def build_cmd(level: int, counter: int, bad_checksum=False) -> can.Message:
    level = max(0, min(255, int(level)))
    counter &= 0x0F
    cks = make_checksum(level, counter)
    if bad_checksum:
        cks ^= 0x5A  # corrupt
    data = bytearray(8)
    data[0] = level & 0xFF
    data[1] = counter
    data[2] = cks
    # bytes 3..7 remain 0
    return can.Message(arbitration_id=CMD_CAN_ID, is_extended_id=False, data=data)
