"""
AirOS Built-in Application: System Settings & Personalization.
Theme selector, Privacy Mode, IntentLock toggles, Native Windows Mouse bridge,
and Handedness preferences.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QTabWidget, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from airos.storage.settings import SettingsManager

class SettingsApp(QWidget):
    settings_updated = Signal()

    def __init__(self, settings_mgr: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(20, 20, 26, 0.95); border-radius: 8px; }
            QTabBar::tab { background: rgba(30, 30, 40, 0.8); color: #8b949e; padding: 10px 20px; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; margin-right: 4px; }
            QTabBar::tab:selected { background: #f59e0b; color: black; font-weight: bold; }
        """)

        # Tab 1: Personalization & Spatial Wallpapers
        tab_theme = QWidget()
        t_layout = QVBoxLayout(tab_theme)
        t_layout.setSpacing(14)

        theme_box = QHBoxLayout()
        t_lbl = QLabel("Active Environment & Wallpaper:")
        t_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        theme_box.addWidget(t_lbl)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems([
            "vision_spatial",
            "cosmic_nebula",
            "dark_modern",
            "glass_morphism",
            "high_contrast"
        ])
        self.combo_theme.setCurrentText(str(self.settings.get("theme", "vision_spatial")))
        self.combo_theme.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.12);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        self.combo_theme.currentTextChanged.connect(self._on_theme_change)
        theme_box.addWidget(self.combo_theme)
        t_layout.addLayout(theme_box)

        desc_lbl = QLabel(
            "<b>Included Spatial Wallpapers:</b><br>"
            "• <b>Vision Spatial:</b> Warm ambient architectural living room with fireplace hearth illumination.<br>"
            "• <b>Cosmic Aurora:</b> Deep space violet and teal nebula with glowing spatial orbs.<br>"
            "• <b>Dark Modern:</b> Frosted graphite titanium minimalism.<br>"
            "• <b>High Contrast:</b> Pure black background with accessible gold highlights."
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #d6cec7; background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 8px;")
        t_layout.addWidget(desc_lbl)

        t_layout.addStretch()
        tabs.addTab(tab_theme, "Wallpapers & Themes")

        # Tab 2: Gestures & IntentLock
        tab_gestures = QWidget()
        g_layout = QVBoxLayout(tab_gestures)
        g_layout.setSpacing(12)
        
        self.chk_intent = QCheckBox("Enable IntentLock™ (requires dwell verification to prevent misclicks)")
        self.chk_intent.setChecked(bool(self.settings.get("intent_lock_enabled", True)))
        self.chk_intent.setStyleSheet("color: #f0f6fc; font-weight: bold;")
        self.chk_intent.toggled.connect(self._on_intent_toggled)
        g_layout.addWidget(self.chk_intent)

        self.chk_native = QCheckBox("Enable Windows Native Mouse & Keyboard Desktop Control (Hardware Bridge)")
        self.chk_native.setChecked(bool(self.settings.get("native_input_enabled", False)))
        self.chk_native.setStyleSheet("color: #f0f6fc; font-weight: bold;")
        self.chk_native.toggled.connect(self._on_native_toggled)
        g_layout.addWidget(self.chk_native)

        self.chk_large = QCheckBox("Large-Target Accessibility Mode (Magnified cursors & targets)")
        self.chk_large.setChecked(bool(self.settings.get("large_target_mode", False)))
        self.chk_large.setStyleSheet("color: #f0f6fc;")
        self.chk_large.toggled.connect(self._on_large_toggled)
        g_layout.addWidget(self.chk_large)

        g_layout.addStretch()
        tabs.addTab(tab_gestures, "Gestures & Input")

        # Tab 3: Privacy & Camera
        tab_privacy = QWidget()
        p_layout = QVBoxLayout(tab_privacy)

        self.chk_privacy = QCheckBox("Privacy Mode (Completely hide camera preview HUD)")
        self.chk_privacy.setChecked(bool(self.settings.get("privacy_mode", False)))
        self.chk_privacy.setStyleSheet("color: #f0f6fc;")
        self.chk_privacy.toggled.connect(self._on_privacy_toggled)
        p_layout.addWidget(self.chk_privacy)

        # Camera & Motion Engine FPS
        fps_box = QHBoxLayout()
        fps_lbl = QLabel("Target Refresh Rate (Motion Engine FPS):")
        fps_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        fps_box.addWidget(fps_lbl)

        self.combo_fps = QComboBox()
        self.combo_fps.addItem("90 FPS (Ultra Smooth & Stable - Recommended)", 90)
        self.combo_fps.addItem("60 FPS (Balanced Smoothness)", 60)
        self.combo_fps.addItem("120 FPS (High Refresh Gaming)", 120)
        self.combo_fps.addItem("30 FPS (Power Saver)", 30)

        current_fps = int(self.settings.get("camera_fps", 90))
        idx = self.combo_fps.findData(current_fps)
        if idx >= 0:
            self.combo_fps.setCurrentIndex(idx)
        else:
            self.combo_fps.setCurrentIndex(0)

        self.combo_fps.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.12);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        self.combo_fps.currentIndexChanged.connect(self._on_fps_changed)
        fps_box.addWidget(self.combo_fps)
        p_layout.addLayout(fps_box)

        info_p = QLabel(
            "🔒 <b>AirOS On-Device Privacy & 90 FPS Performance:</b><br>"
            "Computer vision inference and 90 FPS motion synthesis run entirely on local CPU.<br>"
            "Webcam frames are analyzed strictly in volatile memory and never recorded or transmitted."
        )
        info_p.setWordWrap(True)
        info_p.setStyleSheet("color: #10b981; background: rgba(16, 185, 129, 0.1); padding: 12px; border: 1px solid #10b981; border-radius: 8px;")
        p_layout.addWidget(info_p)

        p_layout.addStretch()
        tabs.addTab(tab_privacy, "Privacy & Camera")

        # Tab 4: User Profile & Biometric Security
        tab_sec = QWidget()
        s_layout = QVBoxLayout(tab_sec)
        s_layout.setSpacing(12)

        u_box = QHBoxLayout()
        u_lbl = QLabel("User Profile Name:")
        u_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        u_box.addWidget(u_lbl)
        self.txt_username = QLineEdit(str(self.settings.get("current_user_name", "Admin User")))
        self.txt_username.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        u_box.addWidget(self.txt_username)
        s_layout.addLayout(u_box)

        pin_box = QHBoxLayout()
        pin_lbl = QLabel("Security PIN Code (Fallback):")
        pin_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        pin_box.addWidget(pin_lbl)
        self.txt_pin = QLineEdit(str(self.settings.get("security_pin", "1234")))
        self.txt_pin.setMaxLength(8)
        self.txt_pin.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        pin_box.addWidget(self.txt_pin)
        s_layout.addLayout(pin_box)

        self.chk_require_login = QCheckBox("Require Biometric Fingerprint / PIN on Startup")
        self.chk_require_login.setChecked(bool(self.settings.get("require_login", False)))
        self.chk_require_login.setStyleSheet("color: #f0f6fc; font-weight: bold;")
        s_layout.addWidget(self.chk_require_login)

        self.chk_activity_log = QCheckBox("Enable User Activity Logging & Records")
        self.chk_activity_log.setChecked(bool(self.settings.get("activity_logging_enabled", True)))
        self.chk_activity_log.setStyleSheet("color: #f0f6fc; font-weight: bold;")
        s_layout.addWidget(self.chk_activity_log)

        info_sec = QLabel(
            "🛡️ <b>Touchless Biometrics:</b><br>"
            "AirOS supports interactive biometric fingerprint verification via touch, mouse hold, or "
            "mid-air hand hover over the on-screen sensor."
        )
        info_sec.setWordWrap(True)
        info_sec.setStyleSheet("color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 12px; border: 1px solid #38bdf8; border-radius: 8px;")
        s_layout.addWidget(info_sec)

        s_layout.addStretch()
        tabs.addTab(tab_sec, "Accounts & Security")

        layout.addWidget(tabs)

        # Save confirmation bar
        save_bar = QHBoxLayout()
        save_bar.addStretch()
        btn_apply = QPushButton("Save & Apply All Settings")
        btn_apply.setStyleSheet("background-color: #f59e0b; color: black; padding: 8px 18px; border-radius: 6px; font-weight: bold;")
        btn_apply.clicked.connect(self._apply_all)
        save_bar.addWidget(btn_apply)
        layout.addLayout(save_bar)

    def _on_theme_change(self, text: str):
        self.settings.set("theme", text)
        self.settings_updated.emit()

    def _on_intent_toggled(self, val: bool):
        self.settings.set("intent_lock_enabled", val)
        self.settings_updated.emit()

    def _on_native_toggled(self, val: bool):
        self.settings.set("native_input_enabled", val)
        self.settings_updated.emit()

    def _on_large_toggled(self, val: bool):
        self.settings.set("large_target_mode", val)
        self.settings_updated.emit()

    def _on_privacy_toggled(self, val: bool):
        self.settings.set("privacy_mode", val)
        self.settings_updated.emit()

    def _on_fps_changed(self, index: int):
        val = self.combo_fps.currentData()
        if val is not None:
            self.settings.set("camera_fps", int(val))
            self.settings_updated.emit()

    def _apply_all(self):
        if hasattr(self, "txt_username"):
            self.settings.set("current_user_name", self.txt_username.text().strip() or "Admin User", save=False)
        if hasattr(self, "txt_pin"):
            self.settings.set("security_pin", self.txt_pin.text().strip() or "1234", save=False)
        if hasattr(self, "chk_require_login"):
            self.settings.set("require_login", self.chk_require_login.isChecked(), save=False)
        if hasattr(self, "chk_activity_log"):
            self.settings.set("activity_logging_enabled", self.chk_activity_log.isChecked(), save=False)
        self.settings.save_settings()
        self.settings.log_user_activity("System", "Updated system and security settings in Settings App")
        self.settings_updated.emit()
        QMessageBox.information(self, "AirOS Settings", "Settings & security preferences updated successfully!")
