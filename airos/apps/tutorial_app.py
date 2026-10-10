"""
AirOS Built-in Application: Gesture Tutorial & Calibration Wizard.
Interactive guide with visual hand diagrams, live recognition feedback,
and customizable sensitivity calibration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QProgressBar, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from airos.storage.settings import SettingsManager

class TutorialApp(QWidget):
    settings_changed = Signal()

    def __init__(self, settings_mgr: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QLabel("👋 AirOS Gesture Learning Center & Calibration")
        header.setFont(QFont("Segoe UI", 13, QFont.Bold))
        header.setStyleSheet("color: #58a6ff;")
        layout.addWidget(header)

        # Gesture cards grid
        gestures_group = QGroupBox("Core Gesture Reference")
        gestures_group.setStyleSheet("QGroupBox { color: #8b949e; font-weight: bold; border: 1px solid #30363d; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        grid = QGridLayout(gestures_group)
        grid.setSpacing(10)

        gestures_info = [
            ("☝️ Move Cursor", "Point your index finger. The cursor glides smoothly with real-time EMA filtering."),
            ("🤏 Left Click", "Briefly pinch index finger and thumb tip together, then release."),
            ("✊ Drag & Drop", "Pinch and hold for >0.35s while moving your hand to drag windows or icons."),
            ("✌️ Two-Finger Scroll", "Extend index & middle fingers close together and move vertically to scroll."),
            ("✋ Open Palm", "Extend all five fingers forward to toggle the Start Menu and quick settings."),
            ("↔️ Swipe Workspace", "Perform a swift horizontal hand wave to switch between virtual desktop spaces."),
            ("✌️✌️ Virtual Keyboard", "Make a V-sign with separated index & middle fingers to toggle AirType keyboard.")
        ]

        for i, (title, desc) in enumerate(gestures_info):
            r = i // 2
            c = i % 2
            card = QLabel(f"<b>{title}</b><br><span style='color: #8b949e; font-size: 11px;'>{desc}</span>")
            card.setWordWrap(True)
            card.setStyleSheet("background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 8px; color: #f0f6fc;")
            grid.addWidget(card, r, c)

        layout.addWidget(gestures_group)

        # Calibration Controls
        calib_group = QGroupBox("Live Calibration & Sensitivity Wizard")
        calib_group.setStyleSheet("QGroupBox { color: #8b949e; font-weight: bold; border: 1px solid #30363d; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        calib_layout = QVBoxLayout(calib_group)

        # Smoothing Slider
        smoothing_box = QHBoxLayout()
        smoothing_label = QLabel("Cursor Smoothing (Responsive ↔ Ultra Smooth):")
        smoothing_label.setStyleSheet("color: #c9d1d9;")
        smoothing_box.addWidget(smoothing_label)

        self.slider_smoothing = QSlider(Qt.Horizontal)
        self.slider_smoothing.setRange(20, 95)
        self.slider_smoothing.setValue(int(float(self.settings.get("cursor_smoothing", 0.65)) * 100))
        self.slider_smoothing.valueChanged.connect(self._on_smoothing_change)
        smoothing_box.addWidget(self.slider_smoothing)
        calib_layout.addLayout(smoothing_box)

        # Pinch Threshold Slider
        pinch_box = QHBoxLayout()
        pinch_label = QLabel("Pinch Distance Sensitivity (Strict ↔ Easy):")
        pinch_label.setStyleSheet("color: #c9d1d9;")
        pinch_box.addWidget(pinch_label)

        self.slider_pinch = QSlider(Qt.Horizontal)
        self.slider_pinch.setRange(25, 90)
        self.slider_pinch.setValue(int(float(self.settings.get("click_pinch_threshold", 0.055)) * 1000))
        self.slider_pinch.valueChanged.connect(self._on_pinch_change)
        pinch_box.addWidget(self.slider_pinch)
        calib_layout.addLayout(pinch_box)

        layout.addWidget(calib_group)

        # Status and Reset Button
        btn_bar = QHBoxLayout()
        self.status_msg = QLabel("Ready for touchless operation.")
        self.status_msg.setStyleSheet("color: #3fb950; font-weight: bold;")
        btn_bar.addWidget(self.status_msg)
        btn_bar.addStretch()

        self.btn_reset = QPushButton("Reset Defaults")
        self.btn_reset.setStyleSheet("background-color: #21262d; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_bar.addWidget(self.btn_reset)

        layout.addLayout(btn_bar)

    def _on_smoothing_change(self, val: int):
        alpha = val / 100.0
        self.settings.set("cursor_smoothing", alpha)
        self.settings_changed.emit()

    def _on_pinch_change(self, val: int):
        thresh = val / 1000.0
        self.settings.set("click_pinch_threshold", thresh)
        self.settings_changed.emit()

    def _reset_defaults(self):
        self.slider_smoothing.setValue(65)
        self.slider_pinch.setValue(55)
        self.settings.set("cursor_smoothing", 0.65)
        self.settings.set("click_pinch_threshold", 0.055)
        self.settings_changed.emit()
        self.status_msg.setText("Defaults restored!")
