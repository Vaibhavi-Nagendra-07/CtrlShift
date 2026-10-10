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
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, QSize
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QFont, QIcon, QMouseEvent, QWheelEvent, QPixmap

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

from airos.vision.camera import CameraWorker
from airos.vision.landmarks import HandDetection
from airos.gestures.state_machine import GestureStateMachine, GestureType, GestureEvent
from airos.input.native_adapter import NativeInputAdapter
from airos.storage.settings import SettingsManager

class AirOSShell(QWidget):
    """Primary Top-Level Desktop Shell of AirOS."""

    def __init__(self, settings_mgr: Optional[SettingsManager] = None):
        super().__init__()
        self.settings = settings_mgr or SettingsManager()
        current_theme_name = str(self.settings.get("theme", "vision_spatial"))
        self.theme = get_theme(current_theme_name)
        
        # State
        self.current_workspace = 0
        self.windows_by_workspace = {0: {}, 1: {}}
        self.active_window: Optional[AirWindow] = None
        self.is_tracking_paused = False

        # Input & Gestures
        self.state_machine = GestureStateMachine(config=self.settings._settings)
        self.native_adapter = NativeInputAdapter(enabled=bool(self.settings.get("native_input_enabled", False)))

        # Registered Applications Suite (VisionOS-inspired)
        self.app_registry = [
            {"id": "browser", "name": "Safari", "icon": "🧭", "color": "#007aff", "factory": lambda: BrowserApp()},
            {"id": "music", "name": "Music", "icon": "🎵", "color": "#fa2d48", "factory": lambda: MusicPlayerApp()},
            {"id": "mindfulness", "name": "Mindfulness", "icon": "🌸", "color": "#00f5d4", "factory": lambda: MindfulnessApp()},
            {"id": "microsoft", "name": "Microsoft 365", "icon": "🏢", "color": "#0078d4", "factory": lambda: MicrosoftHubApp()},
            {"id": "persona", "name": "Persona AI", "icon": "👩‍🚀", "color": "#f72585", "factory": lambda: PersonaPlaygroundApp()},
            {"id": "notes", "name": "Notes", "icon": "📝", "color": "#f59e0b", "factory": lambda: NotesApp(self.settings)},
            {"id": "gallery", "name": "Photos", "icon": "🖼️", "color": "#ec4899", "factory": lambda: GalleryApp()},
            {"id": "calc", "name": "Calculator", "icon": "🧮", "color": "#3b82f6", "factory": lambda: CalculatorApp()},
            {"id": "files", "name": "Files", "icon": "📁", "color": "#10b981", "factory": lambda: FileManagerApp()},
            {"id": "tutorial", "name": "Tutorial", "icon": "👋", "color": "#8b5cf6", "factory": lambda: self._create_tutorial()},
            {"id": "settings", "name": "Settings", "icon": "⚙️", "color": "#64748b", "factory": lambda: self._create_settings()}
        ]

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

    def _sync_settings(self):
        self.theme = get_theme(str(self.settings.get("theme", "vision_spatial")))
        self.state_machine.config = self.settings._settings
        self.native_adapter.set_enabled(bool(self.settings.get("native_input_enabled", False)))
        self.cursor_overlay.update_theme(self.theme)
        
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

        # Spatial Floating Circular Icons Dock (Center Screen)
        self.spatial_dock = QFrame(self.desktop_canvas)
        self.spatial_dock.setObjectName("SpatialDock")
        self.spatial_dock.setStyleSheet("""
            QFrame#SpatialDock {
                background-color: rgba(30, 26, 22, 0.45);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 40px;
            }
        """)
        
        dock_grid = QGridLayout(self.spatial_dock)
        dock_grid.setContentsMargins(28, 20, 28, 20)
        dock_grid.setHorizontalSpacing(32)
        dock_grid.setVerticalSpacing(20)

        for i, app in enumerate(self.app_registry):
            app_box = QVBoxLayout()
            app_box.setSpacing(6)
            app_box.setAlignment(Qt.AlignCenter)

            btn = QPushButton(app["icon"])
            btn.setFixedSize(68, 68)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qradialgradient(cx:0.4, cy:0.4, radius:0.8, fx:0.3, fy:0.3,
                                               stop:0 {app['color']}, stop:1 #111115);
                    border: 2px solid rgba(255, 255, 255, 0.35);
                    border-radius: 34px;
                    font-size: 28px;
                }}
                QPushButton:hover {{
                    border-color: #ffffff;
                    background: qradialgradient(cx:0.4, cy:0.4, radius:0.9, fx:0.3, fy:0.3,
                                               stop:0 #ffffff, stop:0.4 {app['color']}, stop:1 #111115);
                }}
            """)
            btn.clicked.connect(lambda checked, aid=app["id"]: self.launch_app(aid))
            app_box.addWidget(btn)

            lbl = QLabel(app["name"])
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: 600; text-shadow: 0 1px 4px rgba(0,0,0,0.8);")
            app_box.addWidget(lbl)

            container = QWidget()
            container.setLayout(app_box)
            r = i // 6
            c = i % 6
            dock_grid.addWidget(container, r, c)

        # Taskbar
        self.taskbar = Taskbar(self, theme=self.theme)
        self.taskbar.start_clicked.connect(self._toggle_start_menu)
        self.taskbar.workspace_changed.connect(self._switch_workspace)
        self.taskbar.window_tab_clicked.connect(self._focus_window)
        self.taskbar.keyboard_toggle_clicked.connect(self._toggle_keyboard)
        self.taskbar.control_center_clicked.connect(self._toggle_control_center)
        main_layout.addWidget(self.taskbar)

        # Control Center
        self.control_center = ControlCenterWidget(self, theme=self.theme)
        self.control_center.hide()

        # Start Menu
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

    def _init_camera_pipeline(self):
        self.camera_thread = CameraWorker(
            camera_index=int(self.settings.get("camera_index", 0)),
            target_fps=int(self.settings.get("camera_fps", 30))
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

        self._dispatch_gesture_event(event)

    def _dispatch_gesture_event(self, event: GestureEvent):
        cx = int(event.cursor_pos[0] * self.width())
        cy = int(event.cursor_pos[1] * self.height())

        if self.native_adapter.enabled:
            self.native_adapter.move_cursor(event.cursor_pos[0], event.cursor_pos[1])

        if event.gesture in (GestureType.PINCH_CLICK, GestureType.DWELL_CLICK):
            self._simulate_click_at(cx, cy)
            if self.native_adapter.enabled:
                self.native_adapter.click(event.cursor_pos[0], event.cursor_pos[1])

        elif event.gesture == GestureType.DOUBLE_CLICK:
            self._simulate_double_click_at(cx, cy)
            if self.native_adapter.enabled:
                self.native_adapter.double_click(event.cursor_pos[0], event.cursor_pos[1])

        elif event.gesture == GestureType.DRAG:
            if self.active_window and not self.active_window.is_maximized_state:
                dx = int(event.delta[0] * self.width())
                dy = int(event.delta[1] * self.height())
                self.active_window.move(self.active_window.pos() + QPoint(dx, dy))

        elif event.gesture == GestureType.SCROLL:
            self._simulate_scroll_at(cx, cy, event.delta[1])
            if self.native_adapter.enabled:
                self.native_adapter.scroll(event.delta[1])

        elif event.gesture in (GestureType.OPEN_PALM, GestureType.FIST_TOGGLE_MENU):
            self._toggle_start_menu()

        elif event.gesture == GestureType.TOGGLE_KEYBOARD:
            self._toggle_keyboard()

        elif event.gesture == GestureType.SWIPE_RIGHT:
            self.taskbar.set_workspace(1)

        elif event.gesture == GestureType.SWIPE_LEFT:
            self.taskbar.set_workspace(0)

    def _simulate_click_at(self, x: int, y: int):
        target = self.childAt(x, y)
        if target:
            local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
            press_evt = QMouseEvent(QMouseEvent.MouseButtonPress, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            release_evt = QMouseEvent(QMouseEvent.MouseButtonRelease, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
            QApplication.sendEvent(target, press_evt)
            QApplication.sendEvent(target, release_evt)
            if isinstance(target, QPushButton):
                target.animateClick(120)

    def _simulate_double_click_at(self, x: int, y: int):
        target = self.childAt(x, y)
        if target:
            local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
            dbl_evt = QMouseEvent(QMouseEvent.MouseButtonDblClick, local_pos, self.mapToGlobal(QPoint(x, y)), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            QApplication.sendEvent(target, dbl_evt)

    def _simulate_scroll_at(self, x: int, y: int, delta: float):
        target = self.childAt(x, y)
        if target:
            local_pos = target.mapFromGlobal(self.mapToGlobal(QPoint(x, y)))
            angle_delta = QPoint(0, int(delta * 120))
            wheel_evt = QWheelEvent(local_pos, self.mapToGlobal(QPoint(x, y)), QPoint(), angle_delta, Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
            QApplication.sendEvent(target, wheel_evt)

    def _on_virtual_key(self, key_text: str):
        if self.native_adapter.enabled:
            self.native_adapter.type_key(key_text)

    def _on_pause_toggled(self, paused: bool):
        self.is_tracking_paused = paused
        if self.camera_thread:
            self.camera_thread.pause_tracking(paused)

    def _toggle_start_menu(self):
        if self.start_menu.isVisible():
            self.start_menu.hide()
        else:
            self.start_menu.move(12, self.height() - self.taskbar.height() - self.start_menu.height() - 8)
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

    def launch_app(self, app_id: str):
        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            win_map[app_id].bring_to_front()
            return

        app_entry = next((a for a in self.app_registry if a["id"] == app_id), None)
        if not app_entry:
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

    def _on_window_focused(self, win: AirWindow):
        self.active_window = win

    def _on_window_closed(self, app_id: str):
        win_map = self.windows_by_workspace[self.current_workspace]
        if app_id in win_map:
            del win_map[app_id]
        self.taskbar.remove_window_tab(app_id)
        if self.active_window and self.active_window.app_id == app_id:
            self.active_window = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()

        dock_w = min(780, w - 80)
        dock_h = 240
        self.spatial_dock.setGeometry((w - dock_w) // 2, (h - self.taskbar.height() - dock_h) // 2, dock_w, dock_h)

        self.cursor_overlay.setGeometry(0, 0, w, h)
        self.cursor_overlay.raise_()

        if hasattr(self, "camera_hud"):
            self.camera_hud.move(w - self.camera_hud.width() - 16, h - self.taskbar.height() - self.camera_hud.height() - 12)
            self.camera_hud.raise_()

        if hasattr(self, "keyboard") and self.keyboard.isVisible():
            kx = (w - self.keyboard.width()) // 2
            ky = h - self.taskbar.height() - self.keyboard.height() - 16
            self.keyboard.move(kx, ky)

    def paintEvent(self, event):
        painter = QPainter(self)
        wp_path = self.theme.get("wallpaper_file", "")
        if wp_path and os.path.exists(wp_path):
            pix = QPixmap(wp_path)
            painter.drawPixmap(self.rect(), pix)
        else:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor(self.theme.get("bg_gradient_start", "#1a1614")))
            grad.setColorAt(0.5, QColor(self.theme.get("bg_gradient_mid", "#2c2622")))
            grad.setColorAt(1.0, QColor(self.theme.get("bg_gradient_end", "#14100e")))
            painter.fillRect(self.rect(), grad)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))
        painter.end()

    def closeEvent(self, event):
        if hasattr(self, "camera_thread") and self.camera_thread:
            self.camera_thread.stop()
        super().closeEvent(event)
