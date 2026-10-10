"""
AirOS Vision Playground / AI Avatar Studio.
Inspired by Apple VisionOS spatial avatars and persona creation.
Allows selecting 3D avatar personas, themes (Sci-fi, Disco, Sunset, Starry Night),
and interacting with spatial AI prompts.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QLineEdit, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPen

THEMES_LIST = [
    ("🎉 Birthday", "#f72585", "#7209b7"),
    ("🪩 Disco", "#4361ee", "#4cc9f0"),
    ("🏰 Fantasy", "#4895ef", "#560bad"),
    ("🎆 Fireworks", "#f72585", "#b5179e"),
    ("💖 Love", "#e63946", "#ffb703"),
    ("🌌 Starry Night", "#14213d", "#fca311"),
    ("🏖️ Summer", "#06d6a0", "#118ab2"),
    ("🍸 Party", "#9d4edd", "#ff758f"),
    ("🌸 Spring", "#ff99c8", "#fcf6bd"),
    ("🚀 Sci-Fi", "#00f0ff", "#7000ff"),
    ("🌅 Sunset", "#ff7b00", "#ff006e")
]

class AvatarCanvas(QWidget):
    """Draws a spatial luminous avatar persona with particle glow."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.glow_color1 = QColor("#00f0ff")
        self.glow_color2 = QColor("#ff007f")
        self.persona_name = "Spatial AI Persona"

    def set_theme_colors(self, c1_hex, c2_hex, name):
        self.glow_color1 = QColor(c1_hex)
        self.glow_color2 = QColor(c2_hex)
        self.persona_name = name
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Outer luminous halo
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, self.glow_color1)
        grad.setColorAt(1.0, self.glow_color2)
        
        painter.setPen(Qt.NoPen)
        halo_color = QColor(self.glow_color1.red(), self.glow_color1.green(), self.glow_color1.blue(), 50)
        painter.setBrush(QBrush(halo_color))
        painter.drawEllipse(10, 10, 160, 160)

        # Luminous Ring
        painter.setPen(QPen(grad, 5))
        painter.setBrush(QBrush(QColor(20, 24, 32)))
        painter.drawEllipse(25, 25, 130, 130)

        # Persona face avatar
        painter.setFont(QFont("Segoe UI Emoji", 52))
        painter.setPen(Qt.white)
        painter.drawText(self.rect(), Qt.AlignCenter, "👩‍🚀")
        painter.end()

class PersonaPlaygroundApp(QWidget):
    """VisionOS-style Persona & AI Studio App."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Avatar representation
        avatar_box = QHBoxLayout()
        avatar_box.addStretch()
        self.avatar_canvas = AvatarCanvas()
        avatar_box.addWidget(self.avatar_canvas)
        avatar_box.addStretch()
        layout.addLayout(avatar_box)

        # Title
        title_lbl = QLabel("AirOS Spatial Persona Themes")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("color: #f0f6fc; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_lbl)

        # Grid of Themes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)

        for i, (name, c1, c2) in enumerate(THEMES_LIST):
            btn = QPushButton(name)
            btn.setFixedHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.08);
                    color: #f0f6fc;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 22px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {c1};
                    color: white;
                    border-color: {c2};
                }}
            """)
            btn.clicked.connect(lambda checked, col1=c1, col2=c2, n=name: self.avatar_canvas.set_theme_colors(col1, col2, n))
            r = i // 4
            c = i % 4
            grid.addWidget(btn, r, c)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)

        # AI prompt describe input
        input_box = QHBoxLayout()
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("✨ Describe persona aura or background effect...")
        self.prompt_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QLineEdit:focus { border-color: #00f0ff; }
        """)
        input_box.addWidget(self.prompt_input)

        btn_gen = QPushButton("Generate")
        btn_gen.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff007f, stop:1 #7928ca);
                color: white;
                border-radius: 20px;
                padding: 8px 18px;
                font-weight: bold;
            }
        """)
        btn_gen.clicked.connect(self._on_generate)
        input_box.addWidget(btn_gen)

        layout.addLayout(input_box)

    def _on_generate(self):
        txt = self.prompt_input.text().strip()
        if txt:
            # Change aura to magical gradient
            self.avatar_canvas.set_theme_colors("#ff007f", "#00f0ff", txt)
            self.prompt_input.clear()
