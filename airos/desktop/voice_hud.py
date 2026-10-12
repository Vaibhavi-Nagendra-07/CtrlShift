"""
AirOS Voice Command Assistant HUD and Floating Status Pill.
Displays:
- Real-time listening indicator with pulsing audio animation
- Live speech transcription bubble
- Quick commands cheat sheet / modal
- Simulation input bar for testability
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont


class VoiceCommandsDialog(QDialog):
    """Interactive cheat sheet displaying all AirOS voice commands."""

    command_clicked = Signal(str)

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.setWindowTitle("AirOS Voice Commands Reference")
        self.setFixedSize(560, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("🎙️ AirVoice Touchless Command Reference")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)

        sub = QLabel("Speak naturally or click any phrase below to execute instantly:")
        sub.setStyleSheet("font-size: 11px; color: #64748b;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #cbd5e1; border-radius: 8px; background: white; }")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(12)

        categories = [
            ("✏️ Screen Annotation (AirDraw)", [
                ("Start Drawing", "Activates full-screen mid-air drawing overlay"),
                ("Stop Drawing", "Closes drawing overlay"),
                ("Color Blue", "Switches ink to vibrant blue"),
                ("Color Red", "Switches ink to crimson red"),
                ("Color Green", "Switches ink to emerald green"),
                ("Color Yellow", "Switches ink to cyber amber"),
                ("Eraser", "Activates stroke eraser"),
                ("Pen", "Returns to drawing pen"),
                ("Laser Pointer", "Activates glowing presentation laser trail"),
                ("Smart Shape", "Toggles geometric auto-shape snapping"),
                ("Clear Screen", "Clears all drawings immediately"),
                ("Save Drawing", "Takes a screenshot and saves snapshot")
            ]),
            ("🚀 App Launching", [
                ("Open Notes", "Launches AirNotes application"),
                ("Open Calculator", "Launches Arithmetic Calculator"),
                ("Open Browser", "Launches Edge Web Browser"),
                ("Open Files", "Launches File Explorer"),
                ("Open Photos", "Launches Photo Gallery"),
                ("Open Music", "Launches Music Player"),
                ("Open Settings", "Launches AirOS Settings")
            ]),
            ("🪟 Windows & Navigation", [
                ("Show Desktop", "Minimizes / toggles all windows"),
                ("Start Menu", "Toggles centered Start Menu"),
                ("Virtual Keyboard", "Toggles floating AirType keyboard"),
                ("Workspace One", "Switches to Space 1"),
                ("Workspace Two", "Switches to Space 2"),
                ("Pause Tracking", "Freezes touchless hand tracking"),
                ("Resume Tracking", "Resumes touchless hand tracking")
            ])
        ]

        for cat_title, cmds in categories:
            cat_lbl = QLabel(cat_title)
            cat_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 6px;")
            c_layout.addWidget(cat_lbl)

            grid = QGridLayout()
            grid.setSpacing(6)
            for row, (cmd_text, cmd_desc) in enumerate(cmds):
                btn = QPushButton(f"\"{cmd_text}\"")
                btn.setFixedHeight(26)
                btn.setStyleSheet("""
                    QPushButton {
                        background: #f1f5f9;
                        color: #0f172a;
                        border: 1px solid #e2e8f0;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 500;
                        text-align: left;
                        padding-left: 8px;
                    }
                    QPushButton:hover {
                        background: #e2e8f0;
                        border-color: #0078d4;
                    }
                """)
                btn.clicked.connect(lambda ch, t=cmd_text: self._on_cmd_click(t))
                grid.addWidget(btn, row, 0)

                desc_lbl = QLabel(cmd_desc)
                desc_lbl.setStyleSheet("font-size: 10px; color: #64748b;")
                grid.addWidget(desc_lbl, row, 1)

            c_layout.addLayout(grid)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Simulation Bar
        sim_box = QHBoxLayout()
        self.input_sim = QLineEdit()
        self.input_sim.setPlaceholderText("Type a voice command to test...")
        self.input_sim.returnPressed.connect(self._on_sim_submit)
        sim_box.addWidget(self.input_sim)

        btn_run = QPushButton("Run")
        btn_run.setStyleSheet("background: #0078d4; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold;")
        btn_run.clicked.connect(self._on_sim_submit)
        sim_box.addWidget(btn_run)
        layout.addLayout(sim_box)

    def _on_cmd_click(self, text: str):
        self.command_clicked.emit(text)
        self.accept()

    def _on_sim_submit(self):
        text = self.input_sim.text().strip()
        if text:
            self.command_clicked.emit(text)
            self.accept()


class VoiceHUDWidget(QFrame):
    """
    Taskbar/Desktop pill showing live voice recognition status,
    transcript feedback bubble, and commands button.
    """

    voice_command_requested = Signal(str)

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.is_listening = False
        self.pulse_phase = 0.0

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._on_pulse_tick)
        self.pulse_timer.start(50)

        self._init_ui()

    def _init_ui(self):
        self.setObjectName("VoiceHUD")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Microphone Icon / Button
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(28, 28)
        self.btn_mic.setToolTip("AirVoice Listening Indicator (Click for Voice Commands Guide)")
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background: rgba(0, 120, 212, 0.15);
                border: 1px solid rgba(0, 120, 212, 0.35);
                border-radius: 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(0, 120, 212, 0.3);
            }
        """)
        self.btn_mic.clicked.connect(self._show_commands_dialog)
        layout.addWidget(self.btn_mic)

        # Transcript text pill
        self.transcript_lbl = QLabel("AirVoice: Ready")
        self.transcript_lbl.setStyleSheet("color: #1e293b; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.transcript_lbl)

        # Commands help button
        self.btn_help = QPushButton("Commands")
        self.btn_help.setFixedHeight(22)
        self.btn_help.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #0078d4;
                border: 1px solid rgba(0, 120, 212, 0.25);
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 6px;
            }
            QPushButton:hover {
                background: rgba(0, 120, 212, 0.1);
            }
        """)
        self.btn_help.clicked.connect(self._show_commands_dialog)
        layout.addWidget(self.btn_help)

        self.setStyleSheet("""
            QFrame#VoiceHUD {
                background-color: rgba(255, 255, 255, 0.85);
                border: 1px solid rgba(0, 0, 0, 0.10);
                border-radius: 18px;
            }
        """)

    def _on_pulse_tick(self):
        if self.is_listening:
            self.pulse_phase = (self.pulse_phase + 0.15)
            # Subtle glow effect
            alpha = int(128 + 127 * (0.5 + 0.5 * (self.pulse_phase % 3.14)))
            self.btn_mic.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(16, 185, 129, 0.25);
                    border: 2px solid #10b981;
                    border-radius: 14px;
                    font-size: 14px;
                }}
            """)
        else:
            self.btn_mic.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 120, 212, 0.15);
                    border: 1px solid rgba(0, 120, 212, 0.35);
                    border-radius: 14px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(0, 120, 212, 0.3);
                }
            """)

    def set_listening_state(self, listening: bool):
        self.is_listening = listening
        if listening:
            self.transcript_lbl.setText("🎙️ Listening...")
            self.transcript_lbl.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
        else:
            self.transcript_lbl.setText("AirVoice: Ready")
            self.transcript_lbl.setStyleSheet("color: #1e293b; font-size: 11px; font-weight: 500;")

    def set_heard_transcript(self, text: str):
        self.transcript_lbl.setText(f"🗣️ \"{text}\"")
        self.transcript_lbl.setStyleSheet("color: #0078d4; font-size: 11px; font-weight: 600;")
        # Auto-reset label after 3 seconds
        QTimer.singleShot(3500, lambda: self.set_listening_state(self.is_listening))

    def _show_commands_dialog(self):
        dialog = VoiceCommandsDialog(self, theme=self.theme)
        dialog.command_clicked.connect(self.voice_command_requested.emit)
        dialog.exec()
