"""
AirOS Voice Command Recognition and Speech Synthesis Engine (AirVoice).
Features:
- Continuous ambient speech recognition in background QThread
- Command vocabulary matching with natural language aliases
- Asynchronous non-blocking Text-To-Speech audio feedback via pyttsx3
- Mute/Unmute state persistence
"""

import time
import queue
import threading
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal

# Optional dependencies with safe fallbacks
try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False


@dataclass
class VoiceCommand:
    command_id: str
    raw_text: str
    params: Dict[str, Any]
    feedback_text: str


class VoiceCommandParser:
    """Natural language rule matcher for AirOS voice commands."""

    @staticmethod
    def parse(text: str) -> Optional[VoiceCommand]:
        raw = text.strip().lower()
        if not raw:
            return None

        # Helper for word boundary matching
        import re

        # 1. Stop / Close Drawing (Check BEFORE start drawing / draw)
        if any(p in raw for p in ("stop drawing", "exit drawing", "close drawing", "stop draw", "close draw", "exit draw")):
            return VoiceCommand("CMD_DRAW_STOP", raw, {}, "Drawing mode closed.")

        # 2. Application Launch Commands (Check BEFORE single words like 'pen')
        if any(p in raw for p in ("open notes", "air notes", "notes")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "notes"}, "Opening AirNotes.")
        if any(p in raw for p in ("open calculator", "calculator", "calc")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "calc"}, "Opening Calculator.")
        if any(p in raw for p in ("open files", "file manager", "file explorer", "this pc")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "files"}, "Opening File Explorer.")
        if any(p in raw for p in ("open browser", "open edge", "browser", "edge")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "browser"}, "Opening Edge Browser.")
        if any(p in raw for p in ("open photos", "open gallery", "photos", "gallery")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "gallery"}, "Opening Photos.")
        if any(p in raw for p in ("open music", "play music", "music player", "music")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "music"}, "Opening Music.")
        if any(p in raw for p in ("open mindfulness", "meditation")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "mindfulness"}, "Opening Mindfulness.")
        if any(p in raw for p in ("open microsoft", "microsoft 365", "office")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "microsoft"}, "Opening Microsoft 365.")
        if any(p in raw for p in ("open persona", "persona ai", "assistant")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "persona"}, "Opening Persona AI.")
        if any(p in raw for p in ("open tutorial", "tutorial", "how to use")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "tutorial"}, "Opening Tutorial.")
        if any(p in raw for p in ("open settings", "settings", "configuration")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "settings"}, "Opening Settings.")
        if any(p in raw for p in ("open records", "user records", "activity log", "show records", "audit log", "records")):
            return VoiceCommand("CMD_LAUNCH_APP", raw, {"app_id": "records"}, "Opening User Records.")

        # 3. Screen Draw Start Commands
        if any(p in raw for p in ("start drawing", "start draw", "draw on screen", "open draw", "air draw", "air canvas")) or re.search(r'\bdraw\b', raw):
            return VoiceCommand("CMD_DRAW_START", raw, {}, "Drawing mode activated.")

        if any(p in raw for p in ("clear screen", "clear drawing", "clear draw", "clear all", "clean screen", "clear")):
            return VoiceCommand("CMD_DRAW_CLEAR", raw, {}, "Screen cleared.")

        # Color commands
        if "blue" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#1e60ff"}, "Ink set to blue.")
        if "red" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#ef4444"}, "Ink set to red.")
        if "green" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#10b981"}, "Ink set to green.")
        if "yellow" in raw or "amber" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#f59e0b"}, "Ink set to yellow.")
        if "purple" in raw or "violet" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#a855f7"}, "Ink set to purple.")
        if "white" in raw:
            return VoiceCommand("CMD_DRAW_COLOR", raw, {"color": "#ffffff"}, "Ink set to white.")

        # Tools (Use word boundary for 'pen' to prevent matching 'open')
        if any(p in raw for p in ("eraser", "erase")):
            return VoiceCommand("CMD_DRAW_TOOL", raw, {"tool": "eraser"}, "Eraser active.")
        if re.search(r'\bpen\b', raw) or "pencil" in raw or "brush" in raw:
            return VoiceCommand("CMD_DRAW_TOOL", raw, {"tool": "pen"}, "Pen active.")
        if any(p in raw for p in ("highlighter", "highlight")):
            return VoiceCommand("CMD_DRAW_TOOL", raw, {"tool": "highlighter"}, "Highlighter active.")
        if any(p in raw for p in ("laser pointer", "laser")):
            return VoiceCommand("CMD_DRAW_TOOL", raw, {"tool": "laser"}, "Laser pointer active.")

        # Geometry snapping & History
        if any(p in raw for p in ("shape snap", "smart snap", "smart shape", "auto shape", "snap shapes", "snap shape")):
            return VoiceCommand("CMD_DRAW_SHAPE_SNAP", raw, {}, "Shape snap toggled.")
        if any(p in raw for p in ("undo", "step back")):
            return VoiceCommand("CMD_DRAW_UNDO", raw, {}, "Undid stroke.")
        if any(p in raw for p in ("redo", "step forward")):
            return VoiceCommand("CMD_DRAW_REDO", raw, {}, "Redid stroke.")

        # Snapshot
        if any(p in raw for p in ("save drawing", "save screen", "take screenshot", "screenshot", "snapshot", "capture")):
            return VoiceCommand("CMD_DRAW_SAVE", raw, {}, "Saving screen snapshot.")

        # 3. System Shell Controls
        if any(p in raw for p in ("show desktop", "minimize all", "hide windows")):
            return VoiceCommand("CMD_TOGGLE_DESKTOP", raw, {}, "Toggling desktop.")
        if any(p in raw for p in ("start menu", "open start", "launcher", "open menu")):
            return VoiceCommand("CMD_TOGGLE_MENU", raw, {}, "Toggling Start Menu.")
        if any(p in raw for p in ("virtual keyboard", "show keyboard", "open keyboard", "hide keyboard", "keyboard")):
            return VoiceCommand("CMD_TOGGLE_KEYBOARD", raw, {}, "Toggling Virtual Keyboard.")
        if any(p in raw for p in ("control center", "quick settings")):
            return VoiceCommand("CMD_TOGGLE_CONTROL_CENTER", raw, {}, "Toggling Control Center.")
        if any(p in raw for p in ("workspace one", "space one")):
            return VoiceCommand("CMD_SET_WORKSPACE", raw, {"workspace": 0}, "Switched to Space 1.")
        if any(p in raw for p in ("workspace two", "space two")):
            return VoiceCommand("CMD_SET_WORKSPACE", raw, {"workspace": 1}, "Switched to Space 2.")

        # Safety & Tracking Controls
        if any(p in raw for p in ("lock screen", "lock computer", "lock pc", "lock system", "lock")):
            return VoiceCommand("CMD_LOCK_SCREEN", raw, {}, "Screen locked.")
        if any(p in raw for p in ("pause tracking", "pause camera", "freeze tracking", "pause")):
            return VoiceCommand("CMD_PAUSE_TRACKING", raw, {}, "Touchless tracking paused.")
        if any(p in raw for p in ("resume tracking", "resume camera", "resume")):
            return VoiceCommand("CMD_RESUME_TRACKING", raw, {}, "Touchless tracking resumed.")
        if any(p in raw for p in ("windows bridge", "desktop bridge", "mouse bridge")):
            return VoiceCommand("CMD_TOGGLE_BRIDGE", raw, {}, "Toggling Windows bridge.")

        # Audio & Feedback Controls
        if any(p in raw for p in ("mute voice", "silent mode", "be quiet")):
            return VoiceCommand("CMD_MUTE_VOICE", raw, {}, "Voice feedback muted.")
        if any(p in raw for p in ("unmute voice", "enable voice")):
            return VoiceCommand("CMD_UNMUTE_VOICE", raw, {}, "Voice feedback enabled.")

        # Help
        if any(p in raw for p in ("voice help", "what can i say", "show commands", "voice commands")):
            return VoiceCommand("CMD_SHOW_HELP", raw, {}, "Displaying voice commands list.")

        return None


class SpeechSynthesisWorker(QThread):
    """Background worker for non-blocking Text-To-Speech responses."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._running = True
        self.muted = False
        self._engine = None

    def run(self):
        if HAS_TTS:
            try:
                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", 175)
                self._engine.setProperty("volume", 0.9)
            except Exception as e:
                print(f"[AirVoice TTS] Initialization note: {e}")
                self._engine = None

        while self._running:
            try:
                text = self._queue.get(timeout=0.3)
                if text and self._engine and not self.muted:
                    try:
                        self._engine.say(text)
                        self._engine.runAndWait()
                    except Exception as e:
                        print(f"[AirVoice TTS] Speech output error: {e}")
                self._queue.task_done()
            except queue.Empty:
                continue

    def speak(self, text: str):
        if not self.muted and text:
            self._queue.put(text)

    def stop(self):
        self._running = False
        self.wait(1000)


class SpeechRecognitionWorker(QThread):
    """Continuous background microphone listener."""

    speech_detected = Signal()
    command_heard = Signal(str, str, dict, str) # (command_id, raw_text, params, feedback_text)
    transcript_updated = Signal(str)
    listening_state_changed = Signal(bool)
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._recognizer: Optional[Any] = None
        self._microphone: Optional[Any] = None

    def run(self):
        if not HAS_SR:
            self.status_changed.emit("SpeechRecognition package not available")
            return

        try:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()

            self.status_changed.emit("Calibrating ambient noise...")
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.8)

            self.status_changed.emit("Listening for voice commands...")
        except Exception as e:
            self.status_changed.emit(f"Microphone init failed: {e}")
            return

        while self._running:
            try:
                self.listening_state_changed.emit(True)
                with self._microphone as source:
                    try:
                        audio = self._recognizer.listen(source, timeout=2.5, phrase_time_limit=4.0)
                    except sr.WaitTimeoutError:
                        continue

                self.speech_detected.emit()
                self.listening_state_changed.emit(False)

                try:
                    text = self._recognizer.recognize_google(audio)
                    if text:
                        self.transcript_updated.emit(text)
                        cmd = VoiceCommandParser.parse(text)
                        if cmd:
                            self.command_heard.emit(
                                cmd.command_id, cmd.raw_text, cmd.params, cmd.feedback_text
                            )
                except sr.UnknownValueError:
                    pass # Unrecognized ambient sound
                except sr.RequestError as e:
                    self.status_changed.emit(f"Speech service error: {e}")

            except Exception as e:
                time.sleep(0.5)

    def stop(self):
        self._running = False
        self.wait(1200)


class VoiceEngine(QObject):
    """
    Main coordinator for AirVoice Voice Commands.
    Bridges speech recognition, natural language command parsing,
    and text-to-speech audio feedback.
    """

    command_executed = Signal(str, dict) # (command_id, params)
    live_transcript = Signal(str)
    listening_status = Signal(bool)
    feedback_spoken = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_enabled = True
        self.is_muted = False

        self.synth_worker = SpeechSynthesisWorker()
        self.synth_worker.start()

        self.listen_worker = SpeechRecognitionWorker()
        self.listen_worker.command_heard.connect(self._on_command_heard)
        self.listen_worker.transcript_updated.connect(self.live_transcript.emit)
        self.listen_worker.listening_state_changed.connect(self.listening_status.emit)

    def start(self):
        if not self.listen_worker.isRunning():
            self.listen_worker.start()

    def stop(self):
        if self.listen_worker.isRunning():
            self.listen_worker.stop()
        if self.synth_worker.isRunning():
            self.synth_worker.stop()

    def set_muted(self, muted: bool):
        self.is_muted = muted
        self.synth_worker.muted = muted

    def speak(self, text: str):
        if not self.is_muted:
            self.synth_worker.speak(text)
            self.feedback_spoken.emit(text)

    def simulate_voice_input(self, text: str):
        """Allows testing or keyboard/UI triggered command execution."""
        cmd = VoiceCommandParser.parse(text)
        if cmd:
            self._on_command_heard(cmd.command_id, cmd.raw_text, cmd.params, cmd.feedback_text)
            return True
        return False

    def _on_command_heard(self, command_id: str, raw_text: str, params: dict, feedback_text: str):
        # Handle engine-internal commands
        if command_id == "CMD_MUTE_VOICE":
            self.set_muted(True)
        elif command_id == "CMD_UNMUTE_VOICE":
            self.set_muted(False)

        # Speak voice confirmation
        if feedback_text:
            self.speak(feedback_text)

        # Dispatch command to shell
        self.command_executed.emit(command_id, params)
