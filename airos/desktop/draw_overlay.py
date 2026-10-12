"""
AirOS Draw on Screen — Mid-Air Sketch, Annotate & Whiteboard System.
Allows touchless sketching, presentation laser pointer, mid-air annotations,
color palettes, and smart geometric shape snapping directly over the screen.
"""

import os
import time
import math
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QToolButton, QButtonGroup, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QTimer, Signal
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QFont, QPixmap, QImage
)
from airos.gestures.state_machine import GestureType, GestureEvent


class SmartShapeRecognizer:
    """
    Intelligent geometry engine that detects hand-drawn shapes in mid-air:
    - Straight Lines
    - Circles / Ellipses
    - Rectangles / Boxes
    """

    @staticmethod
    def recognize(points: List[QPointF]) -> Optional[Dict[str, Any]]:
        if len(points) < 8:
            return None

        p_start = points[0]
        p_end = points[-1]
        chord_len = math.hypot(p_end.x() - p_start.x(), p_end.y() - p_start.y())

        # Compute total perimeter length
        arc_len = 0.0
        for i in range(1, len(points)):
            arc_len += math.hypot(points[i].x() - points[i - 1].x(), points[i].y() - points[i - 1].y())

        if arc_len <= 15.0:
            return None

        # 1. Straight Line Check: chord length is almost equal to total path length
        if chord_len / arc_len > 0.88:
            return {
                "type": "line",
                "start": p_start,
                "end": p_end
            }

        # 2. Closed Shape Check: start and end points are close to each other
        if chord_len / arc_len < 0.22:
            xs = [p.x() for p in points]
            ys = [p.y() for p in points]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            center = QPointF(cx, cy)

            radii = [math.hypot(p.x() - cx, p.y() - cy) for p in points]
            avg_r = sum(radii) / len(radii)
            if avg_r > 10.0:
                variance = sum((r - avg_r) ** 2 for r in radii) / len(radii)
                std_dev = math.sqrt(variance)
                
                # Low radius variation from centroid -> Circle / Ellipse
                if (std_dev / avg_r) < 0.22:
                    rx = (max(xs) - min(xs)) / 2.0
                    ry = (max(ys) - min(ys)) / 2.0
                    return {
                        "type": "ellipse",
                        "center": center,
                        "rx": max(avg_r, rx),
                        "ry": max(avg_r, ry)
                    }

            # 3. Rectangle Check
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            rect_w = max_x - min_x
            rect_h = max_y - min_y
            if rect_w > 25 and rect_h > 25:
                # Approximate bounding box perimeter
                box_perimeter = 2 * (rect_w + rect_h)
                if abs(arc_len - box_perimeter) / box_perimeter < 0.35:
                    return {
                        "type": "rect",
                        "rect": QRectF(min_x, min_y, rect_w, rect_h)
                    }

        return None


class ScreenDrawBanner(QFrame):
    """
    Sleek top banner matching the user reference UI:
    [✏️] Draw on screen
         Sketch and annotate anywhere, mid-air.
    Plus integrated floating controls for tools, colors, and snapshot saving.
    """

    color_selected = Signal(str)
    width_selected = Signal(int)
    tool_selected = Signal(str) # "pen", "highlighter", "laser", "eraser"
    shape_snap_toggled = Signal(bool)
    clear_requested = Signal()
    undo_requested = Signal()
    save_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScreenDrawBanner")
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.shape_snap_enabled = False
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(14)

        # 1. Header Card Badge (Matching exact reference image)
        card_box = QHBoxLayout()
        card_box.setSpacing(10)

        # Teal square icon with pencil
        self.icon_badge = QLabel("✏️")
        self.icon_badge.setFixedSize(36, 36)
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0d9488, stop:1 #0f766e);
            color: white;
            font-size: 18px;
            border: 2px solid #2dd4bf;
            border-radius: 10px;
        """)
        card_box.addWidget(self.icon_badge)

        # Titles
        titles_layout = QVBoxLayout()
        titles_layout.setSpacing(1)
        titles_layout.setAlignment(Qt.AlignVCenter)

        title_lbl = QLabel("Draw on screen")
        title_lbl.setStyleSheet("""
            color: #ffffff;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: 700;
        """)
        titles_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Sketch and annotate anywhere, mid-air.")
        sub_lbl.setStyleSheet("""
            color: #94a3b8;
            font-family: 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: 500;
        """)
        titles_layout.addWidget(sub_lbl)
        card_box.addLayout(titles_layout)

        layout.addLayout(card_box)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.VLine)
        div1.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
        layout.addWidget(div1)

        # 2. Tool buttons (Pen, Highlighter, Laser, Eraser)
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(4)

        self.btn_pen = self._create_btn("✏️ Pen", lambda: self.tool_selected.emit("pen"), active=True)
        self.btn_highlighter = self._create_btn("🖍️ Highlight", lambda: self.tool_selected.emit("highlighter"))
        self.btn_laser = self._create_btn("🌟 Laser", lambda: self.tool_selected.emit("laser"))
        self.btn_eraser = self._create_btn("🧹 Eraser", lambda: self.tool_selected.emit("eraser"))

        for b in (self.btn_pen, self.btn_highlighter, self.btn_laser, self.btn_eraser):
            tools_layout.addWidget(b)
        layout.addLayout(tools_layout)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.VLine)
        div2.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
        layout.addWidget(div2)

        # 3. Vibrant Color Swatches (Default Blue matching image)
        colors_layout = QHBoxLayout()
        colors_layout.setSpacing(6)
        colors = [
            ("#1e60ff", "Vibrant Blue"),  # Exactly matches the blue in screenshot
            ("#10b981", "Emerald Green"),
            ("#ef4444", "Crimson Red"),
            ("#f59e0b", "Cyber Amber"),
            ("#a855f7", "Electric Purple"),
            ("#ffffff", "Bright White")
        ]
        self.color_buttons = []
        for hex_col, name in colors:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setToolTip(name)
            border_col = "#ffffff" if hex_col == "#1e60ff" else "transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_col};
                    border: 2px solid {border_col};
                    border-radius: 11px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            btn.clicked.connect(lambda ch, c=hex_col, b=btn: self._on_color_click(c, b))
            colors_layout.addWidget(btn)
            self.color_buttons.append(btn)
        layout.addLayout(colors_layout)

        # Divider
        div3 = QFrame()
        div3.setFrameShape(QFrame.VLine)
        div3.setStyleSheet("color: rgba(255, 255, 255, 0.2);")
        layout.addWidget(div3)

        # 4. Actions: Shape Snap, Undo, Clear, Save, Close
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)

        self.btn_snap = self._create_btn("✨ Smart Snap", self._toggle_snap)
        self.btn_snap.setToolTip("Auto-snap hand-drawn lines, circles, and boxes into crisp geometry")
        actions_layout.addWidget(self.btn_snap)

        btn_undo = self._create_btn("↩️ Undo", self.undo_requested.emit)
        actions_layout.addWidget(btn_undo)

        btn_clear = self._create_btn("🗑️ Clear", self.clear_requested.emit)
        actions_layout.addWidget(btn_clear)

        btn_save = self._create_btn("💾 Save", self.save_requested.emit)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #0d9488;
                color: #ffffff;
                border: 1px solid #14b8a6;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: #0f766e; }
        """)
        actions_layout.addWidget(btn_save)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setToolTip("Exit Draw on Screen Mode")
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.2);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
            }
        """)
        btn_close.clicked.connect(self.close_requested.emit)
        actions_layout.addWidget(btn_close)

        layout.addLayout(actions_layout)

        self.setStyleSheet("""
            QFrame#ScreenDrawBanner {
                background-color: rgba(15, 23, 42, 0.94);
                border: 1px solid rgba(45, 212, 191, 0.35);
                border-radius: 14px;
            }
        """)

    def _create_btn(self, text: str, callback, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {"rgba(13, 148, 136, 0.35)" if active else "rgba(255, 255, 255, 0.08)"};
                color: {"#2dd4bf" if active else "#e2e8f0"};
                border: 1px solid {"#2dd4bf" if active else "rgba(255, 255, 255, 0.12)"};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.18);
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def _on_color_click(self, col: str, clicked_btn: QPushButton):
        for b in self.color_buttons:
            b.setStyleSheet(b.styleSheet().replace("border: 2px solid #ffffff;", "border: 2px solid transparent;"))
        clicked_btn.setStyleSheet(clicked_btn.styleSheet().replace("border: 2px solid transparent;", "border: 2px solid #ffffff;"))
        self.color_selected.emit(col)

    def _toggle_snap(self):
        self.shape_snap_enabled = not self.shape_snap_enabled
        if self.shape_snap_enabled:
            self.btn_snap.setStyleSheet("""
                QPushButton {
                    background: rgba(45, 212, 191, 0.25);
                    color: #2dd4bf;
                    border: 1px solid #2dd4bf;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        else:
            self.btn_snap.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: #e2e8f0;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
        self.shape_snap_toggled.emit(self.shape_snap_enabled)

    def set_tool(self, tool_name: str):
        btns = [
            ("pen", self.btn_pen),
            ("highlighter", self.btn_highlighter),
            ("laser", self.btn_laser),
            ("eraser", self.btn_eraser)
        ]
        for name, btn in btns:
            if name == tool_name:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(13, 148, 136, 0.35);
                        color: #2dd4bf;
                        border: 1px solid #2dd4bf;
                        border-radius: 6px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        color: #e2e8f0;
                        border: 1px solid rgba(255, 255, 255, 0.12);
                        border-radius: 6px;
                        padding: 3px 8px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                """)


class ScreenDrawOverlay(QWidget):
    """
    Transparent full-screen interactive overlay for mid-air screen drawing.
    Intercepts touchless hand gestures and paints anti-aliased strokes,
    presentation laser trails, or geometric snapped shapes.
    """

    state_changed = Signal(str) # "draw", "hover", "erase"
    closed = Signal()
    snapshot_saved = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setMouseTracking(True)

        # Drawing state
        self.active_tool = "pen"
        self.current_color = QColor("#1e60ff") # Vibrant royal blue
        self.stroke_width = 6
        self.smart_snap_enabled = False

        self.strokes: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []
        self.current_stroke: Optional[Dict[str, Any]] = None

        # Laser trail dots: (QPointF, timestamp)
        self.laser_points: List[Tuple[QPointF, float]] = []

        # Mid-air gesture tracking
        self.is_pinched_down = False
        self.last_draw_pos: Optional[QPointF] = None

        # Timer to smoothly fade laser trails
        self.laser_timer = QTimer(self)
        self.laser_timer.timeout.connect(self._update_laser_trails)
        self.laser_timer.start(30)

        # Floating Top Banner (Matches User Image)
        self.banner = ScreenDrawBanner(self)
        self.banner.color_selected.connect(self.set_color)
        self.banner.tool_selected.connect(self.set_tool)
        self.banner.shape_snap_toggled.connect(self.set_smart_snap)
        self.banner.clear_requested.connect(self.clear_canvas)
        self.banner.undo_requested.connect(self.undo_stroke)
        self.banner.save_requested.connect(self.save_snapshot)
        self.banner.close_requested.connect(self.hide_overlay)

        self.hide()

    def set_color(self, hex_color: str):
        self.current_color = QColor(hex_color)

    def set_tool(self, tool_name: str):
        self.active_tool = tool_name
        self.banner.set_tool(tool_name)
        if tool_name == "eraser":
            self.state_changed.emit("erase")
        else:
            self.state_changed.emit("hover")

    def set_smart_snap(self, enabled: bool):
        self.smart_snap_enabled = enabled

    def show_overlay(self):
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.raise_()
        self.show()
        self._reposition_banner()
        self.state_changed.emit("hover")

    def hide_overlay(self):
        self.hide()
        self.closed.emit()

    def clear_canvas(self):
        self.strokes.clear()
        self.redo_stack.clear()
        self.laser_points.clear()
        self.update()

    def undo_stroke(self):
        if self.strokes:
            self.redo_stack.append(self.strokes.pop())
            self.update()

    def redo_stroke(self):
        if self.redo_stack:
            self.strokes.append(self.redo_stack.pop())
            self.update()

    def _reposition_banner(self):
        bw = min(880, self.width() - 40)
        bx = (self.width() - bw) // 2
        by = 16
        self.banner.setGeometry(bx, by, bw, self.banner.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_banner()

    def _update_laser_trails(self):
        if not self.laser_points:
            return
        now = time.time()
        # Keep dots younger than 1.2 seconds
        self.laser_points = [p for p in self.laser_points if now - p[1] < 1.2]
        self.update()

    def process_gesture_input(self, event: GestureEvent):
        """Processes live hand gesture events for mid-air sketching."""
        if not self.isVisible():
            return

        cx = event.cursor_pos[0] * self.width()
        cy = event.cursor_pos[1] * self.height()
        pos = QPointF(cx, cy)

        # Don't draw if hand is over banner controls
        banner_rect = self.banner.geometry()
        if banner_rect.contains(int(cx), int(cy)):
            if self.is_pinched_down:
                self._pen_up()
            return

        is_pinching = event.gesture in (
            GestureType.PINCH_CLICK, GestureType.DRAG, GestureType.DWELL_CLICK
        ) or "Pinch" in event.state_description or "Drag" in event.state_description

        if is_pinching:
            if not self.is_pinched_down:
                self._pen_down(pos)
            else:
                self._pen_move(pos)
        else:
            if self.is_pinched_down:
                self._pen_up()
            else:
                if self.active_tool == "laser":
                    self.laser_points.append((pos, time.time()))
                    self.update()

    def _pen_down(self, pos: QPointF):
        self.is_pinched_down = True
        self.last_draw_pos = pos

        if self.active_tool == "eraser":
            self._erase_at(pos)
            self.state_changed.emit("erase")
            return

        if self.active_tool == "laser":
            self.laser_points.append((pos, time.time()))
            self.state_changed.emit("draw")
            self.update()
            return

        # Start new stroke
        col = QColor(self.current_color)
        if self.active_tool == "highlighter":
            col.setAlpha(90)
            w = self.stroke_width * 3
        else:
            w = self.stroke_width

        self.current_stroke = {
            "tool": self.active_tool,
            "color": col,
            "width": w,
            "points": [pos],
            "shape": None
        }
        self.state_changed.emit("draw")
        self.update()

    def _pen_move(self, pos: QPointF):
        if not self.is_pinched_down:
            return

        if self.active_tool == "eraser":
            self._erase_at(pos)
            self.state_changed.emit("erase")
            return

        if self.active_tool == "laser":
            self.laser_points.append((pos, time.time()))
            self.state_changed.emit("draw")
            self.update()
            return

        if self.current_stroke:
            # Sub-pixel spacing to avoid redundant points
            last_p = self.current_stroke["points"][-1]
            if math.hypot(pos.x() - last_p.x(), pos.y() - last_p.y()) >= 2.0:
                self.current_stroke["points"].append(pos)
                self.state_changed.emit("draw")
                self.update()

    def _pen_up(self):
        self.is_pinched_down = False
        if self.current_stroke and len(self.current_stroke["points"]) > 1:
            # Check smart shape recognition if enabled
            if self.smart_snap_enabled:
                shape = SmartShapeRecognizer.recognize(self.current_stroke["points"])
                if shape:
                    self.current_stroke["shape"] = shape

            self.strokes.append(self.current_stroke)
            self.redo_stack.clear()

        self.current_stroke = None
        self.state_changed.emit("hover")
        self.update()

    def _erase_at(self, pos: QPointF, radius: float = 24.0):
        remaining_strokes = []
        for s in self.strokes:
            points = s.get("points", [])
            hit = False
            for p in points:
                if math.hypot(p.x() - pos.x(), p.y() - pos.y()) <= radius:
                    hit = True
                    break
            if not hit:
                remaining_strokes.append(s)
        if len(remaining_strokes) != len(self.strokes):
            self.strokes = remaining_strokes
            self.update()

    # Mouse fallback events for desktop testing without webcam
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pen_down(event.position())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_pinched_down:
            self._pen_move(event.position())
        elif self.active_tool == "laser":
            self.laser_points.append((event.position(), time.time()))
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pen_up()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 1. Render all committed strokes
        for s in self.strokes:
            self._draw_stroke(painter, s)

        # 2. Render currently active stroke
        if self.current_stroke:
            self._draw_stroke(painter, self.current_stroke)

        # 3. Render laser trail points
        now = time.time()
        for pos, t in self.laser_points:
            age = now - t
            if age < 1.2:
                alpha = int(255 * (1.0 - (age / 1.2)))
                r = max(2, int(8 * (1.0 - (age / 1.5))))
                laser_col = QColor(255, 30, 80, alpha)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(laser_col))
                painter.drawEllipse(pos, r, r)

                # Outer halo
                halo_col = QColor(255, 100, 150, int(alpha * 0.4))
                painter.setBrush(QBrush(halo_col))
                painter.drawEllipse(pos, r + 4, r + 4)

        painter.end()

    def _draw_stroke(self, painter: QPainter, stroke: Dict[str, Any]):
        col = stroke["color"]
        w = stroke["width"]
        shape = stroke.get("shape")

        pen = QPen(col, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)

        if shape:
            stype = shape.get("type")
            if stype == "line":
                painter.drawLine(shape["start"], shape["end"])
                return
            elif stype == "ellipse":
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(shape["center"], shape["rx"], shape["ry"])
                return
            elif stype == "rect":
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(shape["rect"])
                return

        points = stroke.get("points", [])
        if len(points) == 1:
            painter.drawPoint(points[0])
            return

        if len(points) > 1:
            path = QPainterPath()
            path.moveTo(points[0])
            # Smooth quadratic Bezier spline interpolation
            for i in range(1, len(points)):
                p0 = points[i - 1]
                p1 = points[i]
                mid = QPointF((p0.x() + p1.x()) * 0.5, (p0.y() + p1.y()) * 0.5)
                path.quadTo(p0, mid)
            path.lineTo(points[-1])
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)

    def save_snapshot(self):
        """Takes a full high-resolution snapshot of the annotated screen."""
        try:
            # Capture parent desktop canvas or entire window
            target_widget = self.parent() if self.parent() else self
            pixmap = target_widget.grab()

            # Ensure drawings directory exists
            docs_dir = Path.home() / ".airos" / "drawings"
            docs_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = docs_dir / f"airdraw_snapshot_{timestamp}.png"
            pixmap.save(str(filename), "PNG")

            self.snapshot_saved.emit(str(filename))
            QMessageBox.information(
                self,
                "Snapshot Saved",
                f"📸 <b>Screen Annotation Saved Successfully!</b><br><br>"
                f"File: <code>{filename.name}</code><br>"
                f"Location: <code>{docs_dir}</code>"
            )
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Could not save snapshot: {e}")
