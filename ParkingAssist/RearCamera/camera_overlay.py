#!/usr/bin/env python3
import cv2
import time
import numpy as np
from picamera2 import Picamera2

# Local imports
from udp_server import DistanceReceiver
from object_detection import detect_candidates
from sensor_fusion import fuse_vision_ultrasonic

# ---------- Config ----------
WINDOW_NAME = "Parking Assist"
CAP_W = 800
CAP_H = 500
BRAKE_THRESHOLD_MM = 300
ROTATE_180 = True   # set False if not needed

def center_window(window_name):
    import tkinter as tk
    # Get display resolution using tkinter (most reliable on Pi)
    root = tk.Tk()
    root.withdraw()  # Hide main tkinter window
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    print(("screen resoulotion:",screen_w,screen_h))

    # Compute top-left corner for centering
    x = int((screen_w-CAP_W) / 2)
    y = int((screen_h-CAP_H) /2)

    # Move the OpenCV window
    cv2.resizeWindow(WINDOW_NAME, CAP_W, CAP_H)
    cv2.moveWindow(window_name, x, y)

def main():
    # Start UDP distance receiver
    dist_receiver = DistanceReceiver()

    # Start camera
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration({"size": (CAP_W, CAP_H)})
    picam2.configure(preview_config)
    picam2.start()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_FULLSCREEN)

    print("Camera + Fusion started.")

    while True:
        frame_rgb = picam2.capture_array()
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        # Rotate if necessary
        if ROTATE_180:
            frame = cv2.flip(frame, -1)

        # Get latest ultrasonic data
        ultrasonic_mm = dist_receiver.get_distance()

        # Detect candidates via vision
        candidates = detect_candidates(frame)

        # Fuse ultrasonic + vision
        fused = fuse_vision_ultrasonic(frame, candidates, ultrasonic_mm)

        # Draw fusion results
        if fused is not None:
            x,y,w,h = fused['bbox']
            cx, cy = fused['centroid']
            cv2.rectangle(frame, (x,y), (x+w,y+h), (255,0,0), 3)
            cv2.circle(frame, (cx,cy), 5, (255,0,0), -1)

            text = f"Fused: {fused['fused_distance_mm']} mm"
            cv2.putText(frame, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255,0,0), 2, cv2.LINE_AA)

            if (fused['fused_distance_mm'] is not None) and (fused['fused_distance_mm'] < BRAKE_THRESHOLD_MM):
                cv2.putText(frame, "BRAKE WARNING!", (x, y+h+30),
                            cv2.FONT_HERSHEY_DUPLEX, 1.0, (0,0,255), 3)

        # Show ultrasonic only fallback
        if ultrasonic_mm is not None:
            cv2.putText(frame, f"Ultrasonic: {ultrasonic_mm} mm",
                        (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0,255,255), 2)

        cv2.imshow(WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    picam2.stop()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
