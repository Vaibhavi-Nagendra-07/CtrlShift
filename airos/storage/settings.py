"""
AirOS Configuration and Persistence Manager.
Provides JSON settings file and SQLite persistence for activity and preferences.
"""

import os
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

DEFAULT_CONFIG_DIR = Path.home() / ".airos"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "airos.db"

DEFAULT_SETTINGS = {
    # System & Theme
    "theme": "dark_modern",  # "dark_modern", "glass_morphism", "high_contrast"
    "wallpaper": "aurora_deep",
    "sound_effects": True,
    "ui_scale": 1.0,
    
    # Hand Tracking & Vision
    "camera_index": 0,
    "camera_fps": 30,
    "handedness": "right",  # "right", "left", "both"
    "tracking_backend": "auto", # "auto", "dnn", "contour", "mediapipe"
    "privacy_mode": False,   # If True, camera preview is hidden completely
    
    # Gesture & Cursor Control
    "cursor_smoothing": 0.65, # EMA alpha weight for cursor smoothing (0.1 to 0.95)
    "cursor_speed": 1.5,      # Pointer movement multiplier
    "active_area_margin": 0.15, # Margin ratio of camera frame mapped to full screen
    "click_pinch_threshold": 0.045, # Normalized distance between index and thumb tip
    "pinch_cooldown_ms": 320,  # Milliseconds between accepted discrete clicks
    "double_click_window_ms": 420, # Max interval between clicks for double-click
    "scroll_sensitivity": 22.0, # Pixels / units per two-finger vertical delta
    "swipe_velocity_threshold": 0.45, # Velocity threshold for horizontal swipe gesture
    
    # IntentLock & Accessibility
    "intent_lock_enabled": True, # Require stable dwell/pinch before triggering action
    "intent_dwell_ms": 200,      # Milliseconds required to hold pinch before click/drag locks
    "large_target_mode": False,  # Accessibility larger buttons and snap magnetic targets
    "emergency_pause_gesture": "open_palm_timeout", # Resume / pause gesture mode
    "native_input_enabled": False, # Whether gestures also drive real Windows mouse via PyAutoGUI
    "virtual_keyboard_docked": True
}

class SettingsManager:
    """Manages persistent JSON configuration and SQLite activity store."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / "config.json"
        self.db_path = self.config_dir / "airos.db"
        self._settings = dict(DEFAULT_SETTINGS)
        self._load_settings()
        self._init_sqlite()

    def _load_settings(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings.update(data)
            except Exception as e:
                print(f"[AirOS Settings] Failed loading config, using defaults: {e}")
        else:
            self.save_settings()

    def save_settings(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4)
        except Exception as e:
            print(f"[AirOS Settings] Failed saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        self._settings[key] = value
        if save:
            self.save_settings()

    def update(self, new_settings: Dict[str, Any]):
        self._settings.update(new_settings)
        self.save_settings()

    def reset_to_defaults(self):
        self._settings = dict(DEFAULT_SETTINGS)
        self.save_settings()

    def _init_sqlite(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS recent_apps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_id TEXT NOT NULL,
                        app_name TEXT NOT NULL,
                        icon TEXT,
                        last_opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS gesture_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        gesture_name TEXT NOT NULL,
                        confidence REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS app_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] SQLite init error: {e}")

    def log_recent_app(self, app_id: str, app_name: str, icon: str = ""):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM recent_apps WHERE app_id = ?
                """, (app_id,))
                cursor.execute("""
                    INSERT INTO recent_apps (app_id, app_name, icon, last_opened)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (app_id, app_name, icon))
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] Error logging recent app: {e}")

    def get_recent_apps(self, limit: int = 10):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT app_id, app_name, icon, last_opened FROM recent_apps
                    ORDER BY last_opened DESC LIMIT ?
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            print(f"[AirOS Database] Error getting recent apps: {e}")
            return []

    def get_all_notes(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, content, updated_at FROM app_notes ORDER BY updated_at DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"[AirOS Database] Error fetching notes: {e}")
            return []

    def save_note(self, note_id: Optional[int], title: str, content: str) -> int:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if note_id:
                    cursor.execute("""
                        UPDATE app_notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (title, content, note_id))
                    conn.commit()
                    return note_id
                else:
                    cursor.execute("""
                        INSERT INTO app_notes (title, content, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (title, content))
                    conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"[AirOS Database] Error saving note: {e}")
            return -1

    def delete_note(self, note_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM app_notes WHERE id = ?", (note_id,))
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] Error deleting note: {e}")
