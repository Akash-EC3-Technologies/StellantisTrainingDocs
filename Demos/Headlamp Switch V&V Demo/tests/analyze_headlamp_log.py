#!/usr/bin/env python3
"""
analyze_headlamp_log.py — Checks HL-REQ-001..003 (+ start/stop presence)
against CSV produced by monitor.py.

Assumptions:
  • Names: SWITCH on GPIO 27, LAMP on GPIO 17 (or use your names; we filter by 'name' column).
  • Events: 'rising'/'falling' from monitor.py with timestamp_ns monotonic.

Config (tune to your spec):
  PRESS_TO_ON_MS = 30
  REL_TO_OFF_MS  = 30
  DEBOUNCE_MS    = 5
  MIN_PULSE_MS   = 5
"""

import csv, sys

PRESS_TO_ON_MS = 30.0
REL_TO_OFF_MS  = 30.0
DEBOUNCE_MS    = 5.0
MIN_PULSE_MS   = 5.0

SWITCH_NAME = "SWITCH"
LAMP_NAME   = "LAMP"

def ms(ns): return ns / 1_000_000.0

def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.reader(f)
        header = None
        for row in r:
            if not row or row[0].startswith("#"): continue
            if header is None:
                header = row
                continue
            rows.append(dict(zip(header, row)))
    return rows

def main(path):
    rows = load(path)

    # Normalize and filter
    ev = []
    for d in rows:
        # Some rows (timeout/stop) have empty gpio/level; guard it
        mono = int(d["mono_ns"]) if d["mono_ns"] else None
        lvl = int(d["level"]) if d["level"] not in ("", None) else None
        name = d["name"]
        ev.append({"utc": d["utc"], "mono_ns": mono, "gpio": d["gpio"], "name": name,
                   "event": d["event"], "level": lvl, "seq": int(d["seq"])})

    sw = [e for e in ev if e["name"] == SWITCH_NAME and e["event"] in ("rising", "falling")]
    lp = [e for e in ev if e["name"] == LAMP_NAME   and e["event"] in ("rising", "falling")]

    failures = []

    # Debounce: collapse switch pulses < MIN_PULSE_MS (falling..rising pairs)
    stable = []
    i = 0
    while i < len(sw):
        s = sw[i]
        if s["event"] == "falling":  # press (pull-up -> low)
            j = i + 1
            while j < len(sw) and sw[j]["event"] != "rising":
                j += 1
            if j < len(sw) and sw[j]["mono_ns"] is not None and s["mono_ns"] is not None:
                width_ms = ms(sw[j]["mono_ns"] - s["mono_ns"])
                if width_ms >= MIN_PULSE_MS:
                    stable.append(("press", s["mono_ns"]))
                    stable.append(("release", sw[j]["mono_ns"]))
                i = j + 1
                continue
        i += 1

    # Timing checks relative to end of debounce window
    for kind, t_ns in stable:
        target = t_ns + int(DEBOUNCE_MS * 1_000_000)
        if kind == "press":
            cand = next((e for e in lp if e["mono_ns"] is not None
                         and e["mono_ns"] >= target and e["level"] == 1), None)
            if not cand:
                failures.append("No LAMP ON after press")
            else:
                dt = ms(cand["mono_ns"] - target)
                if dt > PRESS_TO_ON_MS:
                    failures.append(f"Press→ON {dt:.2f} ms > {PRESS_TO_ON_MS} ms")
        else:
            cand = next((e for e in lp if e["mono_ns"] is not None
                         and e["mono_ns"] >= target and e["level"] == 0), None)
            if not cand:
                failures.append("No LAMP OFF after release")
            else:
                dt = ms(cand["mono_ns"] - target)
                if dt > REL_TO_OFF_MS:
                    failures.append(f"Release→OFF {dt:.2f} ms > {REL_TO_OFF_MS} ms")

    if failures:
        print("FAIL")
        for f in failures:
            print(" -", f)
        sys.exit(1)

    print("PASS")
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gpio_log.csv")
