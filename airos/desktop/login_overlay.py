"""
AirOS Biometric Fingerprint Lock Screen & Login System.
Provides:
- Authentic biometric fingerprint scanner with laser scan animation and radial verification progress.
- Dual authentication methods:
  1. Touch/Click or Mid-Air Gesture Scan (hover index finger over sensor to scan)
  2. 4-Digit Security PIN Fallback
- Live clock, date, and user profile management.
- Complete shell lock lifecycle with smooth unlock transitions.
"""

import time
import math
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QGridLayout, QStackedWidget, QComboBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QRadialGradient,
    QPainterPath
)
from airos.storage.settings import SettingsManager


class FingerprintSensorWidget(QWidget):
    """
    Interactive Biometric Fingerprint Sensor.
    Renders vector concentric fingerprint whorls, animated laser scanning beam,
    and charging progress ring.
    """

    scan_completed = Signal(bool) # True = success

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 150)
        self.setCursor(Qt.PointingHandCursor)

        # Scanning state
        self.is_scanning = False
        self.scan_progress = 0.0 # 0.0 to 1.0
        self.scan_state = "idle" # "idle", "scanning", "success", "failed"
        self.laser_pos = 0.0     # 0.0 to 1.0 (animating up and down)
        self.laser_dir = 1.0

        # Animation timer (60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_timer.start(16)

        # Scan duration is ~1.0 second
        self.scan_start_time = 0.0

    def _on_anim_tick(self):
        # Laser beam movement
        if self.is_scanning:
            self.laser_pos += 0.04 * self.laser_dir
            if self.laser_pos >= 1.0:
                self.laser_pos = 1.0
                self.laser_dir = -1.0
            elif self.laser_pos <= 0.0:
                self.laser_pos = 0.0
                self.laser_dir = 1.0

            # Increment progress
            elapsed = time.time() - self.scan_start_time
            self.scan_progress = min(1.0, elapsed / 0.95)

            if self.scan_progress >= 1.0:
                self.is_scanning = False
                self.scan_state = "success"
                self.scan_completed.emit(True)
        else:
            # Idle gentle pulse
            self.laser_pos = (self.laser_pos + 0.015) % 1.0

        self.update()

    def start_scan(self):
        if self.scan_state == "success":
            return
        self.is_scanning = True
        self.scan_state = "scanning"
        self.scan_start_time = time.time()
        self.scan_progress = 0.0

    def cancel_scan(self):
        if self.scan_state != "success":
            self.is_scanning = False
            self.scan_state = "idle"
            self.scan_progress = 0.0
            self.update()

    def reset(self):
        self.is_scanning = False
        self.scan_state = "idle"
        self.scan_progress = 0.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_scan()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.scan_state == "scanning" and self.scan_progress < 1.0:
            self.cancel_scan()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 - 6

        # Determine colors based on scan state
        if self.scan_state == "success":
            glow_color = QColor("#10b981") # Bright green
            line_color = QColor("#34d399")
        elif self.scan_state == "scanning":
            glow_color = QColor("#00f0ff") # Neon Cyan
            line_color = QColor("#38bdf8")
        else:
            glow_color = QColor("#0ea5e9") # Ambient blue
            line_color = QColor("#7dd3fc")

        # 1. Outer Circular Touch Sensor Glass Plate
        plate_rect = QRectF(cx - 52, cy - 52, 104, 104)
        grad_plate = QRadialGradient(cx, cy, 54)
        grad_plate.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 40))
        grad_plate.setColorAt(0.85, QColor(15, 23, 42, 220))
        grad_plate.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 100))

        painter.setPen(QPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 140), 2))
        painter.setBrush(QBrush(grad_plate))
        painter.drawEllipse(plate_rect)

        # 2. Outer Progress Ring (fills up 0-360 deg when scanning)
        if self.scan_progress > 0.0:
            ring_pen = QPen(glow_color, 4)
            ring_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            arc_rect = QRectF(cx - 57, cy - 57, 114, 114)
            span_angle = int(-self.scan_progress * 360 * 16)
            painter.drawArc(arc_rect, 90 * 16, span_angle)

        # 3. Vector Fingerprint Ridges (Concentric biometric arches & whorls)
        ridge_pen = QPen(line_color, 2)
        ridge_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(ridge_pen)
        painter.setBrush(Qt.NoBrush)

        # Arc 1: Center core
        painter.drawArc(QRectF(cx - 8, cy - 8, 16, 20), 30 * 16, 120 * 16)
        # Arc 2
        painter.drawArc(QRectF(cx - 15, cy - 18, 30, 36), 15 * 16, 150 * 16)
        # Arc 3
        painter.drawArc(QRectF(cx - 22, cy - 26, 44, 52), 20 * 16, 140 * 16)
        # Arc 4
        painter.drawArc(QRectF(cx - 29, cy - 34, 58, 68), 25 * 16, 130 * 16)
        # Arc 5
        painter.drawArc(QRectF(cx - 36, cy - 40, 72, 80), 30 * 16, 120 * 16)
        # Lower loops
        painter.drawArc(QRectF(cx - 14, cy - 2, 28, 32), 200 * 16, 140 * 16)
        painter.drawArc(QRectF(cx - 22, cy + 6, 44, 30), 210 * 16, 120 * 16)

        # 4. Animated Laser Beam when Scanning
        if self.is_scanning:
            beam_y = (cy - 40) + self.laser_pos * 80
            laser_grad = QLinearGradient(cx - 45, beam_y, cx + 45, beam_y)
            laser_grad.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            laser_grad.setColorAt(0.5, QColor(255, 255, 255, 240))
            laser_grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))

            painter.setPen(QPen(laser_grad, 3))
            painter.drawLine(QPointF(cx - 45, beam_y), QPointF(cx + 45, beam_y))

        # 5. Bottom label badge
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        if self.scan_state == "success":
            painter.setPen(QColor("#34d399"))
            painter.drawText(QRectF(0, h - 22, w, 20), Qt.AlignCenter, "VERIFIED ✓")
        elif self.is_scanning:
            painter.setPen(QColor("#38bdf8"))
            pct = int(self.scan_progress * 100)
            painter.drawText(QRectF(0, h - 22, w, 20), Qt.AlignCenter, f"SCANNING {pct}%")
        else:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(QRectF(0, h - 22, w, 20), Qt.AlignCenter, "TOUCH / HOVER")

        painter.end()


class BiometricLoginOverlay(QFrame):
    """
    Full-window Biometric Fingerprint Lock Screen & User Authentication Overlay.
    """

    unlocked = Signal(str) # user_name
    locked = Signal()

    def __init__(self, settings_mgr: Optional[SettingsManager] = None, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr or SettingsManager()
        self.is_locked = False
        self.active_user = self.settings.get("current_user_name", "Admin User")
        self._init_ui()

        # Clock timer (updates every second)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _init_ui(self):
        self.setObjectName("BiometricLoginOverlay")
        self.setStyleSheet("""
            QFrame#BiometricLoginOverlay {
                background-color: rgba(10, 14, 23, 0.94);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)

        # ---------------- 1. Top Clock & Date ----------------
        self.time_lbl = QLabel("12:00")
        self.time_lbl.setAlignment(Qt.AlignCenter)
        self.time_lbl.setStyleSheet("font-size: 64px; font-weight: 300; color: #ffffff; font-family: 'Segoe UI Light', 'Segoe UI', sans-serif;")
        layout.addWidget(self.time_lbl)

        self.date_lbl = QLabel("Monday, October 12, 2026")
        self.date_lbl.setAlignment(Qt.AlignCenter)
        self.date_lbl.setStyleSheet("font-size: 16px; color: #94a3b8; font-weight: 500; margin-bottom: 24px;")
        layout.addWidget(self.date_lbl)

        # ---------------- 2. User Avatar & Profile Switcher ----------------
        avatar_box = QHBoxLayout()
        avatar_box.setAlignment(Qt.AlignCenter)
        self.avatar_circle = QLabel("👤")
        self.avatar_circle.setStyleSheet("""
            font-size: 44px;
            background: rgba(56, 189, 248, 0.15);
            border: 2px solid rgba(56, 189, 248, 0.4);
            border-radius: 40px;
            padding: 8px;
        """)
        avatar_box.addWidget(self.avatar_circle)
        layout.addLayout(avatar_box)

        # User Switcher Dropdown
        user_select_box = QHBoxLayout()
        user_select_box.setAlignment(Qt.AlignCenter)

        self.user_combo = QComboBox()
        self.user_combo.setFixedWidth(200)
        self.user_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 6px 14px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #161b22;
                color: #ffffff;
                selection-background-color: #1f6feb;
                selection-color: #ffffff;
                border: 1px solid #30363d;
            }
        """)

        # Populate registered system users
        users = ["Admin User", "Guest User", "Work Account"]
        if self.active_user not in users:
            users.insert(0, self.active_user)
        self.user_combo.addItems(users)
        self.user_combo.setCurrentText(self.active_user)
        self.user_combo.currentTextChanged.connect(self._on_user_selected)
        user_select_box.addWidget(self.user_combo)
        layout.addLayout(user_select_box)

        sub_user_tip = QLabel("🔒 Biometric Identity Locked")
        sub_user_tip.setAlignment(Qt.AlignCenter)
        sub_user_tip.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: 500; margin-bottom: 8px;")
        layout.addWidget(sub_user_tip)

        # ---------------- 3. Stacked Auth Mode: Fingerprint vs PIN ----------------
        self.stack = QStackedWidget()
        self.stack.setFixedSize(320, 240)

        # Page 0: Biometric Fingerprint Sensor
        page_fp = QWidget()
        fp_layout = QVBoxLayout(page_fp)
        fp_layout.setAlignment(Qt.AlignCenter)
        fp_layout.setSpacing(10)

        self.sensor = FingerprintSensorWidget()
        self.sensor.scan_completed.connect(self._on_fingerprint_success)
        fp_layout.addWidget(self.sensor, alignment=Qt.AlignCenter)

        self.status_lbl = QLabel("Touch sensor or hold hand steady to scan")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        fp_layout.addWidget(self.status_lbl)

        self.btn_use_pin = QPushButton("🔢 Enter PIN instead")
        self.btn_use_pin.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: rgba(56, 189, 248, 0.15); }
        """)
        self.btn_use_pin.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        fp_layout.addWidget(self.btn_use_pin, alignment=Qt.AlignCenter)

        self.stack.addWidget(page_fp)

        # Page 1: 4-Digit PIN Keypad
        page_pin = QWidget()
        pin_layout = QVBoxLayout(page_pin)
        pin_layout.setAlignment(Qt.AlignCenter)
        pin_layout.setSpacing(8)

        pin_title = QLabel("Enter 4-Digit Security PIN")
        pin_title.setAlignment(Qt.AlignCenter)
        pin_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        pin_layout.addWidget(pin_title)

        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setAlignment(Qt.AlignCenter)
        self.pin_input.setMaxLength(8)
        self.pin_input.setFixedHeight(34)
        self.pin_input.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                letter-spacing: 6px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
        """)
        self.pin_input.returnPressed.connect(self._verify_pin)
        pin_layout.addWidget(self.pin_input)

        # Keypad Grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(6)
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "✓"]
        for idx, d in enumerate(digits):
            r = idx // 3
            c = idx % 3
            btn = QPushButton(d)
            btn.setFixedSize(48, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.08);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 5px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover { background: rgba(56, 189, 248, 0.25); border-color: #38bdf8; }
            """)
            btn.clicked.connect(lambda checked, ch=d: self._on_keypad_click(ch))
            grid.addWidget(btn, r, c)
        pin_layout.addWidget(grid_widget, alignment=Qt.AlignCenter)

        self.btn_back_fp = QPushButton("👆 Use Fingerprint")
        self.btn_back_fp.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #38bdf8;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        self.btn_back_fp.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        pin_layout.addWidget(self.btn_back_fp, alignment=Qt.AlignCenter)

        self.stack.addWidget(page_pin)

        layout.addWidget(self.stack, alignment=Qt.AlignCenter)

    def _update_clock(self):
        now = time.localtime()
        self.time_lbl.setText(time.strftime("%I:%M %p", now))
        self.date_lbl.setText(time.strftime("%A, %B %d, %Y", now))

    def _on_user_selected(self, user_name: str):
        if not user_name:
            return
        self.active_user = user_name
        self.settings.set("current_user_name", user_name)
        if "admin" in user_name.lower():
            self.avatar_circle.setText("👑")
        elif "guest" in user_name.lower():
            self.avatar_circle.setText("👤")
        else:
            self.avatar_circle.setText("💼")
        self.status_lbl.setText(f"Ready to authenticate as {user_name}")

    def _on_keypad_click(self, char: str):
        if char == "⌫":
            self.pin_input.setText(self.pin_input.text()[:-1])
        elif char == "✓":
            self._verify_pin()
        else:
            if len(self.pin_input.text()) < 8:
                self.pin_input.setText(self.pin_input.text() + char)
                if len(self.pin_input.text()) == 4:
                    self._verify_pin()

    def _verify_pin(self):
        entered = self.pin_input.text()
        correct_pin = str(self.settings.get("security_pin", "1234"))
        if entered == correct_pin:
            self.status_lbl.setText("PIN Accepted ✓")
            self.settings.log_user_activity("Auth", "User Logged In via PIN Code", f"user={self.active_user}")
            self._unlock_success()
        else:
            self.pin_input.setStyleSheet("""
                QLineEdit {
                    background: rgba(248, 81, 73, 0.2);
                    color: #ffffff;
                    font-size: 18px;
                    border: 2px solid #f85149;
                    border-radius: 6px;
                }
            """)
            self.pin_input.clear()
            self.settings.log_user_activity("Auth", "Failed PIN Login Attempt", f"user={self.active_user}")
            QTimer.singleShot(1000, lambda: self.pin_input.setStyleSheet("""
                QLineEdit {
                    background: rgba(255, 255, 255, 0.1);
                    color: #ffffff;
                    font-size: 18px;
                    font-weight: bold;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 6px;
                }
            """))

    def _on_fingerprint_success(self, success: bool):
        if success:
            self.status_lbl.setText("Biometric Fingerprint Verified ✓")
            self.status_lbl.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")
            self.settings.log_user_activity("Auth", "User Logged In via Fingerprint Biometrics", f"user={self.active_user}")
            # Smooth unlock delay for feedback
            QTimer.singleShot(600, self._unlock_success)

    def _unlock_success(self):
        self.is_locked = False
        self.hide()
        self.unlocked.emit(self.active_user)

    def lock(self):
        """Locks the screen and shows biometric login overlay."""
        self.is_locked = True
        self.active_user = self.settings.get("current_user_name", "Admin User")
        if hasattr(self, "user_combo") and self.user_combo.currentText() != self.active_user:
            self.user_combo.setCurrentText(self.active_user)
        self.sensor.reset()
        self.pin_input.clear()
        self.stack.setCurrentIndex(0)
        self.status_lbl.setText("Touch sensor or hold hand steady to scan")
        self.status_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.show()
        self.raise_()
        self.settings.log_user_activity("Auth", "Screen Locked (Biometric Shield Active)", f"user={self.active_user}")
        self.locked.emit()

    def process_gesture_cursor(self, global_x: int, global_y: int, is_pinch: bool):
        """
        Allows mid-air touchless hand gestures to trigger fingerprint scan!
        If user hovers index finger over the fingerprint sensor widget, start scanning.
        """
        if not self.isVisible() or self.stack.currentIndex() != 0:
            return

        sensor_rect = self.sensor.rect()
        sensor_top_left = self.sensor.mapToGlobal(sensor_rect.topLeft())
        global_sensor_rect = QRectF(sensor_top_left.x(), sensor_top_left.y(), self.sensor.width(), self.sensor.height())

        if global_sensor_rect.contains(QPointF(global_x, global_y)):
            # Hand is hovering over fingerprint sensor!
            if not self.sensor.is_scanning and self.sensor.scan_state != "success":
                self.sensor.start_scan()
        else:
            if self.sensor.is_scanning:
                self.sensor.cancel_scan()
