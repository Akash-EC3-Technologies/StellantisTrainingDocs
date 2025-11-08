# ABS ECU — Raspberry Pi 5 (Phase X)

## Purpose
ABS ECU daemon that:
- Listens for ultrasonic data on CAN (`can0`) with ID `0x100`.
- Applies a brake output expressed as a PWM percentage on Raspberry Pi hardware PWM via sysfs.
- Transmits braking info on CAN ID `0x200`.

## Files
- `abs_ecu.c`              — main C source (SocketCAN + sysfs PWM + CAN send).
- `build_and_run.sh`       — compile and run helper.
- `Functional_Requirement.md`
- `systemd/abs-ecu.service` — optional systemd unit (edit ExecStart path as needed).

## CAN protocol (used here)
- Ultrasonic (input) — CAN ID `0x100`, 8 bytes:
  - bytes 0..1 — distance_mm (big-endian uint16)
  - byte 2 — counter
  - byte 3 — status (0=OK,1=timeout,2=out_of_range)
  - bytes 4..6 reserved
  - byte 7 — CRC8 (poly 0x07) over bytes 0..6

- Brake info (output) — CAN ID `0x200`, 2 bytes:
  - byte0 — brake_state (0x00=OFF, 0x01=ON)
  - byte1 — brake_percent (0..100)

> Note: Brake info frame is kept short and simple (no CRC) because internal CAN bus is short and devices are trusted in this demo. You may add CRC or extended format later.

## PWM (sysfs) notes
- PWM sysfs path: `/sys/class/pwm/pwmchip<chip>/pwm<channel>/`
- The program will:
  - export the channel if needed,
  - set `period` (ns),
  - set `duty_cycle` (ns) according to percentage,
  - enable the channel.
- Default config uses `period_ns=1000000` (1 kHz). Adjust in CLI args.

## Build
```bash
gcc abs_ecu -o abs_ecu.c -Wall
```
## Run
```bash
sudo ./abs_ecu \
  --can can0 \
  --pwmchip 0 \
  --pwm 0 \
  --period 1000000 \
  --threshold 300 \
  --min-distance 50
```
