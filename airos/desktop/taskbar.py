"""
AirOS Windows 11 Fluent Centered Taskbar & System Tray.
Features:
- Centered Fluent Taskbar with Windows 11 Start icon, Search, and Pinned App icons
- Active window indicators (glowing indicator pills under open/focused apps)
- Windows 11 Widgets / Weather pill on left
- System Tray on right with Keyboard toggle, Windows Bridge toggle, Control Center, and Live Clock
- Show Desktop peek bar on far right edge
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QLabel, QWidget, QSizePolicy, QVBoxLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from airos.desktop.voice_hud import VoiceHUDWidget

PINNED_APPS = [
    {"id": "files", "name": "File Explorer", "icon": "📁"},
    {"id": "air_draw", "name": "Draw on Screen", "icon": "✏️"},
    {"id": "browser", "name": "Web Browser", "icon": "🧭"},
    {"id": "notes", "name": "AirNotes", "icon": "📝"},
    {"id": "calc", "name": "Calculator", "icon": "🧮"},
    {"id": "gallery", "name": "Photos", "icon": "🖼️"},
    {"id": "music", "name": "Music", "icon": "🎵"},
    {"id": "persona", "name": "Persona AI", "icon": "👩‍🚀"},
    {"id": "microsoft", "name": "Microsoft 365", "icon": "🏢"},
    {"id": "settings", "name": "Settings", "icon": "⚙️"},
]


class Taskbar(QFrame):
    """Windows 11 Centered Fluent Desktop Taskbar."""

    start_clicked = Signal()
    workspace_changed = Signal(int)
    window_tab_clicked = Signal(str)
    keyboard_toggle_clicked = Signal()
    control_center_clicked = Signal()
    desktop_toggle_clicked = Signal()
    draw_toggle_clicked = Signal()

    def __init__(self, parent=None, theme: dict = None, app_registry: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.app_registry = app_registry or PINNED_APPS
        self.active_workspace = 0
        self.running_apps = set() # set of app_ids that have open windows
        self.active_app_id: Optional[str] = None
        self.app_buttons: Dict[str, QPushButton] = {}
        self.app_indicator_dots: Dict[str, QLabel] = {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("Taskbar")
        self.setFixedHeight(54)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(12, 0, 12, 0)
        root_layout.setSpacing(0)

        # ---------------- 1. Left Section (Widgets & Workspaces) ----------------
        self.left_box = QWidget()
        left_layout = QHBoxLayout(self.left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Windows 11 Weather / Widget pill
        self.widget_btn = QPushButton("⛅ 24°C  AirOS")
        self.widget_btn.setFixedHeight(36)
        self.widget_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                color: #2c3e50;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.22);
            }
        """)
        self.widget_btn.clicked.connect(self.start_clicked.emit)
        left_layout.addWidget(self.widget_btn)

        # Workspace pills (Space 1, Space 2)
        self.ws1_btn = QPushButton("Space 1")
        self.ws2_btn = QPushButton("Space 2")
        for btn in (self.ws1_btn, self.ws2_btn):
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #555555;
                    border: 1px solid rgba(0, 0, 0, 0.10);
                    border-radius: 6px;
                    padding: 2px 8px;
                    font-size: 11px;
                }
                QPushButton:hover { background: rgba(255, 255, 255, 0.2); color: #000; }
            """)
        self.ws1_btn.clicked.connect(lambda: self.set_workspace(0))
        self.ws2_btn.clicked.connect(lambda: self.set_workspace(1))
        left_layout.addWidget(self.ws1_btn)
        left_layout.addWidget(self.ws2_btn)
        self._update_workspace_ui()

        root_layout.addWidget(self.left_box, 1)

        # ---------------- 2. Center Section (Windows 11 Centered Dock) ----------------
        self.center_box = QWidget()
        center_layout = QHBoxLayout(self.center_box)
        center_layout.setContentsMargins(0, 4, 0, 4)
        center_layout.setSpacing(6)
        center_layout.setAlignment(Qt.AlignCenter)

        # Windows 11 Start Button
        self.btn_start = QPushButton("💠")
        self.btn_start.setFixedSize(40, 40)
        self.btn_start.setToolTip("Start (Open AirOS Launcher)")
        self.btn_start.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0078d4, stop:1 #005a9e);
                color: white;
                font-size: 18px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1084d8, stop:1 #0067c0);
                border-color: #ffffff;
            }
            QPushButton:pressed {
                background: #004578;
            }
        """)
        self.btn_start.clicked.connect(self.start_clicked.emit)
        center_layout.addWidget(self.btn_start)

        # Windows 11 Search Button
        self.btn_search = QPushButton("🔍")
        self.btn_search.setFixedSize(40, 40)
        self.btn_search.setToolTip("Search Apps and Files")
        self.btn_search.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.15);
                color: #222222;
                font-size: 15px;
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.35);
                border-color: rgba(0, 103, 192, 0.4);
            }
        """)
        self.btn_search.clicked.connect(self.start_clicked.emit)
        center_layout.addWidget(self.btn_search)

        # Pinned App Icons (Centered)
        for app in PINNED_APPS:
            app_id = app["id"]
            app_container = QWidget()
            app_container.setFixedSize(42, 46)
            c_layout = QVBoxLayout(app_container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(1)
            c_layout.setAlignment(Qt.AlignCenter)

            btn = QPushButton(app["icon"])
            btn.setFixedSize(38, 38)
            btn.setToolTip(app["name"])
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    font-size: 20px;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.28);
                    border: 1px solid rgba(0, 0, 0, 0.08);
                }
                QPushButton:pressed {
                    background: rgba(0, 0, 0, 0.06);
                }
            """)
            btn.clicked.connect(lambda checked, aid=app_id: self.window_tab_clicked.emit(aid))
            c_layout.addWidget(btn)

            # Active indicator pill/dot beneath icon
            dot = QLabel()
            dot.setFixedSize(14, 3)
            dot.setStyleSheet("background: transparent; border-radius: 1px;")
            c_layout.addWidget(dot, 0, Qt.AlignCenter)

            self.app_buttons[app_id] = btn
            self.app_indicator_dots[app_id] = dot
            center_layout.addWidget(app_container)

        root_layout.addWidget(self.center_box, 2)

        # ---------------- 3. Right Section (System Tray & Windows 11 Clock) ----------------
        self.right_box = QWidget()
        right_layout = QHBoxLayout(self.right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Draw on Screen Quick Toggle Button
        self.btn_draw = QPushButton("✏️ Draw")
        self.btn_draw.setFixedHeight(34)
        self.btn_draw.setToolTip("Toggle Draw on Screen (Mid-Air Annotations & Whiteboard)")
        self.btn_draw.setStyleSheet("""
            QPushButton {
                background: rgba(13, 148, 136, 0.18);
                color: #0f766e;
                border: 1px solid rgba(13, 148, 136, 0.35);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QPushButton:hover { background: rgba(13, 148, 136, 0.32); }
        """)
        self.btn_draw.clicked.connect(self.draw_toggle_clicked.emit)
        right_layout.addWidget(self.btn_draw)

        # Voice Assistant HUD
        self.voice_hud = VoiceHUDWidget(self, theme=self.theme)
        right_layout.addWidget(self.voice_hud)

        # Virtual Keyboard Button
        self.btn_kbd = QPushButton("⌨️")
        self.btn_kbd.setFixedSize(34, 34)
        self.btn_kbd.setToolTip("AirType Virtual Keyboard")
        self.btn_kbd.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 6px;
                font-size: 15px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.28); }
        """)
        self.btn_kbd.clicked.connect(self.keyboard_toggle_clicked.emit)
        right_layout.addWidget(self.btn_kbd)

        # Windows Bridge Tray Indicator Pill
        self.btn_bridge = QPushButton("🪟 Desktop")
        self.btn_bridge.setFixedHeight(34)
        self.btn_bridge.setToolTip("Windows Native Mouse & Keyboard Bridge Status")
        self.btn_bridge.setStyleSheet("""
            QPushButton {
                background: rgba(0, 103, 192, 0.12);
                color: #0067c0;
                border: 1px solid rgba(0, 103, 192, 0.25);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }
            QPushButton:hover { background: rgba(0, 103, 192, 0.25); }
        """)
        self.btn_bridge.clicked.connect(self.control_center_clicked.emit)
        right_layout.addWidget(self.btn_bridge)

        # Control Center Button
        self.btn_cc = QPushButton("🎛️")
        self.btn_cc.setFixedSize(34, 34)
        self.btn_cc.setToolTip("AirOS Spatial Control Center")
        self.btn_cc.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 6px;
                font-size: 15px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.28); }
        """)
        self.btn_cc.clicked.connect(self.control_center_clicked.emit)
        right_layout.addWidget(self.btn_cc)

        # Windows 11 Live 2-line Clock & Date
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("color: #1a1a1a; font-weight: 600; font-size: 11px; line-height: 12px;")
        right_layout.addWidget(self.clock_label)

        # Far-right Desktop Peek Strip
        self.btn_peek = QPushButton()
        self.btn_peek.setFixedSize(6, 44)
        self.btn_peek.setToolTip("Show Desktop")
        self.btn_peek.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.08);
                border: none;
                border-radius: 2px;
            }
            QPushButton:hover { background: #0067c0; }
        """)
        self.btn_peek.clicked.connect(self.desktop_toggle_clicked.emit)
        right_layout.addWidget(self.btn_peek)

        root_layout.addWidget(self.right_box, 1)

        # Live clock timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

        self._apply_theme_style()

    def update_theme(self, theme: dict):
        self.theme = theme
        self._apply_theme_style()

    def _apply_theme_style(self):
        tb_bg = self.theme.get("taskbar_bg", "rgba(243, 246, 251, 0.88)")
        text_color = self.theme.get("text_primary", "#1b1b1b")
        border = self.theme.get("card_border", "rgba(0, 0, 0, 0.10)")

        self.setStyleSheet(f"""
            QFrame#Taskbar {{
                background-color: {tb_bg};
                border-top: 1px solid {border};
            }}
        """)
        self.clock_label.setStyleSheet(f"color: {text_color}; font-weight: 600; font-size: 11px;")
        self.widget_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.14);
                color: {text_color};
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid {border};
                border-radius: 8px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.28);
            }}
        """)

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(now.strftime("%I:%M %p\n%m/%d/%Y"))

    def set_workspace(self, ws: int):
        self.active_workspace = ws
        self._update_workspace_ui()
        self.workspace_changed.emit(ws)

    def _update_workspace_ui(self):
        accent = self.theme.get("accent", "#0067c0")
        active_style = f"background-color: {accent}; color: white; font-weight: bold; border-radius: 6px; padding: 2px 8px; border: none;"
        inactive_style = "background: transparent; color: #666666; border: 1px solid rgba(0, 0, 0, 0.10); border-radius: 6px; padding: 2px 8px;"
        self.ws1_btn.setStyleSheet(active_style if self.active_workspace == 0 else inactive_style)
        self.ws2_btn.setStyleSheet(active_style if self.active_workspace == 1 else inactive_style)

    def add_window_tab(self, app_id: str, title: str):
        self.running_apps.add(app_id)
        self.active_app_id = app_id
        self._update_app_indicators()

    def remove_window_tab(self, app_id: str):
        self.running_apps.discard(app_id)
        if self.active_app_id == app_id:
            self.active_app_id = next(iter(self.running_apps)) if self.running_apps else None
        self._update_app_indicators()

    def set_active_app(self, app_id: str):
        self.active_app_id = app_id
        self._update_app_indicators()

    def _update_app_indicators(self):
        accent = self.theme.get("accent", "#0067c0")
        for aid, dot in self.app_indicator_dots.items():
            if aid == self.active_app_id:
                dot.setStyleSheet(f"background: {accent}; border-radius: 1px; min-width: 14px; min-height: 3px;")
            elif aid in self.running_apps:
                dot.setStyleSheet("background: rgba(120, 120, 120, 0.7); border-radius: 1px; min-width: 6px; min-height: 3px;")
            else:
                dot.setStyleSheet("background: transparent;")

    def update_bridge_status(self, enabled: bool):
        if enabled:
            self.btn_bridge.setText("🪟 Desktop (ON)")
            self.btn_bridge.setStyleSheet("""
                QPushButton {
                    background: #107c41;
                    color: white;
                    border: 1px solid #107c41;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 8px;
                }
                QPushButton:hover { background: #0b6a37; }
            """)
        else:
            self.btn_bridge.setText("🪟 Desktop")
            self.btn_bridge.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 103, 192, 0.12);
                    color: #0067c0;
                    border: 1px solid rgba(0, 103, 192, 0.25);
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 8px;
                }
                QPushButton:hover { background: rgba(0, 103, 192, 0.25); }
            """)
