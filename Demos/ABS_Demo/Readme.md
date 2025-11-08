# Demo — ABS ECU & Testbed Verification and Validation

### Overview

This demo simulates a **Brake Sensor ECU → ABS ECU** interaction over **CAN bus** between two Raspberry Pis.

* **Brake Sensor ECU** is simulated by the **Testbed Pi**, which transmits CAN messages.
* **ABS ECU** (on another Pi) receives these messages and publishes a **heartbeat (0x280)** with diagnostic **FaultBits**.
* The LED (PWM) output represents braking effort — but for automated testing, only the **FaultBits** are checked.

The demo illustrates **Verification and Validation (V&V)** principles applied to automotive CAN systems — focusing on:

* Functional behavior (checksum, range, timeout handling)
* Fault handling and recovery
* Timing, robustness, and heartbeat behavior

## ⚙️ Hardware Setup

| Component        | Description                                              |
| ---------------- | -------------------------------------------------------- |
| 2 × Raspberry Pi | One runs the **ABS ECU**, the other is the **Testbed**   |
| CAN interface    | MCP2515-based HAT board on each Pi              |
| LED (optional)   | Connected to ABS Pi GPIO (configured in `ABS/config.py`) |
| Common Ground    | Both Pis share GND for CAN and signal reference          |

**CAN Bus Wiring:**

```
CAN_H <-> CAN_H
CAN_L <-> CAN_L
GND   <-> GND
```

**Baud rate:** `125 kbps`

## Software & Tools Needed

### APT Packages (both Pis)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip can-utils
```

Optional:

```bash
sudo apt install -y git vim
```

### Python Virtual Environment Setup

```bash
# Create and activate venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
python3 -m pip install --upgrade pip
pip install python-can gpiod==2.2.3 pytest
```

> The `gpiod` package provides access to GPIO via **libgpiod v2** APIs.
> Only the ABS ECU Pi needs this for PWM output.

## CAN Interface Setup (both Pis)

Configure CAN at 125 kbps:

```bash
sudo ip link set can0 down || true
sudo ip link add dev can0 type can bitrate 125000
sudo ip link set can0 up
ip -details -statistics link show can0
```

Verify communication by running:

```bash
candump can0
```

## Directory Structure

```
ABS_Demo/
  ABS/             # ABS ECU service
    abs_main.py
    config.py
    ...
  Testbed/         # Test scripts & pytest suite
    test_abs_requirements.py
    conftest.py
  Requirements.md  # Functional & safety requirements
  Readme.md        # This file
```

## Running the Demo

### Start the ABS ECU (on the ABS Pi)

```bash
cd ABS_Demo/ABS
source ../venv/bin/activate
python3 abs_main.py
```

Expected console output:

```
INFO ABS ECU build=abs-ecu-0.1 CAN=can0 LED=/dev/gpiochip0/17
```

The ECU will:

* Listen for commands on CAN ID **0x180**
* Publish heartbeat frames on **0x280** every 200 ms

### Run the Test Suite (on the Testbed Pi)

```bash
cd ABS_Demo/Testbed
source ../venv/bin/activate
pytest -v
```

Each test automatically sends CAN commands to the ABS ECU, then listens for heartbeats to verify requirement compliance.

## Test Overview and Expected Results

| Test Name                                           | Linked Requirement | Description                                                               | Expected Result                                                                    |
| --------------------------------------------------- | ------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **test_heartbeat_presence_and_period**              | F-6                | Verifies heartbeat presence, period (~200 ms), and alive counter behavior | Heartbeat detected, consistent period, alive counter increments                    |
| **test_checksum_rejection_sets_and_clears_chkfail** | S-3                | Sends frames with invalid checksum                                        | `CHKFAIL` bit asserted briefly, then clears within 0.5 s after valid frames resume |
| **test_range_sets_and_clears_range_bit**            | S-2                | Sends out-of-range levels (>100)                                          | `RANGE` bit asserted, clears within 0.5 s after valid range resumes                |
| **test_timeout_asserts_and_recovers**               | S-1                | Stops messages for 0.5 s, then resumes                                    | `TIMEOUT` bit asserted after ~0.5 s silence, clears after next valid frame         |
| **test_counter_jump_non_latching**                  | S-4                | Introduces counter discontinuity (jump >1)                                | ECU logs warning internally, no new faults latched                                 |
| **test_no_false_faults_under_load**                 | P-4                | Floods CAN bus (~70% load) while sending valid messages                   | ECU continues heartbeat; no `RANGE` or `CHKFAIL` bits set                          |

## Interpreting Test Results

Example output:

```
$ pytest -v
test_abs_requirements.py::test_heartbeat_presence_and_period PASSED
test_abs_requirements.py::test_checksum_rejection_sets_and_clears_chkfail PASSED
test_abs_requirements.py::test_range_sets_and_clears_range_bit PASSED
test_abs_requirements.py::test_timeout_asserts_and_recovers PASSED
test_abs_requirements.py::test_counter_jump_non_latching PASSED
test_abs_requirements.py::test_no_false_faults_under_load PASSED
======================== 6 passed in 14.21s ========================
```

If a test fails, pytest shows which requirement failed, e.g.:

```
E AssertionError: CHKFAIL not observed after bad frames
```

## Traceability Summary

| Requirement ID | Test(s) Covering It                               | Pass Criteria                                 |
| -------------- | ------------------------------------------------- | --------------------------------------------- |
| **F-6**        | `test_heartbeat_presence_and_period`              | Heartbeat periodic & alive counter increments |
| **S-1**        | `test_timeout_asserts_and_recovers`               | TIMEOUT asserted & clears after valid frame   |
| **S-2**        | `test_range_sets_and_clears_range_bit`            | RANGE asserted & clears                       |
| **S-3**        | `test_checksum_rejection_sets_and_clears_chkfail` | CHKFAIL asserted & clears                     |
| **S-4**        | `test_counter_jump_non_latching`                  | Counter discontinuity tolerated               |
| **P-4**        | `test_no_false_faults_under_load`                 | No new faults under 70% bus load              |
