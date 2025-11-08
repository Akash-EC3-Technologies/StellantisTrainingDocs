# Raspberry Pi 4 — GPIO

Two small C applications using **libgpiod** on a Raspberry Pi 4:

1. **LED Blink** — blinks an LED on **GPIO 17**  
2. **LED Button** — drives the same LED on **GPIO 17** from a momentary push-button on **GPIO 27** (default pull-up; press = LED on, release = LED off)

## Introduction

These examples use the modern Linux GPIO character device interface via **libgpiod**. On Raspberry Pi 4, GPIOs are exposed via `/dev/gpiochip*` (typically `/dev/gpiochip0` for GPIO 0–31, which includes 17 and 27).

## Setup Instructions (libgpiod)

1. **Update packages**

```bash
sudo apt update
```

2. **Install libgpiod (headers + tools)**

```bash
sudo apt install -y libgpiod-dev gpiod
```

   This installs the development headers (`-dev`) for compiling and the command-line tools like `gpiodetect`, `gpioinfo`.

3. **Verify the GPIO chip is present**

```bash
gpiodetect
# Expect something like: gpiochip0 [pinctrl-bcm2711] (58 lines)
```

4. **(Optional) Basic sanity check**

```bash
gpioinfo | grep -E "line *17|line *27"
```

## LED Blink App

### Connections

* **LED:**

  * **Anode (+)** → **GPIO 17** (pin 11 on the 40-pin header) through a **current-limiting resistor** (e.g., 330 Ω).
  * **Cathode (–)** → **GND** (any ground pin).
* With this wiring, setting GPIO 17 **high (1)** turns the LED **ON**.

> GPIO 17 is physical pin **11**; GND nearby is pins **9**.

### Build (for `led_blink.c`)

```bash
gcc -o led_blink led_blink.c -lgpiod
```

### Run

```bash
sudo ./led_blink
```

### Expected Behavior

* The program prints status to the console and **toggles the LED every 1 second**:

  * “LED ON” (LED lights)
  * “LED OFF” (LED goes off)
* Runs indefinitely until you stop it (Ctrl+C).

---

## LED Button App

### Connections

* **LED:** same as above (GPIO 17 → resistor → LED anode; LED cathode → GND).
* **Button (momentary, normally open):**

  * One side → **GPIO 27** (pin 13)
  * Other side → **GND**
* Assumes **default pull-up** on the input line (so the line reads **1** when idle and **0** when pressed).
  Pressing the button connects GPIO 27 to GND → the code sees a **0** (pressed) and turns the LED **ON**.

> GPIO 27 is physical pin **13**.

### Build (for `led_button.c`)

```bash
gcc -o led_button led_button.c -lgpiod
```

### Run

```bash
sudo ./led_button
```

### Expected Behavior

* While the program runs:

  * **Button released (idle = pulled up = 1)** → **LED OFF**
  * **Button pressed (pulled to GND = 0)** → **LED ON**
* A small `usleep(100000)` (100 ms) reduces CPU usage and acts as a light debounce.

## Trobleshooting

* If you get “permission denied” on `/dev/gpiochip*`, run with `sudo` or join the `gpio` group (then log out/in).
* If `gpiodetect` shows multiple chips, `gpio17` and `gpio27` are on **gpiochip0** on Raspberry Pi 4.
* Use `gpioinfo` to inspect line ownership and direction if something doesn’t work.
* Ensure your LED is oriented correctly and the resistor is in series to protect the GPIO pin.
