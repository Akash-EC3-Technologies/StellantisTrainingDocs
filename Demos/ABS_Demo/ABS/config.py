"""
ABS ECU configuration.
Edit GPIO line/chip as needed for your board.
"""
CAN_CHANNEL = "can0"              # SocketCAN interface name
CMD_CAN_ID = 0x180                # Brake_Req_Level
HEARTBEAT_CAN_ID = 0x280          # ABS heartbeat
CMD_PERIOD_S = 0.100              # nominal 100 ms producer period (info only)
HEARTBEAT_PERIOD_S = 0.200        # 200 ms
TIMEOUT_S = 0.500                 # 500 ms without valid command -> safe state
RANGE_FAULT_HOLD_S = 0.500        # 500 ms latch window for Range/Chk faults

PWM_FREQ_HZ = 500                 # demo LED PWM target
GPIO_CHIP = "/dev/gpiochip0"      # adjust as needed
GPIO_LINE = 17                    # adjust to your LED GPIO offset
ACTIVE_LOW = False                # set True if wiring requires

LOG_LEVEL = "INFO"                # DEBUG/INFO/WARNING
BUILD_ID = "abs-ecu-0.1"
