# Phase 1 — Raspberry Pi CAN Receiver

## Purpose
This component runs on the Raspberry Pi. It reads ultrasonic CAN frames (ID `0x100`) from the SocketCAN interface `can0`, validates the CRC8, logs messages to stdout, and forwards the parsed distance (in mm) to a local UDP endpoint `127.0.0.1:5005`. This UDP forwarding decouples the CAN receiver from the camera overlay process.

## Files in this folder
- `sensor_aggregator.c` — C source code (SocketCAN receiver and UDP forwarder).
- `Functional_Requirement.md` — functional requirements for this component.

## Prerequisites
- Raspberry Pi with SPI enabled (if using an MCP2515 connected via SPI).
- MCP2515 CAN controller configured as `can0` (SocketCAN). Example device-tree overlay in `/boot/config.txt` (example below).
- `can-utils` (optional) for debugging tools like `candump`, `cansend`.
- Build tools: `build-essential` (gcc, make).

### `/boot/config.txt` lines for MCP2515 (adapt pins & osc as needed)
```text
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835
```
After editing /boot/config.txt reboot the Pi.

Bring up can0 (example)
```bash
Copy code
# set up the CAN interface with 125 kbps
sudo ip link set can0 down            # (ignore errors if already down)
sudo ip link set can0 up type can bitrate 125000
# verify
ip -details link show can0
```

## Install build tools (only once):

```bash
sudo apt update
sudo apt install build-essential
```

## Compile & Run
```bash
gcc -o can_recv_udp can_recv_udp.c
sudo ./can_recv_udp
```

The program prints messages like:

```text
Listening on can0...
ULTRASONIC dist=345 mm counter=12 status=0
```
It also forwards the numeric distance as ASCII (e.g. 345\n) to UDP 127.0.0.1:5005.
