"""
AirOS Built-in Application: Spatial Mindfulness & Breathing Companion.
Interactive breathing animation inspired by VisionOS Mindfulness flower app.
"""

import math
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush, QPen

class BreathingFlower(QWidget):
    """Draws animated breathing flower geometry."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(260, 260)
        self.phase = 0.0 # 0.0 to 2*PI
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(30)

    def _animate(self):
        self.phase += 0.03
        if self.phase >= 2 * math.pi:
            self.phase = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width() // 2
        cy = self.height() // 2
        scale = 0.7 + 0.3 * (math.sin(self.phase) * 0.5 + 0.5)

        petals = 6
        base_radius = int(50 * scale)
        petal_radius = int(60 * scale)

        for i in range(petals):
            angle = i * (2 * math.pi / petals) + (self.phase * 0.1)
            px = int(cx + base_radius * math.cos(angle))
            py = int(cy + base_radius * math.sin(angle))
            
            # Translucent turquoise / cyan flower petal
            color = QColor(0, 245, 212, int(80 + 40 * math.sin(self.phase)))
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
            painter.drawEllipse(px - petal_radius, py - petal_radius, petal_radius * 2, petal_radius * 2)

        painter.end()

class MindfulnessApp(QWidget):
    """Mindfulness and Breathing app."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        title = QLabel("Mindfulness & Focus")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00f5d4; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.flower = BreathingFlower()
        layout.addWidget(self.flower, alignment=Qt.AlignCenter)

        self.instruction = QLabel("Breathe In slowly... and Breathe Out")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 13px;")
        layout.addWidget(self.instruction)
