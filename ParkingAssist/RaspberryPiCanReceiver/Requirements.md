# Functional Requirement — Raspberry Pi CAN Receiver (Phase 1)

## Identifier
FR-P1-PI-CAN-RECEIVER

## Purpose
Receive ultrasonic distance frames from the CAN bus, validate integrity using CRC8, and forward parsed data to local consumers (UDP) while logging.

## Inputs
- CAN frames on SocketCAN interface `can0` (standard 11-bit IDs).
  - Expected ultrasonic CAN ID: `0x100`, 8-byte payload as defined in project spec.

## Outputs
- Standard output logs for human inspection.
- UDP packets to `127.0.0.1:5005` containing the current measured distance as ASCII (e.g., `345\n`).

## Functional Behavior
1. Open `can0` via SocketCAN and listen for frames.
2. For each received CAN frame:
   - Accept only frames with `can_id == 0x100` and `can_dlc == 8`.
   - Compute CRC8 over bytes 0..6 using polynomial 0x07 and compare with byte 7.
   - If CRC matches:
     - Extract `distance_mm` from bytes 0..1 (big-endian).
     - Extract `counter` and `status` from bytes 2 and 3.
     - Print a log line with distance, counter, and status.
     - Forward the distance as ASCII followed by newline to UDP `127.0.0.1:5005`.
   - If CRC fails: log an error and drop the frame.
3. Continue running indefinitely; handle transient errors by logging and continuing.

## Non-functional Requirements
- Process frames in near real-time (low processing latency).
- Be robust to malformed frames and temporary CAN link issues.
- Require minimal CPU; suitable to run continuously on a Raspberry Pi.

## Test Cases
- TC1: Valid frame — program logs parsed values and UDP-forwarded distance.
- TC2: CRC mismatch — program logs CRC error and does not forward.
- TC3: Non-ultrasonic ID — program ignores other CAN IDs.
- TC4: CAN link down/up — program should exit with an informative error or retry (current implementation logs and exits; service manager can restart).