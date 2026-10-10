"""
AirOS Built-in Application: AirBrowse.
Full Chromium-based touchless web browser powered by PySide6 QtWebEngineWidgets.
Features:
- Web navigation (Back, Forward, Refresh, Home)
- URL address bar and Google search integration
- Bookmark bar (Google, Microsoft 365, YouTube, Wikipedia, GitHub)
- Two-finger gesture scrolling & click link navigation
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QToolBar
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView

class BrowserApp(QWidget):
    """Touchless Spatial Chromium Web Browser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_home = "https://www.google.com"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Navigation Header Bar
        nav_bar = QWidget()
        nav_bar.setFixedHeight(46)
        nav_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 36, 0.95);
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #f0f6fc;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                min-width: 32px;
                height: 28px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(88, 166, 255, 0.3);
                border-color: #58a6ff;
            }
            QLineEdit {
                background-color: rgba(18, 18, 22, 0.85);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 14px;
                padding: 4px 14px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #58a6ff;
            }
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(10, 4, 10, 4)
        nav_layout.setSpacing(8)

        # Nav buttons
        self.btn_back = QPushButton("◀")
        self.btn_back.clicked.connect(self._go_back)
        nav_layout.addWidget(self.btn_back)

        self.btn_fwd = QPushButton("▶")
        self.btn_fwd.clicked.connect(self._go_forward)
        nav_layout.addWidget(self.btn_fwd)

        self.btn_reload = QPushButton("⟳")
        self.btn_reload.clicked.connect(self._reload_page)
        nav_layout.addWidget(self.btn_reload)

        self.btn_home = QPushButton("🏠")
        self.btn_home.clicked.connect(self._go_home)
        nav_layout.addWidget(self.btn_home)

        # URL Input
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search with Google or enter web URL...")
        self.url_bar.returnPressed.connect(self._navigate_to_url)
        nav_layout.addWidget(self.url_bar)

        self.btn_go = QPushButton("Go")
        self.btn_go.clicked.connect(self._navigate_to_url)
        nav_layout.addWidget(self.btn_go)

        layout.addWidget(nav_bar)

        # Bookmarks Bar
        bmarks_bar = QWidget()
        bmarks_bar.setFixedHeight(32)
        bmarks_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(22, 22, 28, 0.95);
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
            QPushButton {
                background: transparent;
                color: #b0b8c4;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #58a6ff;
            }
        """)
        bm_layout = QHBoxLayout(bmarks_bar)
        bm_layout.setContentsMargins(12, 2, 12, 2)
        bm_layout.setSpacing(6)

        bookmarks = [
            ("🔍 Google", "https://www.google.com"),
            ("🏢 Microsoft 365", "https://www.microsoft365.com"),
            ("▶ YouTube", "https://www.youtube.com"),
            ("📖 Wikipedia", "https://www.wikipedia.org"),
            ("💻 GitHub", "https://www.github.com")
        ]
        for name, url in bookmarks:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, u=url: self._load_url(u))
            bm_layout.addWidget(btn)
        bm_layout.addStretch()

        layout.addWidget(bmarks_bar)

        # WebEngine View
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl(self.default_home))
        self.webview.urlChanged.connect(self._on_url_changed)
        self.webview.titleChanged.connect(self._on_title_changed)
        layout.addWidget(self.webview)

    def _load_url(self, url_str: str):
        if not url_str.startswith("http://") and not url_str.startswith("https://"):
            url_str = "https://" + url_str
        self.webview.setUrl(QUrl(url_str))

    def _navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if "." in text and " " not in text:
            self._load_url(text)
        else:
            search_url = f"https://www.google.com/search?q={text.replace(' ', '+')}"
            self.webview.setUrl(QUrl(search_url))

    def _go_back(self):
        self.webview.back()

    def _go_forward(self):
        self.webview.forward()

    def _reload_page(self):
        self.webview.reload()

    def _go_home(self):
        self.webview.setUrl(QUrl(self.default_home))

    def _on_url_changed(self, qurl: QUrl):
        self.url_bar.setText(qurl.toString())

    def _on_title_changed(self, title: str):
        # Update window title if container is AirWindow
        parent_win = self.parent()
        while parent_win:
            if hasattr(parent_win, "title_label"):
                parent_win.title_label.setText(f"AirBrowse — {title[:36]}")
                break
            parent_win = parent_win.parent()
