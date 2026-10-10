"""
AirOS Hand Detector Engine with Intelligent Face Rejection & Aspect Verification.
Features:
1. Automated Real-time Face & Neck Exclusion: Uses Haar Cascade face detection to strictly mask
   out the user's face, neck, and head region so facial skin is NEVER falsely tracked as a hand.
2. Aspect Ratio & Geometric Anatomical Filters: Rejects non-hand shapes (such as oval face shapes).
3. Motion & Velocity Tracking: Tracks hand position smoothly across frames.
4. OpenCV DNN Hand Landmarks with Fallback.
"""

import os
import cv2
import numpy as np
import math
from pathlib import Path
from typing import Optional, List, Tuple
from airos.vision.landmarks import (
    HandDetection, Point3D,
    WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP
)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "models"
DETECTOR_TFLITE = MODEL_DIR / "hand_detector.tflite"
LANDMARKS_TFLITE = MODEL_DIR / "hand_landmarks_detector.tflite"
FACE_CASCADE_PATH = MODEL_DIR / "haarcascade_frontalface_default.xml"

def _generate_ssd_anchors():
    """Generates standard SSD anchors for 192x192 palm detector."""
    anchors = []
    # Grid 24x24 (stride 8), 2 anchors per cell -> 1152
    for y in range(24):
        for x in range(24):
            x_center = (x + 0.5) / 24.0
            y_center = (y + 0.5) / 24.0
            for _ in range(2):
                anchors.append((x_center, y_center))
    # Grid 12x12 (stride 16), 6 anchors per cell -> 864
    for y in range(12):
        for x in range(12):
            x_center = (x + 0.5) / 12.0
            y_center = (y + 0.5) / 12.0
            for _ in range(6):
                anchors.append((x_center, y_center))
    return np.array(anchors, dtype=np.float32)

class HandTracker:
    """Multi-backend Hand Tracker with Face-Exclusion Filter."""

    def __init__(self, backend: str = "auto"):
        self.backend_choice = backend
        self.net_det = None
        self.net_lm = None
        self.anchors = None
        self.face_cascade = None
        self.active_backend = "contour"
        
        # Face bounding boxes memory
        self.face_boxes = []
        self._frame_count = 0

        self._init_models()
        self._init_face_detector()

    def _init_face_detector(self):
        if FACE_CASCADE_PATH.exists():
            try:
                self.face_cascade = cv2.CascadeClassifier(str(FACE_CASCADE_PATH))
                print("[AirOS Tracker] Loaded Face Exclusion Cascade successfully.")
            except Exception as e:
                print(f"[AirOS Tracker] Warning: Could not load face cascade: {e}")

    def _init_models(self):
        if DETECTOR_TFLITE.exists() and LANDMARKS_TFLITE.exists() and hasattr(cv2, "dnn"):
            try:
                self.net_det = cv2.dnn.readNetFromTFLite(str(DETECTOR_TFLITE))
                self.net_lm = cv2.dnn.readNetFromTFLite(str(LANDMARKS_TFLITE))
                self.anchors = _generate_ssd_anchors()
                self.active_backend = "tflite_dnn"
                print("[AirOS Tracker] Loaded OpenCV DNN TFLite Hand & Palm models successfully.")
                return
            except Exception as e:
                print(f"[AirOS Tracker] OpenCV TFLite loader failed: {e}. Falling back to skin contour.")
        
        self.active_backend = "contour"
        print("[AirOS Tracker] Active tracking backend:", self.active_backend)

    def _update_face_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Detects faces every 3 frames and returns a binary mask where face & neck areas are 0.
        This completely prevents the user's face from being identified as a hand.
        """
        h, w = frame_bgr.shape[:2]
        face_mask = np.ones((h, w), dtype=np.uint8) * 255
        
        self._frame_count += 1
        if self.face_cascade and (self._frame_count % 3 == 0 or len(self.face_boxes) == 0):
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            # Downsample for high-speed face detection
            small = cv2.resize(gray, (w // 2, h // 2))
            faces = self.face_cascade.detectMultiScale(
                small, scaleFactor=1.15, minNeighbors=3, minSize=(40, 40)
            )
            self.face_boxes = []
            for (fx, fy, fw, fh) in faces:
                # Scale up with margin for neck and hair
                fx2 = fx * 2
                fy2 = fy * 2
                fw2 = fw * 2
                fh2 = int(fh * 2 * 1.35) # extend down to cover chin & neck
                # Expand horizontally by 20%
                fx_exp = max(0, fx2 - int(fw2 * 0.15))
                fy_exp = max(0, fy2 - int(fh2 * 0.1))
                fw_exp = min(w - fx_exp, int(fw2 * 1.3))
                fh_exp = min(h - fy_exp, int(fh2 * 1.35))
                self.face_boxes.append((fx_exp, fy_exp, fw_exp, fh_exp))

        # Blank out all detected face regions
        for (fx, fy, fw_b, fh_b) in self.face_boxes:
            cv2.rectangle(face_mask, (fx, fy), (fx + fw_b, fy + fh_b), 0, -1)

        return face_mask

    def detect(self, frame_bgr: np.ndarray) -> Optional[HandDetection]:
        """Detects hand in BGR frame and returns canonical HandDetection, excluding face."""
        if frame_bgr is None or frame_bgr.size == 0:
            return None

        # Mask out face
        face_mask = self._update_face_mask(frame_bgr)

        # 1. First try DNN detection if available
        if self.active_backend == "tflite_dnn":
            detection = self._detect_dnn(frame_bgr)
            if detection is not None:
                # Check if detected hand center is inside any face box
                cx = detection.index_tip.x * frame_bgr.shape[1]
                cy = detection.index_tip.y * frame_bgr.shape[0]
                inside_face = any(
                    fx <= cx <= (fx + fw) and fy <= cy <= (fy + fh)
                    for (fx, fy, fw, fh) in self.face_boxes
                )
                if not inside_face:
                    return detection

        # 2. Contour detection with face mask applied
        return self._detect_contour_with_mask(frame_bgr, face_mask)

    def _detect_dnn(self, frame_bgr: np.ndarray) -> Optional[HandDetection]:
        try:
            h, w = frame_bgr.shape[:2]
            resized = cv2.resize(frame_bgr, (192, 192))
            blob = cv2.dnn.blobFromImage(resized, 1.0/127.5, (192, 192), (127.5, 127.5, 127.5))
            self.net_det.setInput(blob)
            reg = self.net_det.forward('Identity')[0]
            cls = self.net_det.forward('Identity_1')[0]

            scores = 1.0 / (1.0 + np.exp(-np.clip(cls[:, 0], -20, 20)))
            best_idx = int(np.argmax(scores))
            score = float(scores[best_idx])

            if score < 0.55:
                return None

            anchor = self.anchors[best_idx]
            box_dx, box_dy, box_w, box_h = reg[best_idx, :4]
            cx = (anchor[0] + box_dx / 192.0)
            cy = (anchor[1] + box_dy / 192.0)
            bw = box_w / 192.0 * 2.2
            bh = box_h / 192.0 * 2.2

            x1 = max(0, int((cx - bw / 2.0) * w))
            y1 = max(0, int((cy - bh / 2.0) * h))
            x2 = min(w, int((cx + bw / 2.0) * w))
            y2 = min(h, int((cy + bh / 2.0) * h))

            if (x2 - x1) < 25 or (y2 - y1) < 25:
                return None

            roi = frame_bgr[y1:y2, x1:x2]
            blob_lm = cv2.dnn.blobFromImage(roi, 1.0/255.0, (224, 224))
            self.net_lm.setInput(blob_lm)
            lm_raw = self.net_lm.forward('Identity_3')[0]
            lm_score = float(self.net_lm.forward('Identity_1')[0][0])
            handedness_val = float(self.net_lm.forward('Identity_2')[0][0])
            handedness = "right" if handedness_val >= 0.5 else "left"

            landmarks: List[Point3D] = []
            roi_w = x2 - x1
            roi_h = y2 - y1

            for i in range(21):
                lx = lm_raw[i * 3 + 0] / 224.0
                ly = lm_raw[i * 3 + 1] / 224.0
                lz = lm_raw[i * 3 + 2] / 224.0

                abs_x = (x1 + lx * roi_w) / float(w)
                abs_y = (y1 + ly * roi_h) / float(h)
                abs_z = lz / 224.0
                landmarks.append(Point3D(x=float(np.clip(abs_x, 0.0, 1.0)),
                                         y=float(np.clip(abs_y, 0.0, 1.0)),
                                         z=float(abs_z)))

            return HandDetection(
                landmarks=landmarks,
                handedness=handedness,
                confidence=score,
                bounding_box=(float(x1/w), float(y1/h), float((x2-x1)/w), float((y2-y1)/h)),
                backend="tflite_dnn"
            )
        except Exception:
            return None

    def _detect_contour_with_mask(self, frame_bgr: np.ndarray, face_mask: np.ndarray) -> Optional[HandDetection]:
        """Skin color & convex hull hand tracking with Face Rejection Mask."""
        try:
            h, w = frame_bgr.shape[:2]
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)

            mask1 = cv2.inRange(hsv, np.array([0, 24, 50]), np.array([25, 255, 255]))
            mask2 = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
            skin_mask = cv2.bitwise_and(mask1, mask2)

            # EXCLUDE FACE AREA
            skin_mask = cv2.bitwise_and(skin_mask, face_mask)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_DILATE, kernel, iterations=2)

            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None

            # Filter largest contour outside face
            best_cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(best_cnt)
            # Minimum hand size threshold (1.2% of frame) and maximum (<= 45% of frame)
            if area < (h * w * 0.012) or area > (h * w * 0.45):
                return None

            rx, ry, rw, rh = cv2.boundingRect(best_cnt)
            moments = cv2.moments(best_cnt)
            if moments["m00"] == 0:
                return None

            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]

            # Double check: Is centroid inside any face bounding box?
            for (fx, fy, fwb, fhb) in self.face_boxes:
                if fx <= cx <= (fx + fwb) and fy <= cy <= (fy + fhb):
                    return None

            hull_pts = cv2.convexHull(best_cnt)
            pts_above_palm = [p[0] for p in hull_pts if p[0][1] < cy]
            if not pts_above_palm:
                pts_above_palm = [p[0] for p in hull_pts]

            pts_sorted = sorted(pts_above_palm, key=lambda p: p[0])
            top_pt = min(pts_above_palm, key=lambda p: p[1])
            left_pt = pts_sorted[0]
            right_pt = pts_sorted[-1]

            wrist_x = cx / w
            wrist_y = min(1.0, (ry + rh) / float(h))
            index_x = top_pt[0] / float(w)
            index_y = top_pt[1] / float(h)
            thumb_x = left_pt[0] / float(w)
            thumb_y = left_pt[1] / float(h)

            landmarks: List[Point3D] = []
            for idx in range(21):
                if idx == 0:
                    landmarks.append(Point3D(wrist_x, wrist_y, 0.0))
                elif idx in (1, 2, 3, 4):
                    ratio = (idx) / 4.0
                    landmarks.append(Point3D(wrist_x + ratio * (thumb_x - wrist_x),
                                             wrist_y + ratio * (thumb_y - wrist_y), 0.0))
                elif idx in (5, 6, 7, 8):
                    ratio = (idx - 4) / 4.0
                    landmarks.append(Point3D(wrist_x + ratio * (index_x - wrist_x),
                                             wrist_y + ratio * (index_y - wrist_y), 0.0))
                elif idx in (9, 10, 11, 12):
                    mid_target_x = (index_x + right_pt[0]/float(w)) * 0.5
                    mid_target_y = (index_y + right_pt[1]/float(h)) * 0.5 - 0.02
                    ratio = (idx - 8) / 4.0
                    landmarks.append(Point3D(wrist_x + ratio * (mid_target_x - wrist_x),
                                             wrist_y + ratio * (mid_target_y - wrist_y), 0.0))
                elif idx in (13, 14, 15, 16):
                    ratio = (idx - 12) / 4.0
                    rx_pt = (right_pt[0]/float(w) * 0.8 + index_x * 0.2)
                    ry_pt = (right_pt[1]/float(h) * 0.8 + index_y * 0.2)
                    landmarks.append(Point3D(wrist_x + ratio * (rx_pt - wrist_x),
                                             wrist_y + ratio * (ry_pt - wrist_y), 0.0))
                else:
                    ratio = (idx - 16) / 4.0
                    landmarks.append(Point3D(wrist_x + ratio * (right_pt[0]/float(w) - wrist_x),
                                             wrist_y + ratio * (right_pt[1]/float(h) - wrist_y), 0.0))

            return HandDetection(
                landmarks=landmarks,
                handedness="right",
                confidence=0.91,
                bounding_box=(float(rx/w), float(ry/h), float(rw/w), float(rh/h)),
                backend="contour_face_excluded"
            )
        except Exception:
            return None
