"""
AirOS Taskbar & System Tray.
Houses the Start button, running window tabs, clock, workspace switcher,
and quick settings indicators.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QLabel, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QColor

class Taskbar(QFrame):
    """Bottom desktop taskbar managing workspaces, apps, and system time."""

    start_clicked = Signal()
    workspace_changed = Signal(int) # workspace index (0 or 1)
    window_tab_clicked = Signal(str) # app_id
    keyboard_toggle_clicked = Signal()

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.active_workspace = 0
        self.window_buttons = {} # app_id -> QPushButton
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("Taskbar")
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 16, 4)
        layout.setSpacing(10)

        # Start Button
        self.btn_start = QPushButton("💠 AirOS")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #388bfd);
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: #58a6ff;
            }
        """)
        self.btn_start.clicked.connect(self.start_clicked.emit)
        layout.addWidget(self.btn_start)

        # Workspaces Switcher (Workspace 1 & 2)
        self.ws1_btn = QPushButton("Space 1")
        self.ws2_btn = QPushButton("Space 2")
        for btn in (self.ws1_btn, self.ws2_btn):
            btn.setFixedHeight(32)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #21262d;
                    color: #8b949e;
                    border: 1px solid #30363d;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                }
                QPushButton:hover { color: #f0f6fc; }
            """)
        self.ws1_btn.clicked.connect(lambda: self.set_workspace(0))
        self.ws2_btn.clicked.connect(lambda: self.set_workspace(1))
        layout.addWidget(self.ws1_btn)
        layout.addWidget(self.ws2_btn)

        self._update_workspace_ui()

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #30363d;")
        layout.addWidget(sep)

        # Running window tabs area
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_layout.setSpacing(6)
        layout.addWidget(self.tabs_container)

        layout.addStretch()

        # Virtual Keyboard Quick Button
        self.btn_kbd = QPushButton("⌨ AirType")
        self.btn_kbd.setFixedHeight(32)
        self.btn_kbd.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #58a6ff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_kbd.clicked.connect(self.keyboard_toggle_clicked.emit)
        layout.addWidget(self.btn_kbd)

        # Clock & Date
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("color: #f0f6fc; font-weight: 600; font-size: 12px;")
        layout.addWidget(self.clock_label)

        # Timer for live clock update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

        self.setStyleSheet("""
            QFrame#Taskbar {
                background-color: rgba(22, 27, 34, 0.92);
                border-top: 1px solid #30363d;
            }
        """)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%I:%M %p\n%b %d"))

    def set_workspace(self, ws: int):
        self.active_workspace = ws
        self._update_workspace_ui()
        self.workspace_changed.emit(ws)

    def _update_workspace_ui(self):
        active_style = "background-color: #1f6feb; color: white; font-weight: bold; border-radius: 4px; padding: 2px 8px;"
        inactive_style = "background-color: #21262d; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; padding: 2px 8px;"
        self.ws1_btn.setStyleSheet(active_style if self.active_workspace == 0 else inactive_style)
        self.ws2_btn.setStyleSheet(active_style if self.active_workspace == 1 else inactive_style)

    def add_window_tab(self, app_id: str, title: str):
        if app_id in self.window_buttons:
            return
        btn = QPushButton(title)
        btn.setFixedHeight(34)
        btn.setMaximumWidth(160)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #f0f6fc;
                border-bottom: 2px solid #58a6ff;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        btn.clicked.connect(lambda: self.window_tab_clicked.emit(app_id))
        self.tabs_layout.addWidget(btn)
        self.window_buttons[app_id] = btn

    def remove_window_tab(self, app_id: str):
        if app_id in self.window_buttons:
            btn = self.window_buttons.pop(app_id)
            self.tabs_layout.removeWidget(btn)
            btn.deleteLater()
