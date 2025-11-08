# Raspberry Pi LED/Button Validation Test

This document describes how to validate the behavior of the `led_button.c` application running on a **Device Under Test (DUT)** Raspberry Pi using a **Test Bed** Raspberry Pi running a **pytest** validation script with **libgpiod**.

## Overview of the Test Setup

- **Device Under Test (DUT):**
  - Runs `led_button.c`
  - Controls an **LED** on **GPIO 17**
  - Reads a **Button** input on **GPIO 27** (default pull-up)
  - Behavior:  
    - Button **released** → LED **off**  
    - Button **pressed (pulled low)** → LED **on**

- **Test Bed Raspberry Pi:**
  - Runs `pytest` with **libgpiod** Python bindings.
  - Simulates **button presses** on the DUT by driving GPIO lines.
  - Reads back the **LED state** to confirm correct behavior.

## Dependencies (Test Bed Raspberry Pi)

Make sure your **Test Bed** Pi has the following installed:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-pytest python3-libgpiod
```

You can verify that your GPIO chip is visible with:

```bash
gpiodetect
# Example output:
# gpiochip0 [pinctrl-bcm2711] (58 lines)
```

## Pin Connections Between DUT and Test Bed

Both Raspberry Pis must share a **common ground**.

|           Signal | DUT (Device Under Test) | Test Bed    | Direction      | Description                     |
| ---------------: | ----------------------- | ----------- | -------------- | ------------------------------- |
|   **LED output** | GPIO 17                 | GPIO 6      | DUT → Test Bed | Test Bed senses LED state       |
| **Button input** | GPIO 27                 | GPIO 5      | Test Bed → DUT | Test Bed simulates button press |
|       **Ground** | Any GND pin             | Any GND pin | —              | Shared ground reference         |

**Important:**

* Use **1 kΩ series resistors** on both GPIO lines (LED sense and button drive) to protect both boards.
* Ensure **both Pis share ground** — without it, logic levels won’t reference correctly.
* Button input on DUT is **internally pulled up** by software in `led_button.c`.

## Instructions to Run the Test

### 1. Prepare the DUT

1. Compile and run `led_button.c` on the DUT:

   ```bash
   gcc -o led_button led_button.c -lgpiod
   ```

2. Run the app:

   ```bash
   sudo ./led_button
   ```

   The app will loop, monitoring GPIO 27 and controlling the LED on GPIO 17.

### 2. Prepare the Test Bed

1. Connect the GPIO pins as described above.
2. Run pytest:
   ```bash
   pytest
   ```

   Expected output (example):

   ``` text
   1 passed in 2.1s
   ```

## Expected Behavior During Test

| Test Step      | Test Bed Action         | Expected DUT Behavior | Expected Test Result |
| -------------- | ----------------------- | --------------------- | -------------------- |
| Release (idle) | Test Bed pin high-Z     | Button pulled high    | LED OFF (0)          |
| Press          | Test Bed drives LOW     | Button reads low      | LED ON (1)           |
| Release again  | Test Bed back to high-Z | Button pulled high    | LED OFF (0)          |

The pytest will automatically perform all these steps and assert that the LED changes correctly.

## 🧯 Troubleshooting

| Symptom                                        | Possible Cause                                      | Fix                                                                  |
| ---------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------- |
| `PermissionError` or `Operation not permitted` | User doesn’t have access to `/dev/gpiochip0`        | Run pytest with `sudo`                                               |
| Test always fails / LED never toggles          | GPIOs not wired correctly                           | Check pin numbers and connections                                    |
| Test reads wrong values (always 0 or 1)        | No shared ground between Pis                        | Ensure GND ↔ GND connection                                          |
| LED turns on permanently                       | Wrong wiring or pull-up/down misconfiguration       | Verify that the DUT’s button pin is configured as input with pull-up |
| `gpiod: No such file or directory`             | libgpiod not installed                              | `sudo apt install python3-libgpiod`                                  |
| LED never lights                               | Wrong resistor placement or LED polarity            | Check that LED anode is on GPIO17, cathode on GND                    |
| GPIO numbering confusion                       | Using physical pin numbers instead of BCM numbering | Use BCM numbering (e.g. GPIO 17 = physical pin 11)                   |

---

## Optional Configuration

You can override default GPIOs and timing without editing the script:

```bash
export TB_GPIO_PRESS=22        # change button drive pin
export TB_GPIO_SENSE=23        # change LED sense pin
export SETTLE_S=0.2            # wait 200ms between actions
export RETRIES=10              # increase sampling retries
pytest
```

## Summary

| Role     | Component             | GPIO Function                                             |
| -------- | --------------------- | --------------------------------------------------------- |
| DUT      | `led_button.c`        | LED = GPIO 17 (output), Button = GPIO 27 (input, pull-up) |
| Test Bed | `pytest` + `libgpiod` | Simulates press via GPIO 5, reads LED via GPIO 6          |

When correctly wired and configured, the pytest script will:

* Confirm the LED turns **ON when button pressed (low)**
* Confirm the LED turns **OFF when button released (high)**

and return `1 passed` when the DUT behaves as expected.
