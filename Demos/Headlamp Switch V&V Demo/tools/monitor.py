#!/usr/bin/env python3
"""
monitor.py — GPIO edge-event logger

• Requests one or more input lines with BOTH edges + optional debounce.
• Uses wait_edge_events() and read_edge_events() to capture events.
• Writes auditable CSV with ISO UTC + monotonic_ns + gpio + name + event + level + seq.
• Adds heartbeat "timeout" rows when no events occur in the given interval.

Examples:
  python3 monitor.py --line 27:SWITCH --line 17:LAMP --debounce_ms 5 --out gpio_log.csv
"""

import argparse
import csv
import datetime as dt
import os
import sys
import time
from datetime import timedelta
import gpiod
from gpiod.line import Edge, Direction, Value

def now_iso_utc():
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()

def parse_lines(specs):
    """Parse CLI --line entries like '27:SWITCH' into [(offset:int, name:str), ...]."""
    out = []
    for s in specs:
        if ":" in s:
            n, name = s.split(":", 1)
            out.append((int(n), name))
        else:
            out.append((int(s), f"GPIO{s}"))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chip", default="/dev/gpiochip0", help="path to gpiochip (default: /dev/gpiochip0)")
    ap.add_argument("--line", action="append", required=True, help="BCM line spec, e.g. 27:SWITCH (repeatable)")
    ap.add_argument("--debounce_ms", type=int, default=0, help="debounce period (ms) to apply per line (kernel-side)")
    ap.add_argument("--timeout_ms", type=int, default=5000, help="poll timeout for heartbeat rows")
    ap.add_argument("--max_batch_events", type=int, default=16, help="max events to drain per read")
    ap.add_argument("--out", default="gpio_log.csv", help="output CSV path")
    args = ap.parse_args()

    lines = parse_lines(args.line)
    offsets = [o for (o, _) in lines]
    names_by_offset = {o: n for (o, n) in lines}

    # Build per-line settings: input + both edges + optional debounce
    line_settings = {}
    for off in offsets:
        ls = gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH)
        if args.debounce_ms > 0:
            # If the driver supports it, this will be applied; otherwise it may be ignored.
            ls.debounce_period = timedelta(milliseconds=args.debounce_ms)
        line_settings[off] = ls

    # Request all lines in one multi-line request (single event queue)
    with gpiod.Chip(path=args.chip) as chip, \
         chip.request_lines(config=line_settings, consumer="gpio-monitor") as req:

        # Open CSV and emit headers
        first = not os.path.exists(args.out)
        f = open(args.out, "a", newline="")
        w = csv.writer(f)
        if first:
            w.writerow([f"# started={now_iso_utc()} tool=monitor_v2.py version=2.0"])
            w.writerow(["utc", "mono_ns", "gpio", "name", "event", "level", "seq"])

        seq = 0

        # Initial snapshot (levels at start)
        for off in offsets:
            try:
                v = req.get_value(off)
                w.writerow([now_iso_utc(), time.monotonic_ns(), off, names_by_offset[off], "start",
                            1 if v == Value.ACTIVE else 0, seq]); seq += 1
            except Exception as e:
                w.writerow([now_iso_utc(), time.monotonic_ns(), off, names_by_offset[off], "start_err",
                            "", seq]); seq += 1
        f.flush()

        # Main event loop
        timeout_s = args.timeout_ms / 1000.0
        try:
            while True:
                # Wait for any edge; returns True if something is pending
                if req.wait_edge_events(timeout_s):
                    events = req.read_edge_events(args.max_batch_events)
                    for ev in events:
                        # ev has: line_offset, event_type, timestamp_ns
                        off = ev.line_offset
                        et = "rising" if ev.event_type.name.lower().startswith("rising") else "falling"
                        # Read current level right after event (best-effort)
                        try:
                            lev = req.get_value(off)
                            lev_i = 1 if lev == Value.ACTIVE else 0
                        except Exception:
                            lev_i = ""
                        w.writerow([now_iso_utc(), ev.timestamp_ns, off,
                                    names_by_offset.get(off, f"GPIO{off}"), et, lev_i, seq]); seq += 1
                    f.flush()
                else:
                    # Heartbeat timeout
                    w.writerow([now_iso_utc(), time.monotonic_ns(), "", "ALL", "timeout", "", seq]); seq += 1
                    f.flush()
        except KeyboardInterrupt:
            w.writerow([now_iso_utc(), time.monotonic_ns(), "", "ALL", "stop", "", seq]); seq += 1
        finally:
            f.flush(); f.close()

if __name__ == "__main__":
    sys.exit(main())
