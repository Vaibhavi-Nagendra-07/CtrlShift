"""
AirOS Built-in Application: Microsoft 365 Spatial Suite Hub.
Direct touchless access to Microsoft Word, Excel, PowerPoint, Outlook, OneNote, and OneDrive.
Features web embedded mode with automatic tab switching and quick document templates.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

MICROSOFT_SERVICES = [
    {"id": "portal", "name": "M365 Home", "icon": "🏢", "url": "https://www.microsoft365.com"},
    {"id": "word", "name": "Word", "icon": "📄", "url": "https://www.office.com/launch/word"},
    {"id": "excel", "name": "Excel", "icon": "📊", "url": "https://www.office.com/launch/excel"},
    {"id": "powerpoint", "name": "PowerPoint", "icon": "📽️", "url": "https://www.office.com/launch/powerpoint"},
    {"id": "outlook", "name": "Outlook", "icon": "✉️", "url": "https://outlook.live.com"},
    {"id": "onedrive", "name": "OneDrive", "icon": "☁️", "url": "https://onedrive.live.com"}
]

class MicrosoftHubApp(QWidget):
    """Microsoft 365 Cloud Productivity Suite for AirOS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Service Selector Bar
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(24, 28, 36, 0.98);
                border-bottom: 2px solid #0078d4;
            }
            QPushButton {
                background: transparent;
                color: #d2d8e0;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: #58a6ff;
            }
            QPushButton:checked {
                background-color: #0078d4;
                color: white;
            }
        """)
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(12, 4, 12, 4)
        bar_layout.setSpacing(8)

        brand_lbl = QLabel("Microsoft 365")
        brand_lbl.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 13px;")
        bar_layout.addWidget(brand_lbl)

        self.service_btns = []
        for i, s in enumerate(MICROSOFT_SERVICES):
            btn = QPushButton(f"{s['icon']} {s['name']}")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, url=s["url"], b=btn: self._switch_service(url, b))
            bar_layout.addWidget(btn)
            self.service_btns.append(btn)

        bar_layout.addStretch()
        layout.addWidget(top_bar)

        # WebEngine View
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(MICROSOFT_SERVICES[0]["url"]))
        layout.addWidget(self.webview)

    def _switch_service(self, url: str, active_btn: QPushButton):
        for btn in self.service_btns:
            btn.setChecked(btn == active_btn)
        self.webview.setUrl(QUrl(url))
