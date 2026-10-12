"""
AirOS Windows 11 Fluent Centered Start Menu & Application Launcher.
Provides:
- Top search input
- Centered grid of Pinned Apps (Windows 11 Fluent style)
- Recommended / Recent quick tasks
- Bottom User Profile pill and Power Options
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor


class StartMenu(QFrame):
    """Windows 11 Centered Fluent Start Menu."""

    app_launched = Signal(str) # app_id
    shutdown_requested = Signal()
    lock_requested = Signal()

    def __init__(self, apps_info: List[Dict[str, Any]], parent=None, theme: dict = None):
        super().__init__(parent)
        self.apps_info = apps_info
        self.theme = theme or {}
        self.app_buttons = []
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("StartMenu")
        self.setFixedSize(540, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 16)
        main_layout.setSpacing(14)

        # ---------------- 1. Top Search Bar ----------------
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Type here to search apps, settings, and files...")
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.25);
                color: #1b1b1b;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 20px;
                padding: 0 16px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: #ffffff;
                border: 2px solid #0067c0;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_text)
        main_layout.addWidget(self.search_input)

        # ---------------- 2. Pinned Apps Header ----------------
        pinned_header = QHBoxLayout()
        pinned_title = QLabel("Pinned")
        pinned_title.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-weight: bold; font-size: 13px; color: #1b1b1b;")
        pinned_header.addWidget(pinned_title)
        pinned_header.addStretch()

        self.btn_all_apps = QPushButton("All apps >")
        self.btn_all_apps.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #0067c0;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(0, 103, 192, 0.3);
                border-radius: 4px;
                padding: 2px 8px;
            }
            QPushButton:hover { background: rgba(0, 103, 192, 0.1); }
        """)
        pinned_header.addWidget(self.btn_all_apps)
        main_layout.addLayout(pinned_header)

        # ---------------- 3. Pinned Apps Grid (Scrollable) ----------------
        self.grid_container = QWidget()
        self.apps_grid = QGridLayout(self.grid_container)
        self.apps_grid.setContentsMargins(4, 4, 4, 4)
        self.apps_grid.setHorizontalSpacing(12)
        self.apps_grid.setVerticalSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_container)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setFixedHeight(240)
        main_layout.addWidget(scroll)

        self._populate_grid(self.apps_info)

        # ---------------- 4. Recommended Section ----------------
        rec_title = QLabel("Recommended")
        rec_title.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-weight: bold; font-size: 13px; color: #1b1b1b;")
        main_layout.addWidget(rec_title)

        rec_layout = QHBoxLayout()
        rec_layout.setSpacing(10)

        quick_actions = [
            ("notes", "📝 New Note", "Write in SQLite Notes"),
            ("calc", "🧮 Calculator", "Accessible Math"),
            ("files", "📁 Explorer", "Browse Local Drives"),
            ("settings", "⚙️ Control", "Windows Bridge & Themes")
        ]
        for aid, title, sub in quick_actions:
            btn_rec = QPushButton(f"<b>{title}</b><br><span style='font-size:10px; color:#666;'>{sub}</span>")
            btn_rec.setFixedHeight(46)
            btn_rec.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.4);
                    color: #1b1b1b;
                    border: 1px solid rgba(0, 0, 0, 0.08);
                    border-radius: 8px;
                    padding: 4px 8px;
                    text-align: left;
                    font-family: 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.7);
                    border-color: #0067c0;
                }
            """)
            btn_rec.clicked.connect(lambda checked, app_id=aid: self._launch_and_hide(app_id))
            rec_layout.addWidget(btn_rec)

        main_layout.addLayout(rec_layout)

        main_layout.addStretch()

        # ---------------- 5. Bottom User & Power Footer ----------------
        footer = QFrame()
        footer.setFixedHeight(48)
        footer.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.03);
                border-top: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 8px;
            }
        """)
        f_layout = QHBoxLayout(footer)
        self.user_badge = QLabel("💠  <b>Admin User</b>")
        self.user_badge.setStyleSheet("color: #1b1b1b; font-family: 'Segoe UI', sans-serif; font-size: 12px;")
        f_layout.addWidget(self.user_badge)

        f_layout.addStretch()

        self.btn_lock = QPushButton("🔒  Lock")
        self.btn_lock.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #0284c7;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(2, 132, 199, 0.25);
                border-radius: 6px;
                padding: 4px 10px;
                margin-right: 6px;
            }
            QPushButton:hover {
                background: rgba(2, 132, 199, 0.1);
            }
        """)
        self.btn_lock.clicked.connect(self._on_lock_clicked)
        f_layout.addWidget(self.btn_lock)

        btn_power = QPushButton("⏻  Power")
        btn_power.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #c42b1c;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(196, 43, 28, 0.25);
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: rgba(196, 43, 28, 0.1);
            }
        """)
        btn_power.clicked.connect(self.shutdown_requested.emit)
        f_layout.addWidget(btn_power)

        main_layout.addWidget(footer)

        self._apply_theme_style()

    def _apply_theme_style(self):
        bg = self.theme.get("card_bg", "rgba(243, 246, 251, 0.94)")
        border = self.theme.get("card_border", "rgba(0, 0, 0, 0.10)")

        self.setStyleSheet(f"""
            QFrame#StartMenu {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
        """)

    def update_theme(self, theme: dict):
        self.theme = theme
        self._apply_theme_style()

    def update_user(self, user_name: str):
        """Updates the display name on the start menu footer."""
        if hasattr(self, "user_badge"):
            self.user_badge.setText(f"💠  <b>{user_name}</b>")

    def _populate_grid(self, apps: List[Dict[str, Any]]):
        # Clear existing
        for i in reversed(range(self.apps_grid.count())):
            item = self.apps_grid.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        for idx, app in enumerate(apps):
            app_id = app["id"]
            card = QFrame()
            card.setFixedSize(110, 68)
            card.setStyleSheet("""
                QFrame {
                    background: rgba(255, 255, 255, 0.4);
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    border-radius: 8px;
                }
                QFrame:hover {
                    background: rgba(255, 255, 255, 0.85);
                    border: 1px solid #0067c0;
                }
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(4, 6, 4, 6)
            c_layout.setSpacing(2)
            c_layout.setAlignment(Qt.AlignCenter)

            icon_lbl = QLabel(app.get("icon", "📦"))
            icon_lbl.setStyleSheet("font-size: 22px;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(icon_lbl)

            name_lbl = QLabel(app["name"])
            name_lbl.setStyleSheet("color: #1b1b1b; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 500;")
            name_lbl.setAlignment(Qt.AlignCenter)
            c_layout.addWidget(name_lbl)

            # Make the whole card clickable
            btn_overlay = QPushButton(card)
            btn_overlay.setGeometry(0, 0, 110, 68)
            btn_overlay.setStyleSheet("background: transparent; border: none;")
            btn_overlay.setCursor(Qt.PointingHandCursor)
            btn_overlay.clicked.connect(lambda checked, aid=app_id: self._launch_and_hide(aid))

            r = idx // 4
            c = idx % 4
            self.apps_grid.addWidget(card, r, c)

    def _on_search_text(self, text: str):
        query = text.strip().lower()
        if not query:
            self._populate_grid(self.apps_info)
            return
        filtered = [a for a in self.apps_info if query in a['name'].lower() or query in a['id'].lower()]
        self._populate_grid(filtered)

    def _launch_and_hide(self, app_id: str):
        self.app_launched.emit(app_id)
        self.hide()

    def _on_lock_clicked(self):
        self.hide()
        self.lock_requested.emit()
