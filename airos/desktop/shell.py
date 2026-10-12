"""
AirOS Complete Desktop Shell with Spatial VisionOS Layout.
Features:
- Face-excluded precise hand tracking (never locks onto chin or face)
- Translucent spatial floating circular app dock / launcher
- Wallpaper selection & high-res background rendering
- Window management with multi-workspace support
- Floating Virtual Keyboard (AirType)
- Camera HUD & real-time landmark feed with Face Shield indicator
- Touchless adaptive cursor overlay
- Integrated Browser, Microsoft 365, Persona Studio, Music, Mindfulness, Notes, Calc, Files, Gallery, Settings
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QFrame, QApplication, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, QSize, Signal
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QFont, QIcon, QMouseEvent, QWheelEvent, QPixmap, QKeyEvent

from airos.desktop.theme import get_theme
from airos.desktop.taskbar import Taskbar
from airos.desktop.start_menu import StartMenu
from airos.desktop.window_manager import AirWindow
from airos.desktop.keyboard import VirtualKeyboard
from airos.desktop.camera_hud import CameraPreviewHUD
from airos.desktop.cursor_overlay import AdaptiveCursorOverlay
from airos.desktop.control_center import ControlCenterWidget

from airos.apps.notes_app import NotesApp
from airos.apps.calculator_app import CalculatorApp
from airos.apps.file_manager_app import FileManagerApp
from airos.apps.gallery_app import GalleryApp
from airos.apps.tutorial_app import TutorialApp
from airos.apps.settings_app import SettingsApp
from airos.apps.browser_app import BrowserApp
from airos.apps.microsoft_app import MicrosoftHubApp
from airos.apps.persona_app import PersonaPlaygroundApp
from airos.apps.music_app import MusicPlayerApp
from airos.apps.mindfulness_app import MindfulnessApp
from airos.apps.user_records_app import UserRecordsApp
from airos.desktop.login_overlay import BiometricLoginOverlay

from airos.vision.camera import CameraWorker
from airos.vision.landmarks import HandDetection
from airos.gestures.state_machine import GestureStateMachine, GestureType, GestureEvent
from airos.input.native_adapter import NativeInputAdapter
from airos.storage.settings import SettingsManager
from airos.desktop.draw_overlay import ScreenDrawOverlay
from airos.voice.voice_engine import VoiceEngine


class DesktopShortcutItem(QFrame):
    """Windows 11 Fluent Desktop Icon with hover highlight and launch action."""

    def __init__(self, icon_str: str, name_str: str, on_launch, parent=None, theme: dict = None):
        super().__init__(parent)
        self.on_launch = on_launch
        self.theme = theme or {}
        self.setFixedSize(82, 80)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel(icon_str)
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(icon_lbl)

        self.name_lbl = QLabel(name_str)
        self.name_lbl.setAlignment(Qt.AlignCenter)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.name_lbl.setStyleSheet("color: #1a1a1a; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 500; background: transparent;")
        layout.addWidget(self.name_lbl)

        self.setStyleSheet("""
            QFrame {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 8px;
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.45);
                border: 1px solid rgba(0, 103, 192, 0.4);
            }
        """)

    def update_theme(self, theme: dict):
        text_color = theme.get("text_primary", "#1a1a1a")
        self.name_lbl.setStyleSheet(f"color: {text_color}; font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 500; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_launch()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_launch()
        super().mouseDoubleClickEvent(event)


class HeroCardWidget(QFrame):
    """
    AirOS Centered Hero Showcase Card as featured in Windows 11 Touchless Computing (Image 1).
    Displays prominent AirOS branding, touchless gesture radar stats, and quick actions.
    """
    start_requested = Signal()
    bridge_toggled = Signal()
    tutorial_requested = Signal()

    def __init__(self, parent=None, theme: dict = None):
        super().__init__(parent)
        self.theme = theme or {}
        self._init_ui()

    def _init_ui(self):
        self.setObjectName("HeroCard")
        self.setFixedSize(540, 310)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 22, 32, 24)
        layout.setSpacing(12)

        # Header bar with badge & close button
        header = QHBoxLayout()
        badge = QLabel("SPATIAL DESKTOP • WINDOWS 11 FLUENT")
        badge.setStyleSheet("color: #0067c0; font-family: 'Segoe UI', sans-serif; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        header.addWidget(badge)
        header.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setToolTip("Hide Showcase Card")
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888888;
                border: none;
                border-radius: 13px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: rgba(0, 0, 0, 0.08); color: #000; }
        """)
        self.btn_close.clicked.connect(self.hide)
        header.addWidget(self.btn_close)
        layout.addLayout(header)

        # Hero Title (Matches user Image 1)
        self.title_lbl = QLabel("AirOS")
        self.title_lbl.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 44px;
            font-weight: 800;
            color: #1e3a5f;
            background: transparent;
        """)
        layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Touchless Spatial Computing Environment for Windows 11")
        self.sub_lbl.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            color: #55687d;
            background: transparent;
            font-weight: 500;
        """)
        layout.addWidget(self.sub_lbl)

        # Live Status Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(8)

        chip1 = QLabel("🖐️ 1-Euro Pointer: Active")
        chip1.setStyleSheet("background: rgba(16, 124, 65, 0.12); color: #107c41; border: 1px solid rgba(16, 124, 65, 0.3); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")
        chips_layout.addWidget(chip1)

        self.chip_bridge = QLabel("🪟 Windows Bridge: Standby")
        self.chip_bridge.setStyleSheet("background: rgba(0, 103, 192, 0.10); color: #0067c0; border: 1px solid rgba(0, 103, 192, 0.25); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")
        chips_layout.addWidget(self.chip_bridge)

        chip3 = QLabel("🛡️ Face Shield: Active")
        chip3.setStyleSheet("background: rgba(139, 92, 246, 0.10); color: #7c3aed; border: 1px solid rgba(139, 92, 246, 0.25); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")
        chips_layout.addWidget(chip3)
        chips_layout.addStretch()
        layout.addLayout(chips_layout)

        layout.addSpacing(6)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_apps = QPushButton("🚀 Open Start Apps")
        self.btn_apps.setFixedHeight(38)
        self.btn_apps.setStyleSheet("""
            QPushButton {
                background: #0067c0;
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
                padding: 4px 14px;
            }
            QPushButton:hover { background: #005a9e; }
        """)
        self.btn_apps.clicked.connect(self.start_requested.emit)
        btn_layout.addWidget(self.btn_apps)

        self.btn_bridge_toggle = QPushButton("⚡ Toggle Windows Desktop")
        self.btn_bridge_toggle.setFixedHeight(38)
        self.btn_bridge_toggle.setStyleSheet("""
            QPushButton {
                background: rgba(0, 103, 192, 0.12);
                color: #0067c0;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid rgba(0, 103, 192, 0.35);
                border-radius: 6px;
                padding: 4px 14px;
            }
            QPushButton:hover { background: rgba(0, 103, 192, 0.22); }
        """)
        self.btn_bridge_toggle.clicked.connect(self.bridge_toggled.emit)
        btn_layout.addWidget(self.btn_bridge_toggle)

        self.btn_guide = QPushButton("👋 Tutorial")
        self.btn_guide.setFixedHeight(38)
        self.btn_guide.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.05);
                color: #333333;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 6px;
                padding: 4px 12px;
            }
            QPushButton:hover { background: rgba(0, 0, 0, 0.10); }
        """)
        self.btn_guide.clicked.connect(self.tutorial_requested.emit)
        btn_layout.addWidget(self.btn_guide)

        layout.addLayout(btn_layout)

        self._apply_theme_style()

    def _apply_theme_style(self):
        bg = self.theme.get("card_bg", "rgba(255, 255, 255, 0.88)")
        border = self.theme.get("card_border", "rgba(0, 0, 0, 0.10)")
        text = self.theme.get("text_primary", "#1e3a5f")
        sub = self.theme.get("text_secondary", "#55687d")

        self.setStyleSheet(f"""
            QFrame#HeroCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 20px;
            }}
        """)
        self.title_lbl.setStyleSheet(f"font-family: 'Segoe UI', sans-serif; font-size: 44px; font-weight: 800; color: {text}; background: transparent;")
        self.sub_lbl.setStyleSheet(f"font-family: 'Segoe UI', sans-serif; font-size: 13px; color: {sub}; background: transparent; font-weight: 500;")

    def update_theme(self, theme: dict):
        self.theme = theme
        self._apply_theme_style()

    def update_bridge_status(self, enabled: bool):
        if enabled:
            self.chip_bridge.setText("🪟 Windows Bridge: ACTIVE")
            self.chip_bridge.setStyleSheet("background: rgba(16, 124, 65, 0.15); color: #107c41; border: 1px solid #107c41; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: bold;")
        else:
            self.chip_bridge.setText("🪟 Windows Bridge: Standby")
            self.chip_bridge.setStyleSheet("background: rgba(0, 103, 192, 0.10); color: #0067c0; border: 1px solid rgba(0, 103, 192, 0.25); border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: 600;")


class AirOSShell(QWidget):
    """Primary Top-Level Desktop Shell of AirOS."""

    def __init__(self, settings_mgr: Optional[SettingsManager] = None):
        super().__init__()
        self.settings = settings_mgr or SettingsManager()
        current_theme_name = str(self.settings.get("theme", "windows_11_fluent"))
        self.theme = get_theme(current_theme_name)
        
        # State
        self.current_workspace = 0
        self.windows_by_workspace = {0: {}, 1: {}}
        self.active_window: Optional[AirWindow] = None
        self.is_tracking_paused = False

        # Input & Gestures
        self.state_machine = GestureStateMachine(config=self.settings._settings)
        self.native_adapter = NativeInputAdapter(enabled=bool(self.settings.get("native_input_enabled", False)))

        # Registered Applications Suite (Windows 11 Fluent)
        self.app_registry = [
            {"id": "files", "name": "File Explorer", "icon": "📁", "color": "#10b981", "factory": lambda: FileManagerApp()},
            {"id": "air_draw", "name": "Draw on Screen", "icon": "✏️", "color": "#0d9488", "factory": lambda: None},
            {"id": "browser", "name": "Edge Browser", "icon": "🧭", "color": "#0078d4", "factory": lambda: BrowserApp()},
            {"id": "notes", "name": "AirNotes", "icon": "📝", "color": "#f59e0b", "factory": lambda: NotesApp(self.settings)},
            {"id": "calc", "name": "Calculator", "icon": "🧮", "color": "#3b82f6", "factory": lambda: CalculatorApp()},
            {"id": "gallery", "name": "Photos", "icon": "🖼️", "color": "#ec4899", "factory": lambda: GalleryApp()},
            {"id": "music", "name": "Music", "icon": "🎵", "color": "#fa2d48", "factory": lambda: MusicPlayerApp()},
            {"id": "mindfulness", "name": "Mindfulness", "icon": "🌸", "color": "#00f5d4", "factory": lambda: MindfulnessApp()},
            {"id": "microsoft", "name": "Microsoft 365", "icon": "🏢", "color": "#0078d4", "factory": lambda: MicrosoftHubApp()},
            {"id": "persona", "name": "Persona AI", "icon": "👩‍🚀", "color": "#f72585", "factory": lambda: PersonaPlaygroundApp()},
            {"id": "records", "name": "User Records", "icon": "📊", "color": "#38bdf8", "factory": lambda: UserRecordsApp(self.settings)},
            {"id": "tutorial", "name": "Tutorial", "icon": "👋", "color": "#8b5cf6", "factory": lambda: self._create_tutorial()},
            {"id": "settings", "name": "Settings", "icon": "⚙️", "color": "#64748b", "factory": lambda: self._create_settings()}
        ]

        # AirVoice Recognition & Synthesis Engine
        self.voice_engine = VoiceEngine(self)
        self.voice_engine.command_executed.connect(self._handle_voice_command)
        self.voice_engine.live_transcript.connect(self._on_voice_transcript)
        self.voice_engine.listening_status.connect(self._on_voice_listening_status)
        self.voice_engine.start()

        self.desktop_shortcuts = []
        self._init_ui()
        self._init_camera_pipeline()

    def _create_tutorial(self):
        tut = TutorialApp(self.settings)
        tut.settings_changed.connect(self._sync_settings)
        return tut

    def _create_settings(self):
        st = SettingsApp(self.settings)
        st.settings_updated.connect(self._sync_settings)
        return st

    def _on_control_center_toggle(self, key: str, state: bool):
        if key == "native_input":
            self.settings.set("native_input_enabled", state)
            self.native_adapter.set_enabled(state)
            if hasattr(self, "taskbar"):
                self.taskbar.update_bridge_status(state)
            if hasattr(self, "hero_card"):
                self.hero_card.update_bridge_status(state)
        elif key == "privacy":
            self.settings.set("privacy_mode", state)
            if state:
                self.camera_hud.hide()
            else:
                self.camera_hud.show()

    def _toggle_windows_bridge(self):
        new_state = not bool(self.settings.get("native_input_enabled", False))
        self.settings.set("native_input_enabled", new_state)
        self.native_adapter.set_enabled(new_state)
        if hasattr(self, "taskbar"):
            self.taskbar.update_bridge_status(new_state)
        if hasattr(self, "hero_card"):
            self.hero_card.update_bridge_status(new_state)
        if hasattr(self, "control_center"):
            self.control_center.set_toggle_state("native_input", new_state)

    def _sync_settings(self):
        self.theme = get_theme(str(self.settings.get("theme", "windows_11_fluent")))
        self.state_machine.config = self.settings._settings
        bridge_enabled = bool(self.settings.get("native_input_enabled", False))
        self.native_adapter.set_enabled(bridge_enabled)
        self.cursor_overlay.update_theme(self.theme)
        
        if hasattr(self, "control_center"):
            self.control_center.set_toggle_state("native_input", bridge_enabled)
            self.control_center.set_toggle_state("privacy", bool(self.settings.get("privacy_mode", False)))

        if hasattr(self, "taskbar"):
            self.taskbar.update_theme(self.theme)
            self.taskbar.update_bridge_status(bridge_enabled)

        if hasattr(self, "start_menu"):
            self.start_menu.update_theme(self.theme)

        if hasattr(self, "hero_card"):
            self.hero_card.update_theme(self.theme)
            self.hero_card.update_bridge_status(bridge_enabled)

        if hasattr(self, "desktop_shortcuts"):
            for sc in self.desktop_shortcuts:
                sc.update_theme(self.theme)

        if self.settings.get("privacy_mode", False):
            self.camera_hud.hide()
        else:
            self.camera_hud.show()
        self.update()

    def _init_ui(self):
        self.setWindowTitle("AirOS — Touchless Spatial Computing Environment")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Canvas
        self.desktop_canvas = QWidget(self)
        self.desktop_canvas.setObjectName("DesktopCanvas")
        main_layout.addWidget(self.desktop_canvas, 1)

        # 1. Windows 11 Desktop Shortcuts (Left Column, as in Image 1)
        self.desktop_shortcuts_container = QWidget(self.desktop_canvas)
        sc_layout = QVBoxLayout(self.desktop_shortcuts_container)
        sc_layout.setContentsMargins(0, 0, 0, 0)
        sc_layout.setSpacing(12)
        sc_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        shortcuts_info = [
            ("🗑️", "Recycle Bin", self._on_recycle_bin),
            ("📁", "This PC", lambda: self.launch_app("files")),
            ("✏️", "Draw on Screen", self._toggle_draw_overlay),
            ("🧭", "Edge Browser", lambda: self.launch_app("browser")),
            ("📝", "AirNotes", lambda: self.launch_app("notes")),
            ("🧮", "Calculator", lambda: self.launch_app("calc")),
            ("🖼️", "Photos", lambda: self.launch_app("gallery")),
            ("🎵", "Music", lambda: self.launch_app("music")),
            ("⚙️", "Settings", lambda: self.launch_app("settings")),
            ("👋", "Tutorial", lambda: self.launch_app("tutorial")),
        ]

        self.desktop_shortcuts = []
        for icon_str, name_str, cb in shortcuts_info:
            sc = DesktopShortcutItem(icon_str, name_str, cb, parent=self.desktop_shortcuts_container, theme=self.theme)
            sc_layout.addWidget(sc)
            self.desktop_shortcuts.append(sc)

        # 2. Windows 11 / AirOS Centered Hero Showcase Card (as in Image 1)
        self.hero_card = HeroCardWidget(parent=self.desktop_canvas, theme=self.theme)
        self.hero_card.start_requested.connect(self._toggle_start_menu)
        self.hero_card.bridge_toggled.connect(self._toggle_windows_bridge)
        self.hero_card.tutorial_requested.connect(lambda: self.launch_app("tutorial"))
        self.hero_card.update_bridge_status(bool(self.settings.get("native_input_enabled", False)))
        self.hero_card.show()

        # 3. Windows 11 Centered Taskbar
        self.taskbar = Taskbar(self, theme=self.theme, app_registry=self.app_registry)
        self.taskbar.start_clicked.connect(self._toggle_start_menu)
        self.taskbar.workspace_changed.connect(self._switch_workspace)
        self.taskbar.window_tab_clicked.connect(self._on_taskbar_app_clicked)
        self.taskbar.desktop_toggle_clicked.connect(self._toggle_show_desktop)
        self.taskbar.keyboard_toggle_clicked.connect(self._toggle_keyboard)
        self.taskbar.control_center_clicked.connect(self._toggle_control_center)
        self.taskbar.draw_toggle_clicked.connect(self._toggle_draw_overlay)
        self.taskbar.voice_hud.voice_command_requested.connect(self._on_simulated_voice_command)
        self.taskbar.update_bridge_status(bool(self.settings.get("native_input_enabled", False)))
        main_layout.addWidget(self.taskbar)

        # Control Center
        self.control_center = ControlCenterWidget(self, theme=self.theme)
        self.control_center.set_toggle_state("native_input", bool(self.settings.get("native_input_enabled", False)))
        self.control_center.set_toggle_state("privacy", bool(self.settings.get("privacy_mode", False)))
        self.control_center.toggle_clicked.connect(self._on_control_center_toggle)
        self.control_center.hide()

        # Start Menu (Centered Windows 11 Layout)
        self.start_menu = StartMenu(self.app_registry, self, theme=self.theme)
        self.start_menu.app_launched.connect(self.launch_app)
        self.start_menu.shutdown_requested.connect(self.close)
        self.start_menu.hide()

        # AirType Virtual Keyboard
        self.keyboard = VirtualKeyboard(self, theme=self.theme)
        self.keyboard.key_pressed.connect(self._on_virtual_key)
        self.keyboard.hide()

        # Camera HUD
        self.camera_hud = CameraPreviewHUD(self, theme=self.theme)
        self.camera_hud.pause_toggled.connect(self._on_pause_toggled)
        self.camera_hud.show()

        # Adaptive Cursor Overlay
        self.cursor_overlay = AdaptiveCursorOverlay(self, theme=self.theme)
        self.cursor_overlay.show()

        # Screen Draw Overlay (Mid-Air Annotation & Sketching)
        self.draw_overlay = ScreenDrawOverlay(self.desktop_canvas)
        self.draw_overlay.state_changed.connect(self.camera_hud.update_drawing_state)
        self.draw_overlay.closed.connect(lambda: self.camera_hud.set_drawing_mode(False))

        # Biometric Fingerprint Login & Lock Screen Overlay
        self.login_overlay = BiometricLoginOverlay(settings_mgr=self.settings, parent=self)
        self.login_overlay.unlocked.connect(self._on_user_unlocked)
        self.login_overlay.setGeometry(self.rect())
        self.start_menu.lock_requested.connect(self.lock_screen)
        if bool(self.settings.get("require_login", False)):
            self.login_overlay.lock()
        else:
            self.login_overlay.hide()

    def _init_camera_pipeline(self):
        self.camera_thread = CameraWorker(
            camera_index=int(self.settings.get("camera_index", 0)),
            target_fps=int(self.settings.get("camera_fps", 90)),
            backend=str(self.settings.get("tracking_backend", "dnn"))
        )
        self.camera_thread.frame_ready.connect(self._on_frame_ready)
        self.camera_thread.start()

    def _on_frame_ready(self, frame, detection: Optional[HandDetection]):
        if self.is_tracking_paused:
            return

        event = self.state_machine.process(detection, self.width(), self.height())

        if not self.settings.get("privacy_mode", False):
            self.camera_hud.update_frame(frame, detection, event)

        is_large = bool(self.settings.get("large_target_mode", False))
        self.cursor_overlay.update_gesture_event(event, is_large)

        # Route touchless gestures to Biometric Lock Screen if active
        if hasattr(self, "login_overlay") and self.login_overlay.isVisible():
            cx = int(event.cursor_pos[0] * self.width())
            cy = int(event.cursor_pos[1] * self.height())
            is_click = event.gesture in (GestureType.PINCH_CLICK, GestureType.DWELL_CLICK)
            self.login_overlay.process_gesture_cursor(cx, cy, is_click)
            if is_click:
                self._simulate_click_at(cx, cy)
            return

        if hasattr(self, "draw_overlay") and self.draw_overlay.isVisible():
            self.draw_overlay.process_gesture_input(event)

        self._dispatch_gesture_event(event)

    def _dispatch_gesture_event(self, event: GestureEvent):
        # Block desktop actions if Biometric Lock Screen is active
        if hasattr(self, "login_overlay") and self.login_overlay.isVisible():
            return

        cx = int(event.cursor_pos[0] * self.width())
        cy = int(event.cursor_pos[1] * self.height())

        # If drawing mode is active, avoid clicking desktop behind canvas unless clicking the banner
        if hasattr(self, "draw_overlay") and self.draw_overlay.isVisible():
            banner_rect = self.draw_overlay.banner.geometry()
            banner_global_rect = QRect(
                self.draw_overlay.mapTo(self, banner_rect.topLeft()),
                banner_rect.size()
            )
            if not banner_global_rect.contains(cx, cy):
                return

        # 1. Desktop Bridge Cursor Movement (Zero-latency hardware cursor)
        if self.native_adapter.enabled:
            self.native_adapter.move_cursor(event.cursor_pos[0], event.cursor_pos[1])

        # 2. Touchless Hover Feedback for AirOS Shell
        self._simulate_hover_at(cx, cy)

        # 3. Gesture Actions
        if event.gesture in (GestureType.PINCH_CLICK, GestureType.DWELL_CLICK):
            # Clean up native drag if active
            if self.native_adapter.enabled and self.native_adapter.is_mouse_down:
                self.native_adapter.mouse_up()
            self._simulate_click_at(cx, cy)
            self.settings.log_user_activity("Gesture", "Pinch Click", f"at ({cx}, {cy})")
            if self.native_adapter.enabled:
                self.native_adapter.click(event.cursor_pos[0], event.cursor_pos[1])

        elif event.gesture == GestureType.DOUBLE_CLICK:
            if self.native_adapter.enabled and self.native_adapter.is_mouse_down:
                self.native_adapter.mouse_up()
            self._simulate_double_click_at(cx, cy)
            self.settings.log_user_activity("Gesture", "Double Click", f"at ({cx}, {cy})")
            if self.native_adapter.enabled:
                self.native_adapter.double_click(event.cursor_pos[0], event.cursor_pos[1])

        elif event.gesture == GestureType.DRAG:
            # AirOS active window movement
            if self.active_window and not self.active_window.is_maximized_state:
                dx = int(event.delta[0] * self.width())
                dy = int(event.delta[1] * self.height())
                self.active_window.move(self.active_window.pos() + QPoint(dx, dy))
            # Desktop bridge native drag
            if self.native_adapter.enabled:
                if not self.native_adapter.is_mouse_down:
                    self.native_adapter.mouse_down(event.cursor_pos[0], event.cursor_pos[1])
                else:
                    self.native_adapter.move_cursor(event.cursor_pos[0], event.cursor_pos[1])

        elif event.gesture == GestureType.SCROLL:
            if self.native_adapter.enabled and self.native_adapter.is_mouse_down:
                self.native_adapter.mouse_up()
            self._simulate_scroll_at(cx, cy, event.delta[1])
            if self.native_adapter.enabled:
                self.native_adapter.scroll(event.delta[1])

        else:
            # If we transitioned out of drag, release native mouse button
            if self.native_adapter.enabled and self.native_adapter.is_mouse_down:
                self.native_adapter.mouse_up()

            if event.gesture in (GestureType.OPEN_PALM, GestureType.FIST_TOGGLE_MENU):
                self._toggle_start_menu()
            elif event.gesture == GestureType.TOGGLE_KEYBOARD:
                self._toggle_keyboard()
            elif event.gesture == GestureType.SWIPE_RIGHT:
                self.taskbar.set_workspace(1)
            elif event.gesture == GestureType.SWIPE_LEFT:
                self.taskbar.set_workspace(0)

    def _simulate_hover_at(self, x: int, y: int):
        target = self.childAt(x, y)
        if target and target != self.cursor_overlay:
            local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
            move_evt = QMouseEvent(
                QMouseEvent.MouseMove,
                local_pos,
                self.mapToGlobal(QPoint(x, y)),
                Qt.NoButton,
                Qt.NoButton,
                Qt.NoModifier
            )
            QApplication.sendEvent(target, move_evt)

    def _simulate_click_at(self, x: int, y: int):
        try:
            target = self.childAt(x, y)
            if target == self.cursor_overlay:
                self.cursor_overlay.hide()
                target = self.childAt(x, y)
                self.cursor_overlay.show()

            if target:
                # Check if clicking on desktop shortcut item
                p = target
                while p and p != self:
                    if isinstance(p, DesktopShortcutItem):
                        p.on_launch()
                        return
                    if isinstance(p, AirWindow):
                        p.bring_to_front()
                        self.active_window = p
                        break
                    p = p.parent()

                local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
                press_evt = QMouseEvent(QMouseEvent.MouseButtonPress, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
                release_evt = QMouseEvent(QMouseEvent.MouseButtonRelease, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
                QApplication.sendEvent(target, press_evt)
                QApplication.sendEvent(target, release_evt)
                if isinstance(target, QPushButton):
                    try:
                        target.animateClick()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[AirOS Shell] Click simulation warning: {e}")

    def _simulate_double_click_at(self, x: int, y: int):
        try:
            target = self.childAt(x, y)
            if target == self.cursor_overlay:
                self.cursor_overlay.hide()
                target = self.childAt(x, y)
                self.cursor_overlay.show()

            if target:
                p = target
                while p and p != self:
                    if isinstance(p, DesktopShortcutItem):
                        p.on_launch()
                        return
                    if isinstance(p, AirWindow):
                        p.bring_to_front()
                        self.active_window = p
                        break
                    p = p.parent()

                local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
                dbl_evt = QMouseEvent(QMouseEvent.MouseButtonDblClick, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(target, dbl_evt)
        except Exception as e:
            print(f"[AirOS Shell] Double click simulation warning: {e}")

    def _simulate_scroll_at(self, x: int, y: int, delta: float):
        try:
            target = self.childAt(x, y)
            if target:
                local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
                angle_delta = QPoint(0, int(delta * 120))
                wheel_evt = QWheelEvent(local_pos, self.mapToGlobal(QPoint(x, y)), QPoint(), angle_delta, Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
                QApplication.sendEvent(target, wheel_evt)
        except Exception as e:
            print(f"[AirOS Shell] Scroll simulation warning: {e}")

    def _on_virtual_key(self, key_text: str):
        # 1. Native Windows typing bridge
        if self.native_adapter.enabled:
            self.native_adapter.type_key(key_text)

        # 2. In-app Qt focus widget typing
        focus_w = QApplication.focusWidget()
        if focus_w:
            if key_text == "Backspace":
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier))
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyRelease, Qt.Key_Backspace, Qt.NoModifier))
            elif key_text == "Enter":
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n"))
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyRelease, Qt.Key_Return, Qt.NoModifier, "\n"))
            elif key_text == "Space":
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Space, Qt.NoModifier, " "))
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyRelease, Qt.Key_Space, Qt.NoModifier, " "))
            elif len(key_text) == 1:
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyPress, 0, Qt.NoModifier, key_text))
                QApplication.sendEvent(focus_w, QKeyEvent(QKeyEvent.KeyRelease, 0, Qt.NoModifier, key_text))

    def _on_pause_toggled(self, paused: bool):
        self.is_tracking_paused = paused
        if self.camera_thread:
            self.camera_thread.pause_tracking(paused)

    def _on_recycle_bin(self):
        QMessageBox.information(
            self,
            "Recycle Bin",
            "🗑️ <b>AirOS Recycle Bin</b><br><br>"
            "Status: Clean & Empty<br>"
            "All temporary cache buffers are clear."
        )

    def _toggle_start_menu(self):
        if self.start_menu.isVisible():
            self.start_menu.hide()
        else:
            sx = (self.width() - self.start_menu.width()) // 2
            sy = self.height() - self.taskbar.height() - self.start_menu.height() - 10
            self.start_menu.move(sx, sy)
            self.start_menu.show()
            self.start_menu.raise_()

    def _toggle_control_center(self):
        if self.control_center.isVisible():
            self.control_center.hide()
        else:
            cx = self.width() - self.control_center.width() - 16
            cy = self.height() - self.taskbar.height() - self.control_center.height() - 8
            self.control_center.move(cx, cy)
            self.control_center.show()
            self.control_center.raise_()

    def _toggle_keyboard(self):
        if self.keyboard.isVisible():
            self.keyboard.hide()
        else:
            kx = (self.width() - self.keyboard.width()) // 2
            ky = self.height() - self.taskbar.height() - self.keyboard.height() - 16
            self.keyboard.move(kx, ky)
            self.keyboard.show()
            self.keyboard.raise_()

    def _toggle_show_desktop(self):
        win_map = self.windows_by_workspace[self.current_workspace]
        any_visible = any(win.isVisible() for win in win_map.values())
        for win in win_map.values():
            if any_visible:
                win.hide()
            else:
                win.show()
        if not any_visible and hasattr(self, "hero_card"):
            self.hero_card.show()

    def _on_taskbar_app_clicked(self, app_id: str):
        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            win = win_map[app_id]
            if win.isVisible():
                if self.active_window == win:
                    win.minimize_window()
                else:
                    win.bring_to_front()
                    self.active_window = win
                    self.taskbar.set_active_app(app_id)
            else:
                win.show()
                win.bring_to_front()
                self.active_window = win
                self.taskbar.set_active_app(app_id)
        else:
            self.launch_app(app_id)

    def _switch_workspace(self, ws: int):
        self.current_workspace = ws
        for w_idx, win_map in self.windows_by_workspace.items():
            for app_id, win in win_map.items():
                if w_idx == ws:
                    win.show()
                else:
                    win.hide()

    def _focus_window(self, app_id: str):
        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            win = win_map[app_id]
            win.show()
            win.bring_to_front()
            self.active_window = win
            self.taskbar.set_active_app(app_id)

    def launch_app(self, app_id: str):
        if app_id == "air_draw":
            self._toggle_draw_overlay()
            return

        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            win = win_map[app_id]
            win.show()
            win.bring_to_front()
            self.active_window = win
            self.taskbar.set_active_app(app_id)
            return

        app_entry = next((a for a in self.app_registry if a["id"] == app_id), None)
        if not app_entry or not app_entry.get("factory"):
            return

        content = app_entry["factory"]()
        win = AirWindow(app_id, app_entry["name"], content, parent=self.desktop_canvas, theme=self.theme)
        
        win.resize(820, 530)
        offset = (len(win_map) * 35) % 180
        win.move(140 + offset, 45 + offset)
        win.window_closed.connect(self._on_window_closed)
        win.window_focused.connect(lambda aid: self._on_window_focused(win))
        win.show()
        win.bring_to_front()

        win_map[app_id] = win
        self.active_window = win
        self.taskbar.add_window_tab(app_id, app_entry["name"])
        self.settings.log_recent_app(app_id, app_entry["name"], app_entry.get("icon", ""))
        self.settings.log_user_activity("App", f"Launched {app_entry['name']}", f"app_id={app_id}")

    def _toggle_draw_overlay(self):
        if not hasattr(self, "draw_overlay"):
            return
        if self.draw_overlay.isVisible():
            self.draw_overlay.hide_overlay()
            self.camera_hud.set_drawing_mode(False)
        else:
            self.draw_overlay.setGeometry(0, 0, self.desktop_canvas.width(), self.desktop_canvas.height())
            self.draw_overlay.show_overlay()
            self.camera_hud.set_drawing_mode(True, "hover")
            if hasattr(self, "cursor_overlay"):
                self.cursor_overlay.raise_()

    def _handle_voice_command(self, command_id: str, params: dict):
        if command_id == "CMD_DRAW_START":
            if hasattr(self, "draw_overlay") and not self.draw_overlay.isVisible():
                self._toggle_draw_overlay()
        elif command_id == "CMD_DRAW_STOP":
            if hasattr(self, "draw_overlay") and self.draw_overlay.isVisible():
                self._toggle_draw_overlay()
        elif command_id == "CMD_DRAW_CLEAR":
            if hasattr(self, "draw_overlay"):
                self.draw_overlay.clear_canvas()
        elif command_id == "CMD_DRAW_COLOR":
            col = params.get("color")
            if hasattr(self, "draw_overlay") and col:
                self.draw_overlay.set_color(col)
        elif command_id == "CMD_DRAW_TOOL":
            tool = params.get("tool")
            if hasattr(self, "draw_overlay") and tool:
                self.draw_overlay.set_tool(tool)
        elif command_id == "CMD_DRAW_SHAPE_SNAP":
            if hasattr(self, "draw_overlay"):
                self.draw_overlay.banner._toggle_snap()
        elif command_id == "CMD_DRAW_UNDO":
            if hasattr(self, "draw_overlay"):
                self.draw_overlay.undo_stroke()
        elif command_id == "CMD_DRAW_REDO":
            if hasattr(self, "draw_overlay"):
                self.draw_overlay.redo_stroke()
        elif command_id == "CMD_DRAW_SAVE":
            if hasattr(self, "draw_overlay"):
                self.draw_overlay.save_snapshot()
        elif command_id == "CMD_LAUNCH_APP":
            app_id = params.get("app_id")
            if app_id:
                self.launch_app(app_id)
        elif command_id == "CMD_TOGGLE_DESKTOP":
            self._toggle_show_desktop()
        elif command_id == "CMD_TOGGLE_MENU":
            self._toggle_start_menu()
        elif command_id == "CMD_TOGGLE_KEYBOARD":
            self._toggle_keyboard()
        elif command_id == "CMD_TOGGLE_CONTROL_CENTER":
            self._toggle_control_center()
        elif command_id == "CMD_SET_WORKSPACE":
            ws = params.get("workspace", 0)
            self.taskbar.set_workspace(ws)
            self._switch_workspace(ws)
        elif command_id == "CMD_PAUSE_TRACKING":
            if not self.is_tracking_paused:
                self.camera_hud._toggle_pause()
        elif command_id == "CMD_RESUME_TRACKING":
            if self.is_tracking_paused:
                self.camera_hud._toggle_pause()
        elif command_id == "CMD_TOGGLE_BRIDGE":
            self._toggle_windows_bridge()
        elif command_id == "CMD_LOCK_SCREEN":
            self.lock_screen()
        elif command_id == "CMD_SHOW_HELP":
            if hasattr(self, "taskbar") and hasattr(self.taskbar, "voice_hud"):
                self.taskbar.voice_hud._show_commands_dialog()

        # Log executed voice command in activity records
        self.settings.log_user_activity("Voice", f"Voice: {cmd.feedback_text}", f"id={command_id}, text='{cmd.raw_text}'")

    def _on_simulated_voice_command(self, text: str):
        if hasattr(self, "voice_engine"):
            self.voice_engine.simulate_voice_input(text)

    def _on_voice_transcript(self, text: str):
        if hasattr(self, "taskbar") and hasattr(self.taskbar, "voice_hud"):
            self.taskbar.voice_hud.set_heard_transcript(text)

    def _on_voice_listening_status(self, is_listening: bool):
        if hasattr(self, "taskbar") and hasattr(self.taskbar, "voice_hud"):
            self.taskbar.voice_hud.set_listening_state(is_listening)

    def _on_window_focused(self, win: AirWindow):
        self.active_window = win
        self.taskbar.set_active_app(win.app_id)

    def _on_window_closed(self, app_id: str):
        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            del win_map[app_id]
        self.taskbar.remove_window_tab(app_id)
        if self.active_window and self.active_window.app_id == app_id:
            self.active_window = None
        self.settings.log_user_activity("App", f"Closed {app_id}", f"app_id={app_id}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()

        # 1. Desktop shortcuts on left
        if hasattr(self, "desktop_shortcuts_container"):
            self.desktop_shortcuts_container.setGeometry(16, 16, 92, h - self.taskbar.height() - 24)

        # 2. Windows 11 AirOS Hero Showcase Card in Center
        if hasattr(self, "hero_card"):
            card_w = min(540, w - 240)
            card_h = 310
            card_x = (w - card_w) // 2
            card_y = (h - self.taskbar.height() - card_h) // 2
            self.hero_card.setGeometry(card_x, card_y, card_w, card_h)

        # 3. Transparent Cursor Overlay
        self.cursor_overlay.setGeometry(0, 0, w, h)
        self.cursor_overlay.raise_()

        # 4. Camera HUD in corner
        if hasattr(self, "camera_hud"):
            self.camera_hud.move(w - self.camera_hud.width() - 16, h - self.taskbar.height() - self.camera_hud.height() - 12)
            self.camera_hud.raise_()

        # 5. Virtual Keyboard
        if hasattr(self, "keyboard") and self.keyboard.isVisible():
            kx = (w - self.keyboard.width()) // 2
            ky = h - self.taskbar.height() - self.keyboard.height() - 16
            self.keyboard.move(kx, ky)

        # 6. Start Menu Centered
        if hasattr(self, "start_menu") and self.start_menu.isVisible():
            sx = (w - self.start_menu.width()) // 2
            sy = h - self.taskbar.height() - self.start_menu.height() - 10
            self.start_menu.move(sx, sy)

        # 7. Screen Draw Overlay
        if hasattr(self, "draw_overlay"):
            self.draw_overlay.setGeometry(0, 0, self.desktop_canvas.width(), self.desktop_canvas.height())

        # 8. Biometric Fingerprint Lock Screen Overlay
        if hasattr(self, "login_overlay"):
            self.login_overlay.setGeometry(0, 0, w, h)
            if self.login_overlay.isVisible():
                self.login_overlay.raise_()

    def lock_screen(self):
        """Locks the AirOS desktop with Biometric Fingerprint Authentication."""
        if hasattr(self, "login_overlay"):
            self.login_overlay.setGeometry(self.rect())
            self.login_overlay.lock()
            if hasattr(self, "cursor_overlay"):
                self.cursor_overlay.raise_()

    def _on_user_unlocked(self, user_name: str):
        """Callback when user authenticates via fingerprint or PIN."""
        print(f"[AirOS Auth] Successfully authenticated user: {user_name}")
        self.settings.set("current_user_name", user_name)
        if hasattr(self, "start_menu"):
            self.start_menu.update_user(user_name)
        if hasattr(self, "taskbar") and hasattr(self.taskbar, "voice_hud"):
            self.taskbar.voice_hud.set_heard_transcript(f"Welcome back, {user_name}!")

    def paintEvent(self, event):
        painter = QPainter(self)
        wp_path = self.theme.get("wallpaper_file", "")
        if wp_path and os.path.exists(wp_path):
            pix = QPixmap(wp_path)
            painter.drawPixmap(self.rect(), pix)
        else:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor(self.theme.get("bg_gradient_start", "#dce5ef")))
            grad.setColorAt(0.5, QColor(self.theme.get("bg_gradient_mid", "#c5d6e8")))
            grad.setColorAt(1.0, QColor(self.theme.get("bg_gradient_end", "#b0c4de")))
            painter.fillRect(self.rect(), grad)

        # Apply subtle dark tint only for dark themes
        if "dark" in self.theme.get("name", "").lower():
            painter.fillRect(self.rect(), QColor(0, 0, 0, 35))

        painter.end()

    def closeEvent(self, event):
        if hasattr(self, "voice_engine") and self.voice_engine:
            self.voice_engine.stop()
        if hasattr(self, "camera_thread") and self.camera_thread:
            self.camera_thread.stop()
        super().closeEvent(event)
