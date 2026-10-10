"""
AirOS Built-in Application: Calculator.
High-readability calculator with large touchless/click targets.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class CalculatorApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expression = ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.display.setFixedHeight(56)
        self.display.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #58a6ff;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        layout.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(6)

        buttons = [
            ("C", 0, 0), ("(", 0, 1), (")", 0, 2), ("/", 0, 3),
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("*", 1, 3),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("-", 2, 3),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("+", 3, 3),
            ("0", 4, 0), (".", 4, 1), ("DEL", 4, 2), ("=", 4, 3)
        ]

        for text, r, c in buttons:
            btn = QPushButton(text)
            btn.setFixedHeight(48)
            btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
            if text in ["=", "+", "-", "*", "/"]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1f6feb;
                        color: white;
                        border: none;
                        border-radius: 6px;
                    }
                    QPushButton:hover { background-color: #388bfd; }
                """)
            elif text in ["C", "DEL"]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #30363d;
                        color: #f85149;
                        border: none;
                        border-radius: 6px;
                    }
                    QPushButton:hover { background-color: #3e444d; }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #21262d;
                        color: #f0f6fc;
                        border: 1px solid #30363d;
                        border-radius: 6px;
                    }
                    QPushButton:hover { background-color: #30363d; }
                """)

            btn.clicked.connect(lambda checked, val=text: self._on_button_click(val))
            grid.addWidget(btn, r, c)

        layout.addLayout(grid)

    def _on_button_click(self, val: str):
        if val == "C":
            self.expression = ""
            self.display.setText("0")
        elif val == "DEL":
            self.expression = self.expression[:-1]
            self.display.setText(self.expression if self.expression else "0")
        elif val == "=":
            try:
                # Safe eval arithmetic
                allowed = set("0123456789+-*/.() ")
                if all(c in allowed for c in self.expression):
                    result = eval(self.expression)
                    self.display.setText(str(round(result, 6)))
                    self.expression = str(result)
                else:
                    self.display.setText("Error")
            except Exception:
                self.display.setText("Error")
        else:
            self.expression += val
            self.display.setText(self.expression)
