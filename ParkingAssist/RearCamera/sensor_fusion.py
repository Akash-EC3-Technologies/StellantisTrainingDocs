import time
import math

# Typical Pi Camera v2 horizontal FOV
CAM_HFOV_DEG = 62.0
ASSOC_ANGLE_TOL_DEG = 20.0
ASSOC_HOLD_SEC = 0.4

# -------- Kalman Filter --------
class Kalman1D:
    def __init__(self, q=0.1, r=50.0, p=1.0, x=0.0):
        self.q = q
        self.r = r
        self.p = p
        self.x = x

    def predict(self):
        self.p += self.q
        return self.x

    def update(self, z):
        k = self.p / (self.p + self.r)
        self.x = self.x + k*(z - self.x)
        self.p = (1-k)*self.p
        return self.x

# Global fusion state
kalman = None
kalman_init = False
last_assoc = {"time": 0, "bbox": None, "centroid": None}

def pixel_to_bearing(cx, width):
    norm = (cx - width/2) / width
    return norm * CAM_HFOV_DEG

def fuse_vision_ultrasonic(frame, candidates, ultrasonic_mm):
    global kalman, kalman_init, last_assoc

    h, w = frame.shape[:2]

    # --- Kalman initialization / update ---
    if ultrasonic_mm is not None:
        if not kalman_init:
            kalman = Kalman1D(x=float(ultrasonic_mm))
            kalman_init = True
        fused_distance = kalman.update(float(ultrasonic_mm))
    else:
        if kalman_init:
            fused_distance = kalman.predict()
        else:
            fused_distance = None

    # --- Compute bearing for each detected object ---
    for c in candidates:
        cx, cy = c['centroid']
        c['bearing'] = pixel_to_bearing(cx, w)
        x,y,wc,hc = c['bbox']
        c['bottom'] = y + hc
        c['score'] = c['area'] * 0.7 + (c['bottom']) * 0.3

    # --- Angle-based association ---
    beam_angle = 0.0
    assoc = [c for c in candidates if abs(c['bearing'] - beam_angle) <= ASSOC_ANGLE_TOL_DEG]

    chosen = None
    if assoc:
        chosen = max(assoc, key=lambda c: c['score'])
    else:
        if time.time() - last_assoc['time'] <= ASSOC_HOLD_SEC:
            if last_assoc["bbox"] is not None:
                chosen = {
                    "bbox": last_assoc["bbox"],
                    "centroid": last_assoc["centroid"],
                    "score": 0
                }

    if chosen is None:
        return None

    # Save for temporal persistence
    last_assoc["time"] = time.time()
    last_assoc["bbox"] = chosen["bbox"]
    last_assoc["centroid"] = chosen["centroid"]

    return {
        "bbox": chosen["bbox"],
        "centroid": chosen["centroid"],
        "fused_distance_mm": ultrasonic_mm,
        "visual_score": chosen["score"],
    }
