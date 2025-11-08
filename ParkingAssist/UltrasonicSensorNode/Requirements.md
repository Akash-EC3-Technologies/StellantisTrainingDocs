# Functional Requirement — Arduino Ultrasonic CAN Sender (Phase 1)

## Identifier
FR-P1-ARDUINO-ULTRASONIC

## Purpose
Read distance from HC-SR04 ultrasonic sensor and reliably transmit the measured value over the CAN bus periodically.

## Inputs
- HC-SR04 echo signal (digital input)
- HC-SR04 trigger control (digital output)
- Power supply (5V) and ground

## Outputs
- CAN bus messages (standard 11-bit ID) with ID `0x100` containing:
  - distance (mm), counter, status, reserved, CRC8

## Functional Behavior
1. The Arduino shall trigger the HC-SR04 with a 10 µs pulse and read the echo pulse width.
2. Convert echo time to distance in millimeters: `distance_mm = duration_us / 58` (approx).
3. If no echo within timeout (30 ms), mark `status = 1` and set `distance = 0xFFFF`.
4. If distance is beyond practical limit (e.g., > 4000 mm), mark `status = 2`.
5. Assemble an 8-byte CAN data frame:
   - bytes 0..1: distance_mm (big-endian)
   - byte 2: transmit counter (wraps 0..255)
   - byte 3: status
   - bytes 4..6: zeros
   - byte 7: CRC8 over bytes 0..6 (polynomial 0x07)
6. Transmit the frame on CAN ID `0x100` at 125 kbps every 100 ms.

## Error Handling
- On consecutive measurement errors or CAN send failures, continue attempting; always send status codes instead of stopping.

## Test Cases (basic)
- TC1: Normal measurement — distance within range, CRC verified at receiver.
- TC2: Timeout measurement — receiver sees status=1 and ignores the distance value.
- TC3: Out-of-range measurement — receiver sees status=2.
- TC4: CAN send failure — Arduino logs via Serial and continues.
