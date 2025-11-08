import time, logging, struct
from logger_setup import setup_logging
import config
from checksum import verify_checksum
from faults import TIMEOUT, CHKFAIL, RANGE, BUSOFF
import pwm
from can_iface import CanInterface
from heartbeat import Heartbeat

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def parse_cmd_frame(data: bytes):
    """
    Byte0: Level (0..100)
    Byte1: RollingCounter (0..15)
    Byte2: Checksum
    """
    if len(data) < 3:
        return None
    level = data[0]
    counter = data[1] & 0x0F
    checksum = data[2]
    return level, counter, checksum

def main():
    log = setup_logging(config.LOG_LEVEL)
    log.info("ABS ECU build=%s CAN=%s LED=%s/%s", config.BUILD_ID, config.CAN_CHANNEL, config.GPIO_CHIP, config.GPIO_LINE)

    # PWM setup
    pwm.enable(0, 0, 500, 0)

    # CAN setup
    canif = CanInterface(config.CAN_CHANNEL)
    hb = Heartbeat(canif.send, config.HEARTBEAT_CAN_ID, config.HEARTBEAT_PERIOD_S)
    hb.start()
    # State
    last_valid_rx = 0.0
    last_counter = None
    range_fault_until = 0.0
    chk_fault_until = 0.0

    def rx(msg):
        nonlocal last_valid_rx, last_counter, range_fault_until, chk_fault_until
        now = time.monotonic()
        # Note: Using only standard frames
        if msg.arbitration_id != config.CMD_CAN_ID:
            return
        parsed = parse_cmd_frame(msg.data)
        if not parsed:
            return
        level, counter, checksum = parsed
        # Verify checksum
        from checksum import verify_checksum as vchk, make_checksum
        if not vchk(level, counter, checksum):
            chk_fault_until = now + config.RANGE_FAULT_HOLD_S
            return
        # Range clamp
        applied = clamp(level, 0, 100)
        if applied != level:
            range_fault_until = now + config.RANGE_FAULT_HOLD_S
        # Rolling counter discontinuity log (non-latching)
        if last_counter is not None:
            diff = (counter - last_counter) & 0x0F
            if diff not in (0,1):
                logging.getLogger("ABS").warning("Counter jump: %d -> %d", last_counter, counter)
        last_counter = counter
        # Apply duty
        pwm.set_duty_cycle(0,0,applied)
        last_valid_rx = now

    canif.on_receive(rx)

    try:
        while True:
            now = time.monotonic()
            # Timeout handling
            faults = 0
            if (now - last_valid_rx) > config.TIMEOUT_S:
                faults |= TIMEOUT
                pwm.set_duty_cycle(0,0,0)  # safe state
            # Transient faults
            if now < range_fault_until:
                faults |= RANGE
            if now < chk_fault_until:
                faults |= CHKFAIL
            # (BUSOFF would need can state read; omitted in this demo)
            hb.fault_bits = faults
            hb.tick(now)
            time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        hb.stop()
        canif.shutdown()
        pwm.disable(0,0)

if __name__ == "__main__":
    main()
