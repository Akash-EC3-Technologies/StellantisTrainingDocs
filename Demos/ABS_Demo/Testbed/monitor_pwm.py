"""
Measure PWM duty and frequency on a GPIO line using libgpiod v2.
Requires the LED/PWM signal to be wired to this Pi's input line.
"""
import argparse, time, statistics, gpiod
from gpiod.line import Direction, Edge, Bias, Clock
import common

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chip", default="/dev/gpiochip0")
    ap.add_argument("--line", type=int, default=common.GPIO_LINE, help="Line offset to sample")
    ap.add_argument("--window", type=float, default=1.0, help="Seconds per report")
    args = ap.parse_args()

    chip = gpiod.Chip(args.chip)
    settings = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH, bias=Bias.PULL_DOWN, event_clock=Clock.MONOTONIC)
    req = chip.request_lines(config={args.line: settings}, consumer="PWM_MON")

    print("timestamp_s, freq_hz, duty_pct, samples")
    t_start = time.monotonic()
    highs = []
    lows = []
    last_ts = None
    last_val = None

    try:
        while True:
            if not req.wait_edge_events(timeout=args.window):
                # periodic report even if no events
                print(f"{time.monotonic():.6f},0,0,0")
                continue
            events = req.read_edge_events()
            for ev in events:
                ts = ev.timestamp_ns / 1e9
                # we don't read the level; estimate durations between edges
                if last_ts is not None:
                    dt = ts - last_ts
                    # Alternate low/high estimates based on edge order
                    if last_val == "HIGH":
                        lows.append(dt)
                        last_val = "LOW"
                    else:
                        highs.append(dt)
                        last_val = "HIGH"
                # Detect edge type to initialize last_val
                if last_val is None:
                    last_val = "HIGH" if str(ev.event_type).endswith("RISING_EDGE") else "LOW"
                last_ts = ts

            # Periodic report
            now = time.monotonic()
            if (now - t_start) >= args.window:
                # Compute averages
                h = sum(highs)/len(highs) if highs else 0.0
                l = sum(lows)/len(lows) if lows else 0.0
                period = h + l
                if period > 0:
                    freq = 1.0 / period
                    duty = (h / period) * 100.0
                else:
                    freq = 0.0
                    duty = 0.0
                print(f"{now:.6f},{freq:.2f},{duty:.2f},{len(highs)+len(lows)}")
                highs.clear(); lows.clear()
                t_start = now
    except KeyboardInterrupt:
        pass
    finally:
        try:
            req.release()
        except Exception:
            pass
        chip.close()

if __name__ == "__main__":
    main()
