# Functional Requirement — ABS ECU (Phase X)

## ID
FR-ABS-ECU-PI

## Purpose
Receive ultrasonic sensor readings over CAN and apply braking output as PWM percentage. Broadcast braking status over CAN.

## Inputs
- CAN frames on SocketCAN interface (e.g., `can0`), ultrasonic ID `0x100`.

## Outputs
- Hardware PWM output via sysfs at `/sys/class/pwm/pwmchip<p>/pwm<q>/` with duty cycle mapped to brake percentage.
- CAN frames ID `0x200` containing braking state & percentage.

## Behaviour
1. Listen on CAN interface for ID `0x100`. Validate CRC8 (poly 0x07) over bytes 0..6 against byte 7.
2. If CRC valid and status==0 and distance_mm is numeric:
   - If `distance_mm < threshold_mm`:
     - Compute `brake_percent = min(100, round( (threshold_mm - distance_mm) / (threshold_mm - min_distance_mm) * 100 ))`
       - If distance <= min_distance_mm then brake_percent = 100.
     - Set PWM duty cycle to `period_ns * brake_percent / 100`.
     - Set brake_state=ON (0x01).
   - Else:
     - Set brake_percent=0, brake_state=OFF.
3. If CRC invalid or status != 0: set brake OFF.
4. On each change or periodic update, send CAN frame ID `0x200` with [brake_state, brake_percent].
5. On process exit, disable PWM and unexport if program exported it.

## Non-functional
- Reaction latency: should apply PWM within one CAN frame period + processing time (ms scale).
- Robustness: tolerate transient CRC errors; default to brake OFF on invalid data.