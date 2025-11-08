# Functional Requirement — Raspberry Pi Camera Overlay (Phase 2)

## Identifier
FR-P2-PI-CAMERA-OVERLAY

## Purpose
Display the real-time rear camera feed and overlay ultrasonic sensor data (distance in mm) so the driver/demo viewer can see proximity information.

## Inputs
- Camera video stream from a Pi camera or USB webcam (e.g., /dev/video0).
- UDP stream of distances from `127.0.0.1:5005` (ASCII lines like "345\n").

## Outputs
- A live window showing camera feed with overlays:
  - Distance text (mm)
  - Proximity bar (graphical)
  - Visual brake warning when distance < threshold
  - Optional audible beep on threshold crossing

## Functional Behavior
1. Open the camera device and capture video frames continuously.
2. Concurrently listen for UDP distance updates. Use the most recent measurement.
3. Overlay on each frame:
   - Large text: `Dist: <mm> mm` (or `--` if timed out)
   - A horizontal proximity bar scaled to a configurable maximum range
   - A red warning label `BRAKE: IMMINENT` if `distance < threshold`
4. When distance falls below the threshold, optionally play a short beep.
5. Provide a keyboard shortcut `q` to quit.

## Non-functional Requirements
- Maintain at least 15 FPS at moderate resolution (e.g., 640x480) on Raspberry Pi 3/4 when possible.
- React to distance updates within 200 ms of receipt.
- Be resilient to missing UDP updates; display `--` if no update is received for >1 second.

## Test Cases
- TC1: Valid UDP distance updates appear as overlay text and bar.
- TC2: No UDP updates for >1s => overlay shows `Dist: -- mm`.
- TC3: Distance < threshold => brake warning appears and beep plays.
- TC4: Camera backend fallback: if OpenCV fails but picamera2 exists, script uses picamera2 capture.