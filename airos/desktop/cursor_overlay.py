"""
AirOS Touchless Adaptive Cursor Overlay with Live Charging Radial Progress.
Draws:
- Real-time gesture state
- Dynamic charging dwell ring (fills up 0-360 deg when hovering to click)
- Pinch click green flash
- Drag indicator
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
        self.dwell_progress = 0.0
        self.cursor_visible = True
        self.is_large_target = False

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
        self.dwell_progress = getattr(event, "dwell_progress", 0.0)
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

        base_radius = 18 if not self.is_large_target else 26
        gesture = self.gesture_event.gesture

        main_color = QColor(self.theme.get("cursor_color", "#00f0ff"))

        if gesture in (GestureType.PINCH_CLICK, GestureType.DWELL_CLICK, GestureType.DOUBLE_CLICK):
            main_color = QColor("#3fb950") # Bright green click flash
            base_radius = int(base_radius * 0.8)
        elif gesture == GestureType.DRAG:
            main_color = QColor("#f59e0b") # Amber drag
            base_radius = int(base_radius * 1.25)
        elif gesture == GestureType.SCROLL:
            main_color = QColor("#a855f7") # Purple scroll
        elif gesture == GestureType.OPEN_PALM:
            main_color = QColor("#ef4444")

        # 1. Outer halo ring
        halo_pen = QPen(QColor(main_color.red(), main_color.green(), main_color.blue(), 50), 4)
        painter.setPen(halo_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), base_radius + 6, base_radius + 6)

        # 2. Live Radial Dwell Charging Arc (Hover to click feedback)
        if self.dwell_progress > 0.02:
            charge_pen = QPen(QColor("#f59e0b"), 4)
            charge_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(charge_pen)
            painter.setBrush(Qt.NoBrush)
            arc_radius = base_radius + 9
            rect = QRectF(cx - arc_radius, cy - arc_radius, arc_radius * 2, arc_radius * 2)
            # 16ths of a degree (span = dwell_progress * 360 * 16)
            span_angle = int(-self.dwell_progress * 360 * 16)
            painter.drawArc(rect, 90 * 16, span_angle)

        # 3. Main cursor circle with soft glow
        painter.setPen(QPen(QColor(255, 255, 255, 230), 2))
        painter.setBrush(QBrush(main_color))
        painter.drawEllipse(QPoint(cx, cy), base_radius, base_radius)

        # 4. Center precision dot
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(QPoint(cx, cy), 3, 3)

        # 5. State badge text
        state_text = ""
        if gesture in (GestureType.PINCH_CLICK, GestureType.DWELL_CLICK):
            state_text = "✓ CLICK"
        elif gesture == GestureType.DOUBLE_CLICK:
            state_text = "DBL CLICK"
        elif gesture == GestureType.DRAG:
            state_text = "DRAG"
        elif gesture == GestureType.SCROLL:
            state_text = "SCROLL"
        elif self.dwell_progress > 0.15:
            state_text = f"Holding... {int(self.dwell_progress * 100)}%"

        if state_text:
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            # Text shadow
            painter.setPen(QPen(QColor(0, 0, 0, 180)))
            painter.drawText(cx + base_radius + 11, cy + 6, state_text)
            painter.setPen(QPen(Qt.white))
            painter.drawText(cx + base_radius + 10, cy + 5, state_text)

        painter.end()
