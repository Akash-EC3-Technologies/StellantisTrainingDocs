# Headlamp Switch — HIL Validation (Automotive V&V Demo)

This is a demonstration of an Automotive V&V workflow for a simple Headlamp Switch requirement using two Raspberry Pis (one DUT, one Test Bed).

## Overview

This demo validates a **Headlamp Controller** running on a Raspberry Pi (**DUT**) using another Raspberry Pi as a **Test Bed**. It exercises a realistic Automotive V&V flow: **requirements → implementation → tests → logs → analysis → traceability**.

- **DUT (Device Under Test):** `headlamp_controller.c` (libgpiod)
- Input: **GPIO 27** (Headlamp switch, pull-up; pressed = GND)
- Output: **GPIO 17** (Headlamp output; 1 = ON)
- Behavior: Debounced switch controls headlamp with bounded latency
- **Test Bed:** Python `pytest` + `libgpiod` drives the switch line and reads the output line.
- **Monitor & Analyzer:** CSV logger + post-run analyzer to assert timing requirements.

## Hardware Wiring
- **Common GND:** DUT GND ↔ TB GND
- **Switch drive (Test Bed → DUT):** TB **GPIO 5** —1 kΩ→ DUT **GPIO 27**
- **Headlamp sense (DUT → Test Bed):** DUT **GPIO 17** —1 kΩ→ TB **GPIO 6**

## Software Dependencies
### DUT
```bash
sudo apt update
sudo apt install -y libgpiod-dev
```

### Test Bed
```bash
sudo apt update
sudo apt install -y python3 python3-pytest python3-libgpiod
```

## Build & Run (DUT)

On **DUT** Raspberry pi, build and run the headlamp_controller.c

```bash
gcc -O2 -Wall -o ./DUT/headlamp_controller ./DUT/headlamp_controller.c -lgpiod
sudo ./DUT/headlamp_controller
```

## Verification and Validation (Test Bed)

### Monitor and Log Activity


```bash
# record GPIO events while you operate the switch from pytest or manually
python3 ./tools/monitor.py --line 27:SWITCH --line 17:LAMP --debounce_ms 2 --out gpio_log.csv
```

### Run HIL Tests

On **Test Bed** Raspberry pi, run the pytest to check if everything is functional 

```bash
# optional pin overrides (defaults match wiring above)
# export TB_GPIO_PRESS=5
# export TB_GPIO_SENSE=6
pytest -q ./tests/test_headlamp_controller.py
```

### Analyze Logs

On **Test Bed** Raspberry pi, Analyse test results to check if behaviour matchs the requirement spec
```bash
# analyze for compliance with requirements
python3 tests/analyze_headlamp_log.py gpio_log.csv
```
