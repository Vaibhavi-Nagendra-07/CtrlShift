"""
AirOS Touchless Adaptive Cursor Overlay.
Draws an interactive, high-visibility cursor that displays:
- Real-time gesture state
- IntentLock charging ring (dwell / pinch feedback)
- Drag indicators
- Large-target accessibility mode
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from airos.gestures.state_machine import GestureType, GestureEvent

class AdaptiveCursorOverlay(QWidget):
    """Floating transparent overlay that renders the touchless AirOS cursor."""

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.cursor_norm_pos = (0.5, 0.5)
        self.gesture_event = None
        self.intent_charge = 0.0 # 0.0 to 1.0 charge ratio
        self.cursor_visible = True
        self.is_large_target = False

        # Set transparent pass-through overlay flags
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)

    def update_theme(self, theme: dict):
        self.theme = theme
        self.update()

    def update_gesture_event(self, event: GestureEvent, is_large: bool = False):
        self.gesture_event = event
        self.cursor_norm_pos = event.cursor_pos
        self.is_large_target = is_large
        self.update()

    def set_cursor_visibility(self, visible: bool):
        self.cursor_visible = visible
        self.update()

    def paintEvent(self, event):
        if not self.cursor_visible or not self.gesture_event:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = int(self.cursor_norm_pos[0] * w)
        cy = int(self.cursor_norm_pos[1] * h)

        base_radius = 16 if not self.is_large_target else 24
        gesture = self.gesture_event.gesture

        # Determine colors based on gesture state
        color_hex = self.theme.get("cursor_color", "#00f0ff")
        intent_hex = self.theme.get("cursor_intent", "#58a6ff")
        
        main_color = QColor(color_hex)
        ring_color = QColor(intent_hex)

        if gesture == GestureType.PINCH_CLICK or gesture == GestureType.DOUBLE_CLICK:
            main_color = QColor("#3fb950") # Bright green click
            base_radius = int(base_radius * 0.75)
        elif gesture == GestureType.DRAG:
            main_color = QColor("#d29922") # Orange drag
            base_radius = int(base_radius * 1.2)
        elif gesture == GestureType.SCROLL:
            main_color = QColor("#a371f7") # Purple scroll
        elif gesture == GestureType.OPEN_PALM:
            main_color = QColor("#f85149") # Coral open palm

        # 1. Outer halo ring
        halo_pen = QPen(QColor(main_color.red(), main_color.green(), main_color.blue(), 60), 4)
        painter.setPen(halo_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), base_radius + 6, base_radius + 6)

        # 2. Main cursor circle
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.setBrush(QBrush(main_color))
        painter.drawEllipse(QPoint(cx, cy), base_radius, base_radius)

        # 3. Center precision dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(QPoint(cx, cy), 3, 3)

        # 4. State badge text
        state_text = ""
        if gesture == GestureType.PINCH_CLICK:
            state_text = "CLICK"
        elif gesture == GestureType.DOUBLE_CLICK:
            state_text = "DBL CLICK"
        elif gesture == GestureType.DRAG:
            state_text = "DRAG"
        elif gesture == GestureType.SCROLL:
            state_text = "SCROLL"
        elif gesture == GestureType.OPEN_PALM:
            state_text = "MENU"

        if state_text:
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            painter.setPen(QPen(Qt.white))
            painter.drawText(cx + base_radius + 8, cy + 5, state_text)

        painter.end()
