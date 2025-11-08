# Phase 2 — Raspberry Pi Camera + Ultrasonic Overlay

## Purpose
Capture the Raspberry Pi rear-camera feed and overlay ultrasonic distance data (received via UDP from the Phase 1 CAN receiver). Display the combined video on an attached display (TFT/HDMI) for a parking assist demo.

## Files
- `camera_overlay.py`         — main Python app (captures video, listens for distance UDP, overlays graphics).
- `requirements.txt`         — Python dependencies.
- `run_camera.sh`            — helper to run the app.
- `systemd/camera-overlay.service` — optional systemd service to autostart at boot.
- `Functional_Requirement.md`— functional requirements.

## How it integrates with Phase 1
- The Phase 1 Raspberry Pi CAN receiver forwards parsed distances as ASCII lines over UDP to `127.0.0.1:5005`.
- `camera_overlay.py` listens on UDP port `5005` and uses the latest distance value to draw overlays on the live camera feed.

## Supported camera backends
- Primary: OpenCV `cv2.VideoCapture(0)` (works if your camera device is exposed as `/dev/video0` or via `v4l2`).
- Fallback: `picamera2` (new Pi camera stack). If `picamera2` is detected and OpenCV fails, the script tries the `picamera2` capture path.

## Installation (Raspberry Pi OS)
1. Update:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
2. Install system packages:

```bash
sudo apt install -y python3-pip python3-opencv libjpeg-dev v4l-utils
```

If using Pi Camera v2/v3 with libcamera/picamera2:

```bash
sudo apt install -y python3-picamera2
```

3. Install Python packages:
```bash
cd ~
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
### Run

> Ensure the CAN receiver (Phase 1) is running and forwarding to UDP 127.0.0.1:5005.

```bash
python camera_overlay.py
```

Press q in the window to quit.