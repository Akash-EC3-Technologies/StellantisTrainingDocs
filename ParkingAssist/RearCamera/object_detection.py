import cv2
import numpy as np

def detect_candidates(frame,
                      canny1=60,
                      canny2=180,
                      min_area=800,
                      morph_size=7):
    """
    Returns list of object candidates:
    [{'bbox':(x,y,w,h), 'centroid':(cx,cy), 'area':A}]
    """
    h, w = frame.shape[:2]

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, canny1, canny2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_size, morph_size))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x,y,wc,hc = cv2.boundingRect(cnt)
        cx = x + wc//2
        cy = y + hc//2
        candidates.append({
            "bbox": (x,y,wc,hc),
            "centroid": (cx,cy),
            "area": area,
        })
    return candidates
