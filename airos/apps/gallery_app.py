"""
AirOS Built-in Application: Gallery.
Visual photo viewer and image viewer with touchless next/prev and zoom controls.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont

class GalleryApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_list = []
        self.current_index = 0
        self._init_ui()
        self._load_sample_images()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_load = QPushButton("📁 Load Images")
        self.btn_load.setStyleSheet("background-color: #21262d; color: white; padding: 6px 12px; border-radius: 4px;")
        self.btn_load.clicked.connect(self._select_folder)
        toolbar.addWidget(self.btn_load)

        self.btn_prev = QPushButton("◀ Previous")
        self.btn_prev.setStyleSheet("background-color: #1f6feb; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_prev.clicked.connect(self._prev_image)
        toolbar.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setStyleSheet("background-color: #1f6feb; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_next.clicked.connect(self._next_image)
        toolbar.addWidget(self.btn_next)

        toolbar.addStretch()
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setStyleSheet("color: #8b949e; font-weight: bold;")
        toolbar.addWidget(self.counter_label)

        layout.addLayout(toolbar)

        # Viewer Display
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("background-color: #0b0e14; border: 1px solid #30363d; border-radius: 6px;")
        
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #8b949e; font-size: 16px;")
        self.scroll.setWidget(self.image_label)
        self.scroll.setWidgetResizable(True)

        layout.addWidget(self.scroll)

    def _load_sample_images(self):
        # Generate colorful abstract sample images if user folder not selected
        sample_pixmaps = []
        colors = [
            (QColor(41, 128, 185), "Deep Ocean Nebula"),
            (QColor(142, 68, 173), "Cosmic Violet Horizon"),
            (QColor(39, 174, 96), "Emerald Forest"),
            (QColor(230, 126, 34), "Solar Flare")
        ]
        for color, title in colors:
            pix = QPixmap(640, 400)
            pix.fill(color)
            p = QPainter(pix)
            p.setPen(Qt.white)
            p.setFont(QFont("Segoe UI", 18, QFont.Bold))
            p.drawText(pix.rect(), Qt.AlignCenter, f"AirOS Wallpapers\n{title}")
            p.end()
            sample_pixmaps.append(pix)

        self.image_list = sample_pixmaps
        self._show_image()

    def _show_image(self):
        if not self.image_list:
            self.image_label.setText("No images available")
            self.counter_label.setText("0 / 0")
            return

        self.counter_label.setText(f"{self.current_index + 1} / {len(self.image_list)}")
        item = self.image_list[self.current_index]
        if isinstance(item, QPixmap):
            self.image_label.setPixmap(item)
        elif isinstance(item, Path):
            pix = QPixmap(str(item))
            self.image_label.setPixmap(pix.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _next_image(self):
        if self.image_list:
            self.current_index = (self.current_index + 1) % len(self.image_list)
            self._show_image()

    def _prev_image(self):
        if self.image_list:
            self.current_index = (self.current_index - 1 + len(self.image_list)) % len(self.image_list)
            self._show_image()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Directory", str(Path.home() / "Pictures"))
        if folder:
            path = Path(folder)
            files = [p for p in path.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]]
            if files:
                self.image_list = files
                self.current_index = 0
                self._show_image()
