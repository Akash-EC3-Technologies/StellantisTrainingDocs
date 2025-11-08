# Phase 1 — Arduino Ultrasonic Sensor Node

## Overview
This folder contains the Arduino sketch and supporting notes to read an HC-SR04 ultrasonic sensor and periodically send the distance reading over CAN using an MCP2515 CAN controller.

## Files
- `Ultrasonic_CAN_Sender.ino` — Arduino sketch (main source).
- `Functional_Requirement.md` — short functional requirements for this component.

## Dependencies / Libraries
- Arduino IDE (or Arduino CLI)
- `MCP_CAN` library by Cory J. (search "MCP_CAN" in Arduino Library Manager or install from GitHub)
  - In Arduino IDE: Sketch → Include Library → Manage Libraries → search `MCP_CAN` (or install `mcp_can`).

## CAN Parameters
- CAN bitrate: **125 kbps**
- Ultrasonic CAN ID: `0x100`
- Ultrasonic payload layout (8 bytes):
  - `data[0..1]` — `distance_mm` (uint16, big-endian)
  - `data[2]` — `counter` (uint8)
  - `data[3]` — `status` (0 = OK, 1 = timeout, 2 = out_of_range)
  - `data[4..6]` — reserved (set to 0)
  - `data[7]` — `crc8` computed over bytes `0..6` using CRC-8 poly 0x07

## Connections

### HC-SR04 to Arduino UNO:
- VCC  -> 5V
- GND  -> GND
- TRIG -> Arduino digital pin 8 (HC_TRIG in sketch)
- ECHO -> Arduino digital pin 7 (HC_ECHO in sketch)

### MCP2515 to Arduino UNO:
- VCC  -> 5V
- GND  -> GND
- CS   -> D10  (Chip Select for SPI; matches sketch CS_PIN)
- MOSI -> D11 (hardware SPI MOSI)
- MISO -> D12 (hardware SPI MISO)
- SCK  -> D13 (hardware SPI SCK)
- INT  -> D2 

- CANH -> CAN bus high
- CANL -> CAN bus low

## Usage
1. Install `MCP_CAN` library.
2. Open `Ultrasonic_CAN_Sender.ino` in Arduino IDE and upload to UNO.
3. Ensure CAN bus has proper termination (120Ω at each physical end).
4. On the CAN bus receiver (Raspberry Pi or another node) listen for ID `0x100` frames and verify CRC.
