"""
AirOS Start Menu & Application Launcher.
Provides search bar, pinned applications, recent items, system shortcuts, and external app launch.
"""

from typing import List, Dict, Any, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QColor

class StartMenu(QFrame):
    """Modern slide-up Start Menu and Application Launcher."""

    app_launched = Signal(str) # app_id
    shutdown_requested = Signal()

    def __init__(self, apps_info: List[Dict[str, Any]], parent=None, theme: dict = None):
        super().__init__(parent)
        self.apps_info = apps_info
        self.theme = theme or {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("StartMenu")
        self.setFixedSize(380, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        # Header Profile & Search
        header = QHBoxLayout()
        avatar = QLabel("💠")
        avatar.setStyleSheet("font-size: 22px;")
        header.addWidget(avatar)

        user_label = QLabel("AirOS User")
        user_label.setStyleSheet("color: #f0f6fc; font-weight: bold; font-size: 14px;")
        header.addWidget(user_label)
        header.addStretch()

        self.btn_power = QPushButton("⏻")
        self.btn_power.setToolTip("Shutdown AirOS")
        self.btn_power.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #f85149;
                font-size: 16px;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_power.clicked.connect(self.shutdown_requested.emit)
        header.addWidget(self.btn_power)
        layout.addLayout(header)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Type or gesture to search apps...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        self.search_input.textChanged.connect(self._filter_apps)
        layout.addWidget(self.search_input)

        # Pinned Apps Label
        section_lbl = QLabel("Pinned & Built-in Applications")
        section_lbl.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        layout.addWidget(section_lbl)

        # App List
        self.app_list = QListWidget()
        self.app_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                background-color: #21262d;
                color: #f0f6fc;
                border-radius: 6px;
                margin-bottom: 6px;
                padding: 10px;
                font-size: 13px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #30363d;
                color: #58a6ff;
            }
        """)
        self.app_list.itemClicked.connect(self._on_item_click)
        layout.addWidget(self.app_list)

        self._populate_list(self.apps_info)

        self.setStyleSheet("""
            QFrame#StartMenu {
                background-color: rgba(22, 27, 34, 0.96);
                border: 1px solid #30363d;
                border-radius: 12px;
            }
        """)

    def _populate_list(self, apps: List[Dict[str, Any]]):
        self.app_list.clear()
        for app in apps:
            item = QListWidgetItem(f"{app.get('icon', '📦')}  {app['name']}")
            item.setData(Qt.UserRole, app['id'])
            self.app_list.addItem(item)

    def _filter_apps(self, query: str):
        query = query.strip().lower()
        if not query:
            self._populate_list(self.apps_info)
            return

        filtered = [a for a in self.apps_info if query in a['name'].lower() or query in a['id'].lower()]
        self._populate_list(filtered)

    def _on_item_click(self, item: QListWidgetItem):
        app_id = item.data(Qt.UserRole)
        self.app_launched.emit(app_id)
        self.hide()
