"""
Generate background traffic to reach target utilization (approx).
This is a rough userland generator; adjust --rate if needed.
"""
import argparse, time, can, random
import common

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--util", type=float, default=0.7, help="Target utilization 0..1 (approx)")
    ap.add_argument("--rate", type=float, default=None, help="Override frames/sec")
    args = ap.parse_args()

    # Approx: at 125 kbit/s, a classic 8B data frame ~ 130 bits on wire incl. stuff → ~961 fps @100%.
    # We'll aim for util*900 fps by default.
    fps = args.rate if args.rate else (max(1.0, args.util) * 600.0)
    period = 1.0 / fps

    bus = can.Bus(interface="socketcan", channel=common.CAN_CHANNEL)
    print(f"Sending ~{fps:.0f} fps background frames... Ctrl-C to stop.")
    next_t = time.monotonic()
    rid = 0
    try:
        while True:
            data = bytes(random.getrandbits(8) for _ in range(8))
            msg = can.Message(arbitration_id=0x300 + (rid % 0x100), is_extended_id=False, data=data)
            bus.send(msg)
            rid += 1
            next_t += period
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.monotonic()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
