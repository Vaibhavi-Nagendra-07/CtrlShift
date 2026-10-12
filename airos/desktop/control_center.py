"""
AirOS Spatial Control Center Widget.
Inspired by Apple VisionOS / macOS Control Center with translucent glass aesthetic.
Provides touchless interactive controls for:
- Spatial Audio Volume slider & mute
- Display Brightness slider
- Environment Immersion Depth dial
- Quick Toggles: Wi-Fi, Bluetooth, AirDrop, Focus Mode, Privacy Shield, Native Input
- Gesture Tracking Sensitivity Quick Switch
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class ControlCenterWidget(QFrame):
    """Floating Glass Spatial Control Center."""

    volume_changed = Signal(int)
    brightness_changed = Signal(int)
    immersion_changed = Signal(int)
    toggle_clicked = Signal(str, bool)

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.toggles_state = {
            "wifi": True,
            "bluetooth": True,
            "airdrop": True,
            "focus": False,
            "privacy": False,
            "native_input": False
        }
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("ControlCenter")
        self.setFixedSize(360, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Control Center")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()

        badge = QLabel("Spatial OS")
        badge.setStyleSheet("color: #f59e0b; background: rgba(245, 158, 11, 0.15); border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
        header.addWidget(badge)
        layout.addLayout(header)

        # 2x3 Grid of Glass Toggle Pills
        grid = QGridLayout()
        grid.setSpacing(10)

        toggles_info = [
            ("wifi", "Wi-Fi", "📶", "Connected"),
            ("bluetooth", "Bluetooth", "🦷", "On"),
            ("airdrop", "AirDrop", "📡", "Contacts"),
            ("focus", "Focus Mode", "🌙", "Off"),
            ("privacy", "Face Shield", "🛡️", "Active"),
            ("native_input", "Windows Bridge", "🪟", "Opt-in")
        ]

        self.toggle_buttons = {}
        for i, (key, label, icon, sub) in enumerate(toggles_info):
            btn = QPushButton(f"{icon}  <b>{label}</b><br><span style='font-size: 10px; opacity: 0.7;'>{sub}</span>")
            btn.setFixedHeight(54)
            btn.setCheckable(True)
            btn.setChecked(self.toggles_state[key])
            self._apply_toggle_style(btn, self.toggles_state[key])
            btn.clicked.connect(lambda checked, k=key, b=btn: self._on_toggle(k, b))
            r = i // 2
            c = i % 2
            grid.addWidget(btn, r, c)
            self.toggle_buttons[key] = btn

        layout.addLayout(grid)

        # Sliders Section
        # 1. Volume
        vol_box = QVBoxLayout()
        vol_header = QHBoxLayout()
        vol_lbl = QLabel("🔊 Spatial Audio Volume")
        vol_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 600;")
        self.vol_val = QLabel("75%")
        self.vol_val.setStyleSheet("color: #94a3b8; font-size: 11px;")
        vol_header.addWidget(vol_lbl)
        vol_header.addStretch()
        vol_header.addWidget(self.vol_val)
        vol_box.addLayout(vol_header)

        self.slider_vol = QSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(75)
        self.slider_vol.valueChanged.connect(self._on_vol_change)
        self._style_slider(self.slider_vol, "#007aff")
        vol_box.addWidget(self.slider_vol)
        layout.addLayout(vol_box)

        # 2. Display Brightness
        bright_box = QVBoxLayout()
        bright_header = QHBoxLayout()
        bright_lbl = QLabel("☀️ Display Luminance")
        bright_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 600;")
        self.bright_val = QLabel("85%")
        self.bright_val.setStyleSheet("color: #94a3b8; font-size: 11px;")
        bright_header.addWidget(bright_lbl)
        bright_header.addStretch()
        bright_header.addWidget(self.bright_val)
        bright_box.addLayout(bright_header)

        self.slider_bright = QSlider(Qt.Horizontal)
        self.slider_bright.setRange(10, 100)
        self.slider_bright.setValue(85)
        self.slider_bright.valueChanged.connect(self._on_bright_change)
        self._style_slider(self.slider_bright, "#f59e0b")
        bright_box.addWidget(self.slider_bright)
        layout.addLayout(bright_box)

        # 3. Environment Immersion Depth Dial
        imm_box = QVBoxLayout()
        imm_header = QHBoxLayout()
        imm_lbl = QLabel("🪐 Spatial Immersion Depth")
        imm_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 600;")
        self.imm_val = QLabel("50%")
        self.imm_val.setStyleSheet("color: #94a3b8; font-size: 11px;")
        imm_header.addWidget(imm_lbl)
        imm_header.addStretch()
        imm_header.addWidget(self.imm_val)
        imm_box.addLayout(imm_header)

        self.slider_imm = QSlider(Qt.Horizontal)
        self.slider_imm.setRange(0, 100)
        self.slider_imm.setValue(50)
        self.slider_imm.valueChanged.connect(self._on_imm_change)
        self._style_slider(self.slider_imm, "#a855f7")
        imm_box.addWidget(self.slider_imm)
        layout.addLayout(imm_box)

        self.setStyleSheet("""
            QFrame#ControlCenter {
                background-color: rgba(25, 23, 21, 0.94);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 20px;
            }
        """)

    def _style_slider(self, slider: QSlider, active_color: str):
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 4px;
            }}
            QSlider::sub-page:horizontal {{
                background: {active_color};
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: white;
                width: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }}
        """)

    def _apply_toggle_style(self, btn: QPushButton, is_active: bool):
        if is_active:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.24);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.35);
                    border-radius: 14px;
                    padding: 6px;
                    text-align: left;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.06);
                    color: rgba(255, 255, 255, 0.6);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 14px;
                    padding: 6px;
                    text-align: left;
                }
            """)

    def set_toggle_state(self, key: str, state: bool):
        self.toggles_state[key] = state
        if hasattr(self, "toggle_buttons") and key in self.toggle_buttons:
            btn = self.toggle_buttons[key]
            btn.setChecked(state)
            self._apply_toggle_style(btn, state)

    def _on_toggle(self, key: str, btn: QPushButton):
        self.toggles_state[key] = not self.toggles_state[key]
        self._apply_toggle_style(btn, self.toggles_state[key])
        self.toggle_clicked.emit(key, self.toggles_state[key])

    def _on_vol_change(self, val: int):
        self.vol_val.setText(f"{val}%")
        self.volume_changed.emit(val)

    def _on_bright_change(self, val: int):
        self.bright_val.setText(f"{val}%")
        self.brightness_changed.emit(val)

    def _on_imm_change(self, val: int):
        self.imm_val.setText(f"{val}%")
        self.immersion_changed.emit(val)
