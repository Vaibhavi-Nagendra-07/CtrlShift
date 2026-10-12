"""
AirOS Camera Preview & HUD Indicator.
Displays mirrored webcam feed, detected skeletal landmarks, gesture state badge,
and one-click Emergency Pause control.
"""

import time
from typing import Optional
import cv2
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont
from airos.vision.landmarks import HandDetection, HAND_CONNECTIONS
from airos.gestures.state_machine import GestureEvent

class CameraPreviewHUD(QFrame):
    """Real-time HUD displaying camera status, landmarks, and pause toggle."""

    pause_toggled = Signal(bool)

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.is_paused = False
        self.last_pixmap = None
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("CameraHUD")
        self.setFixedSize(260, 210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header bar
        header = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #3fb950; font-size: 14px;")
        header.addWidget(self.status_dot)

        self.title = QLabel("AirVision HUD")
        self.title.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 11px;")
        header.addWidget(self.title)
        header.addStretch()

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setFixedHeight(22)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 3px;
                font-size: 10px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #30363d;
            }
        """)
        self.btn_pause.clicked.connect(self._toggle_pause)
        header.addWidget(self.btn_pause)
        layout.addLayout(header)

        # Video feed frame
        self.video_label = QLabel("Initializing camera...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #0d1117; border-radius: 6px; color: #8b949e; font-size: 10px;")
        self.video_label.setFixedHeight(135)
        layout.addWidget(self.video_label)

        # Drawing mode badge (as in user screenshot: teal banner "Drawing: draw")
        self.drawing_badge = QLabel("Drawing: draw")
        self.drawing_badge.setAlignment(Qt.AlignCenter)
        self.drawing_badge.setFixedHeight(22)
        self.drawing_badge.setStyleSheet("""
            background-color: #004d40;
            color: #26a69a;
            border: 1px solid #00796b;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.drawing_badge.hide()
        layout.addWidget(self.drawing_badge)

        # Bottom gesture badge
        self.gesture_badge = QLabel("Gesture: Ready")
        self.gesture_badge.setStyleSheet("color: #f0f6fc; font-size: 10px; font-weight: 500;")
        layout.addWidget(self.gesture_badge)

        self.setStyleSheet("""
            QFrame#CameraHUD {
                background-color: rgba(22, 27, 34, 0.94);
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)

        self.is_drawing_active = False
        self.drawing_state = "hover"
        self._last_fps_time = time.time()
        self._fps = 90.0

    def set_drawing_mode(self, active: bool, state: str = "draw"):
        self.is_drawing_active = active
        self.drawing_state = state
        if active:
            self.setFixedSize(260, 235)
            self.drawing_badge.show()
            self.update_drawing_state(state)
        else:
            self.setFixedSize(260, 210)
            self.drawing_badge.hide()

    def update_drawing_state(self, state: str):
        self.drawing_state = state
        if not self.is_drawing_active:
            return
        if state == "draw":
            self.drawing_badge.setText("Drawing: draw")
            self.drawing_badge.setStyleSheet("""
                background-color: #005b60;
                color: #2dd4bf;
                border: 1px solid #14b8a6;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)
        elif state == "erase":
            self.drawing_badge.setText("Drawing: erase")
            self.drawing_badge.setStyleSheet("""
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 1px solid #ef4444;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)
        else:
            self.drawing_badge.setText("Drawing: hover")
            self.drawing_badge.setStyleSheet("""
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            """)

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.setText("▶ Resume")
            self.btn_pause.setStyleSheet("background-color: #238636; color: white;")
            self.status_dot.setStyleSheet("color: #d29922; font-size: 14px;")
            self.gesture_badge.setText("Gesture: PAUSED")
        else:
            self.btn_pause.setText("⏸ Pause")
            self.btn_pause.setStyleSheet("background-color: #21262d; color: #c9d1d9;")
            self.status_dot.setStyleSheet("color: #3fb950; font-size: 14px;")
            self.gesture_badge.setText("Gesture: Active")

        self.pause_toggled.emit(self.is_paused)

    def update_frame(self, frame_bgr: np.ndarray, detection: Optional[HandDetection], event: Optional[GestureEvent]):
        if self.is_paused or frame_bgr is None:
            return

        h, w = frame_bgr.shape[:2]
        display_frame = frame_bgr.copy()

        now = time.time()
        dt = now - self._last_fps_time
        if dt > 0:
            current_fps = 1.0 / dt
            self._fps = 0.93 * self._fps + 0.07 * current_fps
        self._last_fps_time = now

        # Overlay FPS & Gesture telemetry at top of frame (matching user screenshot)
        g_desc = event.state_description if event else "Ready"
        fps_text = f"FPS: {self._fps:.1f}  GESTURE: {g_desc[:12]}"
        cv2.putText(display_frame, fps_text, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 128), 1, cv2.LINE_AA)

        is_valid_hand = bool(
            detection is not None 
            and detection.is_valid 
            and getattr(detection, 'is_anatomical_hand', True) 
            and detection.confidence >= 0.50
        )

        if is_valid_hand:
            # 1. Bounding box around hand (matching touchless reference image)
            pts = [(int(p.x * w), int(p.y * h)) for p in detection.landmarks]
            xs = [pt[0] for pt in pts]
            ys = [pt[1] for pt in pts]
            x1 = max(0, min(xs) - 14)
            y1 = max(0, min(ys) - 14)
            x2 = min(w - 1, max(xs) + 14)
            y2 = min(h - 1, max(ys) + 14)

            # Draw sleek glowing bounding box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 100, 255), 2)

            # Handedness and confidence label badge above box (e.g. "Right 98%")
            tag = f"{detection.handedness.title()} {int(detection.confidence * 100)}%"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tag_y1 = max(0, y1 - th - 6)
            cv2.rectangle(display_frame, (x1, tag_y1), (x1 + tw + 8, y1), (0, 100, 255), -1)
            cv2.putText(display_frame, tag, (x1 + 4, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # 2. Draw skeletal bone connections
            for start_idx, end_idx in HAND_CONNECTIONS:
                cv2.line(display_frame, pts[start_idx], pts[end_idx], (0, 230, 255), 2, cv2.LINE_AA)

            # 3. Draw keypoint circles on joints
            for idx, pt in enumerate(pts):
                if idx == 8: # Index fingertip (pointer)
                    cv2.circle(display_frame, pt, 6, (0, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(display_frame, pt, 8, (255, 255, 255), 1, cv2.LINE_AA)
                elif idx == 4: # Thumb tip
                    cv2.circle(display_frame, pt, 5, (255, 200, 0), -1, cv2.LINE_AA)
                else:
                    cv2.circle(display_frame, pt, 4, (0, 255, 128), -1, cv2.LINE_AA)

            self.status_dot.setStyleSheet("color: #3fb950; font-size: 14px;")
        else:
            self.status_dot.setStyleSheet("color: #8b949e; font-size: 14px;")

        # Convert to QPixmap using hardware-accelerated OpenCV resize (eliminates Qt render bottleneck)
        lbl_w = max(10, self.video_label.width())
        lbl_h = max(10, self.video_label.height())
        disp_resized = cv2.resize(display_frame, (lbl_w, lbl_h), interpolation=cv2.INTER_LINEAR)
        rgb_frame = cv2.cvtColor(disp_resized, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * lbl_w
        q_img = QImage(rgb_frame.data, lbl_w, lbl_h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

        if event and is_valid_hand:
            self.gesture_badge.setText(f"Gesture: {event.state_description}")
        else:
            self.gesture_badge.setText("Ready (Raise hand to control)")
