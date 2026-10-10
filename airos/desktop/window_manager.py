"""
AirOS Window Manager & AirWindow Component.
Provides draggable, resizable, minimizable, maximizable, focusable and snapable windows.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize
from PySide6.QtGui import QColor, QFont, QCursor

class AirWindow(QFrame):
    """A fully managed desktop application window."""

    window_closed = Signal(str)      # app_id
    window_focused = Signal(str)     # app_id
    window_minimized = Signal(str)   # app_id
    window_snapped = Signal(str, str) # app_id, snap_direction ("left", "right", "max")

    def __init__(self, app_id: str, title: str, content_widget: QWidget, parent=None, theme: dict = None):
        super().__init__(parent)
        self.app_id = app_id
        self.window_title = title
        self.content_widget = content_widget
        self.theme = theme or {}
        
        # State
        self.is_maximized_state = False
        self.saved_geometry = QRect(100, 100, 680, 480)
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.is_resizing = False
        self.resize_margin = 12

        self._init_ui()

    def _init_ui(self):
        self.setObjectName("AirWindow")
        self.setMouseTracking(True)
        self.setGeometry(self.saved_geometry)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header / Title Bar
        self.title_bar = QFrame(self)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(38)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)
        title_layout.setSpacing(8)

        # Title icon & text
        self.title_label = QLabel(self.window_title, self.title_bar)
        self.title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.title_label.setStyleSheet("color: #f0f6fc;")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        # Window Controls (Minimize, Maximize/Restore, Close)
        btn_size = QSize(28, 26)

        self.btn_min = QPushButton("─", self.title_bar)
        self.btn_min.setFixedSize(btn_size)
        self.btn_min.setToolTip("Minimize")
        self.btn_min.clicked.connect(self.minimize_window)
        title_layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("□", self.title_bar)
        self.btn_max.setFixedSize(btn_size)
        self.btn_max.setToolTip("Maximize / Restore")
        self.btn_max.clicked.connect(self.toggle_maximize)
        title_layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕", self.title_bar)
        self.btn_close.setFixedSize(btn_size)
        self.btn_close.setToolTip("Close")
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.clicked.connect(self.close_window)
        title_layout.addWidget(self.btn_close)

        layout.addWidget(self.title_bar)

        # Content area
        self.content_container = QFrame(self)
        self.content_container.setObjectName("ContentContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(1, 1, 1, 1)
        content_layout.addWidget(self.content_widget)
        layout.addWidget(self.content_container)

        self._apply_styles()

    def _apply_styles(self):
        bg = self.theme.get("window_bg", "#161b22")
        header = self.theme.get("window_header", "#21262d")
        border = self.theme.get("card_border", "#30363d")
        accent = self.theme.get("accent", "#58a6ff")

        self.setStyleSheet(f"""
            QFrame#AirWindow {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#TitleBar {{
                background-color: {header};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid {border};
            }}
            QPushButton {{
                background: transparent;
                color: #8b949e;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #30363d;
                color: #f0f6fc;
            }}
            QPushButton#CloseBtn:hover {{
                background-color: #f85149;
                color: white;
            }}
        """)

    def bring_to_front(self):
        self.raise_()
        self.window_focused.emit(self.app_id)

    def close_window(self):
        self.window_closed.emit(self.app_id)
        self.hide()
        self.deleteLater()

    def minimize_window(self):
        self.hide()
        self.window_minimized.emit(self.app_id)

    def toggle_maximize(self):
        if not self.parent():
            return
        parent_rect = self.parent().rect()
        # Leave room for taskbar at bottom (e.g. 52px)
        work_area = QRect(0, 0, parent_rect.width(), parent_rect.height() - 52)

        if not self.is_maximized_state:
            self.saved_geometry = self.geometry()
            self.setGeometry(work_area)
            self.is_maximized_state = True
            self.btn_max.setText("❐")
        else:
            self.setGeometry(self.saved_geometry)
            self.is_maximized_state = False
            self.btn_max.setText("□")

    def snap_to(self, direction: str):
        if not self.parent():
            return
        parent_rect = self.parent().rect()
        work_h = parent_rect.height() - 52
        work_w = parent_rect.width()

        if direction == "left":
            self.setGeometry(0, 0, work_w // 2, work_h)
            self.is_maximized_state = False
            self.btn_max.setText("□")
        elif direction == "right":
            self.setGeometry(work_w // 2, 0, work_w // 2, work_h)
            self.is_maximized_state = False
            self.btn_max.setText("□")
        elif direction == "max":
            self.toggle_maximize()

        self.window_snapped.emit(self.app_id, direction)

    # Mouse & Touchless Interaction
    def mousePressEvent(self, event):
        self.bring_to_front()
        if event.button() == Qt.LeftButton:
            # Check if clicking title bar
            if event.position().y() <= 38:
                self.is_dragging = True
                self.drag_start_pos = event.position().toPoint()
            # Check bottom-right corner for resizing
            elif (self.width() - event.position().x() < self.resize_margin and 
                  self.height() - event.position().y() < self.resize_margin):
                self.is_resizing = True
                self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.position().toPoint() - self.drag_start_pos
            new_pos = self.pos() + delta
            self.move(new_pos)
            
            # Snap check on screen borders
            if self.parent():
                if self.x() <= 10:
                    pass # Can indicate snap preview
                elif (self.x() + self.width()) >= (self.parent().width() - 10):
                    pass
        elif self.is_resizing:
            delta = event.position().toPoint() - self.drag_start_pos
            new_w = max(360, self.width() + delta.x())
            new_h = max(240, self.height() + delta.y())
            self.resize(new_w, new_h)
            self.drag_start_pos = event.position().toPoint()
        else:
            # Change cursor for resize handle
            if (self.width() - event.position().x() < self.resize_margin and 
                self.height() - event.position().y() < self.resize_margin):
                self.setCursor(Qt.SizeFDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            if self.parent():
                # Window snapping trigger
                if self.x() < 15:
                    self.snap_to("left")
                elif (self.x() + self.width()) > (self.parent().width() - 15):
                    self.snap_to("right")
                elif self.y() < 10:
                    self.snap_to("max")

        self.is_resizing = False
        super().mouseReleaseEvent(event)
