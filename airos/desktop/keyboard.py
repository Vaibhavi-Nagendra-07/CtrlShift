"""
AirOS Floating Virtual Touchless Keyboard.
Provides touchless/click-activated QWERTY layout with Shift, Backspace, Enter, Space.
Features VisionOS translucent glass aesthetic with rounded pill keys.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout, QLabel
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QColor

KEYBOARD_ROWS = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Bksp"],
    ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]"],
    ["Shift", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", "Enter"],
    ["Space", "Clear", "Close"]
]

KEYBOARD_ROWS_SHIFT = [
    ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "Bksp"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}"],
    ["Shift", "A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\"", "Enter"],
    ["Space", "Clear", "Close"]
]

class VirtualKeyboard(QWidget):
    """Virtual On-Screen Keyboard tailored for AirOS gestures with VisionOS Glass Styling."""
    
    key_pressed = Signal(str) # Key character or command
    visibility_toggled = Signal(bool)

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.shift_active = False
        self.target_widget = None
        self.key_buttons = {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("VirtualKeyboard")
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 14)
        main_layout.setSpacing(8)

        # Header with drag bar / title
        header = QHBoxLayout()
        title = QLabel("⌨ AirType Spatial Keyboard")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()

        self.shift_indicator = QLabel("Shift: OFF")
        self.shift_indicator.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        header.addWidget(self.shift_indicator)

        main_layout.addLayout(header)

        # Build rows
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        main_layout.addLayout(self.rows_layout)

        self._render_keys()

        self.setStyleSheet("""
            QWidget#VirtualKeyboard {
                background-color: rgba(30, 26, 24, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 20px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                font-weight: 500;
                min-height: 42px;
                min-width: 38px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.28);
                border-color: #f59e0b;
                color: white;
            }
            QPushButton:pressed {
                background-color: #f59e0b;
                color: black;
            }
            QPushButton#ActionKey {
                background-color: rgba(255, 255, 255, 0.18);
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.setFixedSize(760, 275)

    def _render_keys(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()

        rows = KEYBOARD_ROWS_SHIFT if self.shift_active else KEYBOARD_ROWS
        self.key_buttons.clear()

        for row in rows:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(6)
            for key in row:
                btn = QPushButton(key)
                if key in ["Shift", "Bksp", "Enter", "Space", "Clear", "Close"]:
                    btn.setObjectName("ActionKey")
                    if key == "Space":
                        btn.setFixedWidth(240)
                    elif key in ["Shift", "Bksp", "Enter"]:
                        btn.setFixedWidth(80)
                    elif key == "Close":
                        btn.setStyleSheet("background-color: rgba(239, 68, 68, 0.8); color: white; border-radius: 12px;")

                btn.clicked.connect(lambda checked, k=key: self._handle_key(k))
                row_layout.addWidget(btn)
                self.key_buttons[key] = btn
            self.rows_layout.addLayout(row_layout)

    def _handle_key(self, key: str):
        if key == "Shift":
            self.shift_active = not self.shift_active
            self.shift_indicator.setText(f"Shift: {'ON' if self.shift_active else 'OFF'}")
            self.shift_indicator.setStyleSheet(f"color: {'#10b981' if self.shift_active else 'rgba(255, 255, 255, 0.6)'}; font-weight: bold;")
            self._render_keys()
            return

        if key == "Close":
            self.hide()
            self.visibility_toggled.emit(False)
            return

        if key == "Bksp":
            char = "\b"
            send_val = "Backspace"
        elif key == "Enter":
            char = "\n"
            send_val = "Enter"
        elif key == "Space":
            char = " "
            send_val = "Space"
        elif key == "Clear":
            char = ""
            send_val = "Clear"
        else:
            char = key
            send_val = key

        if self.target_widget:
            try:
                if send_val == "Backspace":
                    text = self.target_widget.text() if hasattr(self.target_widget, "text") else self.target_widget.toPlainText()
                    if hasattr(self.target_widget, "setText"):
                        self.target_widget.setText(text[:-1])
                    elif hasattr(self.target_widget, "setPlainText"):
                        self.target_widget.setPlainText(text[:-1])
                elif send_val == "Clear":
                    if hasattr(self.target_widget, "clear"):
                        self.target_widget.clear()
                else:
                    if hasattr(self.target_widget, "insert"):
                        self.target_widget.insert(char)
                    elif hasattr(self.target_widget, "insertPlainText"):
                        self.target_widget.insertPlainText(char)
            except Exception:
                pass

        self.key_pressed.emit(send_val)

        if self.shift_active and len(key) == 1:
            self.shift_active = False
            self.shift_indicator.setText("Shift: OFF")
            self.shift_indicator.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
            self._render_keys()

    def set_target_widget(self, widget):
        self.target_widget = widget
