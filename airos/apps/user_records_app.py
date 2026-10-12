"""
AirOS User Activity Records & Live Audit Monitor.
Tracks, visualizes, and exports all user interactions:
- Application launches & lifecycle
- Mid-air gestures & interactions
- Voice commands executed
- Biometric fingerprint authentication & security logins
- Real-time live activity feed with search, category filtering, and JSON export.
"""

import time
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QLineEdit, QFrame, QGridLayout,
    QMessageBox, QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from airos.storage.settings import SettingsManager


class MetricCard(QFrame):
    """Sleek metric card showing interaction counts."""
    def __init__(self, title: str, value: str, icon: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(82)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
            }}
            QFrame:hover {{
                background-color: rgba(255, 255, 255, 0.09);
                border: 1px solid {color_hex};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        # Icon box
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 28px; background: transparent;")
        layout.addWidget(icon_lbl)

        # Text container
        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"color: {color_hex}; font-size: 20px; font-weight: 800; background: transparent;")
        t_box.addWidget(self.val_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 500; background: transparent;")
        t_box.addWidget(title_lbl)
        layout.addLayout(t_box)

    def set_value(self, val: str):
        self.val_lbl.setText(val)


class UserRecordsApp(QWidget):
    """Primary User Activity Records Application for AirOS."""

    def __init__(self, settings_mgr: Optional[SettingsManager] = None, parent=None):
        super().__init__(parent)
        self.settings = settings_mgr or SettingsManager()
        self._init_ui()

        # Live auto-refresh timer (polls every 2.5s)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_records)
        self.refresh_timer.start(2500)

        self._refresh_records()

    def _init_ui(self):
        self.setWindowTitle("User Activity Records")
        self.resize(760, 540)
        self.setStyleSheet("background-color: #0f131a; color: #f0f6fc; font-family: 'Segoe UI', sans-serif;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header bar
        header = QHBoxLayout()
        avatar_lbl = QLabel("👤")
        avatar_lbl.setStyleSheet("font-size: 26px; background: rgba(56, 189, 248, 0.15); border-radius: 18px; padding: 4px;")
        header.addWidget(avatar_lbl)

        user_info = QVBoxLayout()
        user_info.setSpacing(1)
        u_name = self.settings.get("current_user_name", "Admin User")
        self.title_lbl = QLabel(f"<b>{u_name}'s Activity Records</b>")
        self.title_lbl.setStyleSheet("font-size: 16px; color: #ffffff;")
        user_info.addWidget(self.title_lbl)

        sub_lbl = QLabel("Real-time logging of applications, mid-air gestures, voice commands & biometric logins")
        sub_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        user_info.addWidget(sub_lbl)
        header.addLayout(user_info)
        header.addStretch()

        # Top action buttons
        self.btn_export = QPushButton("💾 Export JSON")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background: #1f6feb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background: #388bfd; }
        """)
        self.btn_export.clicked.connect(self._export_records)
        header.addWidget(self.btn_export)

        self.btn_clear = QPushButton("🗑️ Clear Log")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background: rgba(248, 81, 73, 0.15);
                color: #f85149;
                border: 1px solid rgba(248, 81, 73, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background: rgba(248, 81, 73, 0.3); }
        """)
        self.btn_clear.clicked.connect(self._clear_records)
        header.addWidget(self.btn_clear)

        main_layout.addLayout(header)

        # ---------------- Metrics Summary Row ----------------
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_total = MetricCard("Total Activities", "0", "📊", "#38bdf8")
        cards_layout.addWidget(self.card_total)

        self.card_gestures = MetricCard("Gestures Performed", "0", "⚡", "#a855f7")
        cards_layout.addWidget(self.card_gestures)

        self.card_apps = MetricCard("Apps Opened", "0", "📁", "#10b981")
        cards_layout.addWidget(self.card_apps)

        self.card_auth = MetricCard("Biometric Logins", "0", "🛡️", "#f59e0b")
        cards_layout.addWidget(self.card_auth)

        main_layout.addLayout(cards_layout)

        # ---------------- Filter & Search Toolbar ----------------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        f_lbl = QLabel("Filter Category:")
        f_lbl.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 500;")
        toolbar.addWidget(f_lbl)

        self.combo_category = QComboBox()
        self.combo_category.addItems(["All", "App", "Gesture", "Voice", "Auth", "System"])
        self.combo_category.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }
        """)
        self.combo_category.currentTextChanged.connect(self._refresh_records)
        toolbar.addWidget(self.combo_category)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search actions or details...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
        """)
        self.search_box.textChanged.connect(self._refresh_records)
        toolbar.addWidget(self.search_box)

        self.chk_live = QCheckBox("Live Auto-Refresh")
        self.chk_live.setChecked(True)
        self.chk_live.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold;")
        self.chk_live.toggled.connect(self._on_live_toggle)
        toolbar.addWidget(self.chk_live)

        main_layout.addLayout(toolbar)

        # ---------------- Activity Records Table ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Timestamp", "Category", "User Action", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(22, 27, 34, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.05);
                color: #c9d1d9;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #8b949e;
                font-weight: 600;
                font-size: 11px;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #30363d;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
            QTableWidget::item:selected {
                background-color: rgba(56, 189, 248, 0.2);
                color: #ffffff;
            }
        """)
        main_layout.addWidget(self.table)

    def _on_live_toggle(self, enabled: bool):
        if enabled:
            self.refresh_timer.start(2500)
        else:
            self.refresh_timer.stop()

    def _refresh_records(self):
        category = self.combo_category.currentText()
        search = self.search_box.text()
        records = self.settings.get_user_activities(limit=150, category=category, search=search)
        stats = self.settings.get_activity_stats()

        # Update metric cards
        self.card_total.set_value(str(stats.get("total_actions", 0)))
        by_cat = stats.get("by_category", {})
        self.card_gestures.set_value(str(by_cat.get("Gesture", 0)))
        self.card_apps.set_value(str(by_cat.get("App", 0)))
        self.card_auth.set_value(str(by_cat.get("Auth", 0)))

        # Update table rows
        self.table.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            # ID
            item_id = QTableWidgetItem(str(r["id"]))
            item_id.setForeground(QColor("#8b949e"))
            self.table.setItem(row_idx, 0, item_id)

            # Timestamp
            ts = r.get("timestamp", "")
            if len(ts) >= 19:
                ts = ts[11:19]  # HH:MM:SS
            item_time = QTableWidgetItem(ts)
            item_time.setForeground(QColor("#79c0ff"))
            self.table.setItem(row_idx, 1, item_time)

            # Category with badge color
            cat = r.get("category", "General")
            item_cat = QTableWidgetItem(f"[{cat}]")
            if cat == "App":
                item_cat.setForeground(QColor("#10b981"))
            elif cat == "Gesture":
                item_cat.setForeground(QColor("#c084fc"))
            elif cat == "Voice":
                item_cat.setForeground(QColor("#38bdf8"))
            elif cat == "Auth":
                item_cat.setForeground(QColor("#f59e0b"))
            elif cat == "System":
                item_cat.setForeground(QColor("#94a3b8"))
            self.table.setItem(row_idx, 2, item_cat)

            # Action
            act = r.get("action", "")
            item_act = QTableWidgetItem(act)
            item_act.setForeground(QColor("#ffffff"))
            self.table.setItem(row_idx, 3, item_act)

            # Details
            det = r.get("details", "")
            item_det = QTableWidgetItem(det)
            item_det.setForeground(QColor("#8b949e"))
            self.table.setItem(row_idx, 4, item_det)

    def _export_records(self):
        default_name = f"airos_user_records_{int(time.time())}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Export Activity Records", default_name, "JSON Files (*.json)")
        if path:
            out_file = self.settings.export_activities_json(path)
            if out_file:
                QMessageBox.information(self, "Export Successful", f"Saved activity records to:\n{out_file}")
            else:
                QMessageBox.warning(self, "Export Failed", "Could not export records.")

    def _clear_records(self):
        reply = QMessageBox.question(
            self, "Clear Records",
            "Are you sure you want to permanently clear all recorded user activities?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings.clear_user_activities()
            self._refresh_records()
