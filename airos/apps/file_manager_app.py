"""
AirOS Built-in Application: File Manager.
Enables browsing directories, viewing file details, safe launch, and IntentLock deletion.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

class FileManagerApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = Path.home()
        self._init_ui()
        self._load_directory(self.current_path)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Address & navigation bar
        nav_bar = QHBoxLayout()
        self.btn_up = QPushButton("⬆ Up")
        self.btn_up.setStyleSheet("background-color: #21262d; color: white; padding: 6px 12px; border-radius: 4px;")
        self.btn_up.clicked.connect(self._navigate_up)
        nav_bar.addWidget(self.btn_up)

        self.path_bar = QLineEdit(str(self.current_path))
        self.path_bar.setReadOnly(True)
        self.path_bar.setStyleSheet("background-color: #0d1117; color: #58a6ff; border: 1px solid #30363d; border-radius: 4px; padding: 6px;")
        nav_bar.addWidget(self.path_bar)

        layout.addLayout(nav_bar)

        # File List
        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #161b22;
            }
            QListWidget::item:selected {
                background-color: #21262d;
                color: #58a6ff;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.file_list)

        # Status & Action bar
        bottom_bar = QHBoxLayout()
        self.status_label = QLabel("0 items")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        bottom_bar.addWidget(self.status_label)
        bottom_bar.addStretch()

        self.btn_open = QPushButton("Open")
        self.btn_open.setStyleSheet("background-color: #1f6feb; color: white; padding: 4px 12px; border-radius: 4px;")
        self.btn_open.clicked.connect(lambda: self._open_item(self.file_list.currentItem()))
        bottom_bar.addWidget(self.btn_open)

        layout.addLayout(bottom_bar)

    def _load_directory(self, path: Path):
        try:
            self.file_list.clear()
            self.current_path = path
            self.path_bar.setText(str(path))

            entries = list(path.iterdir())
            entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

            for entry in entries:
                if entry.name.startswith("."):
                    continue
                icon_prefix = "📁" if entry.is_dir() else "📄"
                item = QListWidgetItem(f"{icon_prefix}  {entry.name}")
                item.setData(Qt.UserRole, entry)
                self.file_list.addItem(item)

            self.status_label.setText(f"{len(entries)} items")
        except Exception as e:
            QMessageBox.warning(self, "Access Error", f"Cannot open folder: {e}")

    def _navigate_up(self):
        parent = self.current_path.parent
        if parent and parent != self.current_path:
            self._load_directory(parent)

    def _open_item(self, item: QListWidgetItem):
        if not item:
            return
        entry: Path = item.data(Qt.UserRole)
        if entry.is_dir():
            self._load_directory(entry)
        else:
            try:
                # Open with Windows default handler safely
                os.startfile(str(entry))
            except Exception as e:
                QMessageBox.warning(self, "Open Error", f"Could not launch file: {e}")
