"""
AirOS Camera Preview & HUD Indicator.
Displays mirrored webcam feed, detected skeletal landmarks, gesture state badge,
and one-click Emergency Pause control.
"""

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
        self.video_label.setFixedHeight(140)
        layout.addWidget(self.video_label)

        # Bottom gesture badge
        self.gesture_badge = QLabel("Gesture: Ready")
        self.gesture_badge.setStyleSheet("color: #f0f6fc; font-size: 10px; font-weight: 500;")
        layout.addWidget(self.gesture_badge)

        self.setStyleSheet("""
            QFrame#CameraHUD {
                background-color: rgba(22, 27, 34, 0.92);
                border: 1px solid #30363d;
                border-radius: 8px;
            }
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

    def update_frame(self, frame_bgr: np.ndarray, detection: HandDetection, event: GestureEvent):
        if self.is_paused or frame_bgr is None:
            return

        # Render landmarks on frame copy
        h, w = frame_bgr.shape[:2]
        display_frame = frame_bgr.copy()

        if detection and detection.is_valid:
            # Draw bone connections
            pts = [(int(p.x * w), int(p.y * h)) for p in detection.landmarks]
            for start_idx, end_idx in HAND_CONNECTIONS:
                cv2.line(display_frame, pts[start_idx], pts[end_idx], (88, 166, 255), 2)
            for idx, pt in enumerate(pts):
                color = (0, 240, 255) if idx == 8 else (0, 255, 128)
                cv2.circle(display_frame, pt, 4, color, -1)

        # Convert to QPixmap
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)

        if event:
            self.gesture_badge.setText(f"Gesture: {event.state_description}")
