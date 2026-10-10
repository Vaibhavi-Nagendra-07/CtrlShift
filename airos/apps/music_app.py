"""
AirOS Built-in Application: Apple Music / Spotify Spatial Player.
Interactive media player with playback controls, spatial sound equalizer, and playlist viewer.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush

TRACKS = [
    ("Midnight City", "M83", "04:03", "🌌"),
    ("Starboy", "The Weeknd, Daft Punk", "03:50", "⚡"),
    ("Spatial Dreams (VisionOS Mix)", "AirOS Ambient", "05:12", "🪐"),
    ("Get Lucky", "Daft Punk, Pharrell Williams", "04:08", "🪩"),
    ("Cornfield Chase", "Hans Zimmer (Interstellar)", "02:06", "🚀")
]

class MusicPlayerApp(QWidget):
    """Spatial Apple Music / Audio Player."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_idx = 0
        self.is_playing = False
        self.playback_progress = 30
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Album Art & Luminous Visualizer Card
        card = QFrame()
        card.setFixedHeight(180)
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fa2d48, stop:1 #a200ff);
                border-radius: 16px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignCenter)

        self.album_icon = QLabel("🎵")
        self.album_icon.setFont(QFont("Segoe UI Emoji", 48))
        self.album_icon.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.album_icon)

        self.track_title = QLabel(TRACKS[0][0])
        self.track_title.setAlignment(Qt.AlignCenter)
        self.track_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        card_layout.addWidget(self.track_title)

        self.artist_label = QLabel(TRACKS[0][1])
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 12px;")
        card_layout.addWidget(self.artist_label)

        layout.addWidget(card)

        # Progress bar
        self.slider_prog = QSlider(Qt.Horizontal)
        self.slider_prog.setRange(0, 100)
        self.slider_prog.setValue(self.playback_progress)
        self.slider_prog.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #fa2d48; border-radius: 2px; }
            QSlider::handle:horizontal { background: white; width: 12px; margin-top: -4px; margin-bottom: -4px; border-radius: 6px; }
        """)
        layout.addWidget(self.slider_prog)

        # Player Controls
        ctrls = QHBoxLayout()
        ctrls.setAlignment(Qt.AlignCenter)
        ctrls.setSpacing(20)

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.clicked.connect(self._prev_track)
        ctrls.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(56, 56)
        self.btn_play.clicked.connect(self._toggle_play)
        ctrls.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.clicked.connect(self._next_track)
        ctrls.addWidget(self.btn_next)

        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.15);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 22px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background: #fa2d48;
                    border-color: white;
                }
            """)
        self.btn_play.setStyleSheet(self.btn_play.styleSheet().replace("border-radius: 22px;", "border-radius: 28px;"))

        layout.addLayout(ctrls)

        # Playlist List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: rgba(20, 20, 26, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: white;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
            QListWidget::item:selected { background: rgba(250, 45, 72, 0.3); color: #fa2d48; }
        """)
        for title, artist, dur, icon in TRACKS:
            self.list_widget.addItem(f"{icon}  {title} — {artist} ({dur})")
        self.list_widget.itemClicked.connect(self._select_track)
        layout.addWidget(self.list_widget)

    def _toggle_play(self):
        self.is_playing = not self.is_playing
        self.btn_play.setText("⏸" if self.is_playing else "▶")

    def _next_track(self):
        self.current_idx = (self.current_idx + 1) % len(TRACKS)
        self._update_track()

    def _prev_track(self):
        self.current_idx = (self.current_idx - 1 + len(TRACKS)) % len(TRACKS)
        self._update_track()

    def _select_track(self, item):
        row = self.list_widget.row(item)
        self.current_idx = row
        self._update_track()

    def _update_track(self):
        title, artist, dur, icon = TRACKS[self.current_idx]
        self.track_title.setText(title)
        self.artist_label.setText(artist)
        self.album_icon.setText(icon)
        self.is_playing = True
        self.btn_play.setText("⏸")
