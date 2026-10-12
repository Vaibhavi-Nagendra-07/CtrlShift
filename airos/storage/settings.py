"""
AirOS Configuration and Persistence Manager.
Provides JSON settings file and SQLite persistence for activity and preferences.
"""

import os
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

DEFAULT_CONFIG_DIR = Path.home() / ".airos"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "airos.db"

DEFAULT_SETTINGS = {
    # System & Theme
    "theme": "windows_11_fluent",  # "windows_11_fluent", "windows_11_dark", "vision_spatial", "cosmic_nebula"
    "wallpaper": "win11_bloom",
    "sound_effects": True,
    "ui_scale": 1.0,
    
    # Hand Tracking & Vision
    "camera_index": 0,
    "camera_fps": 90,
    "handedness": "right",  # "right", "left", "both"
    "tracking_backend": "dnn", # "dnn" (OpenCV DNN TFLite, recommended), "mediapipe", "contour"
    "privacy_mode": False,   # If True, camera preview is hidden completely
    
    # Gesture & Cursor Control
    "cursor_smoothing": 0.65, # 1-Euro smoothing weight (0.1 to 0.95)
    "cursor_speed": 1.5,      # Pointer movement multiplier
    "active_area_margin": 0.12, # Margin ratio of camera frame mapped to full screen
    "click_pinch_threshold": 0.065, # Comfortable normalized pinch distance
    "pinch_cooldown_ms": 140,  # Milliseconds cooldown between clicks
    "double_click_window_ms": 420, # Max interval between clicks for double-click
    "scroll_sensitivity": 24.0, # Pixels / units per two-finger vertical delta
    "swipe_velocity_threshold": 0.45, # Velocity threshold for horizontal swipe gesture
    
    # IntentLock & Accessibility
    "intent_lock_enabled": True, # Require stable dwell/pinch before triggering action
    "dwell_click_enabled": True, # Enable dwell hover clicking
    "intent_dwell_ms": 150,      # Milliseconds required to hold pinch before click/drag locks
    "large_target_mode": False,  # Accessibility larger buttons and snap magnetic targets
    "emergency_pause_gesture": "open_palm_timeout", # Resume / pause gesture mode
    "native_input_enabled": False, # Windows Native Mouse & Keyboard bridge (Opt-in)
    "virtual_keyboard_docked": True,

    # User Profile & Biometric Security & Records
    "current_user_name": "Admin User",
    "require_login": False,
    "fingerprint_enabled": True,
    "security_pin": "1234",
    "activity_logging_enabled": True
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

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _init_sqlite(self):
        try:
            with self._db() as conn:
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] SQLite init error: {e}")

    def log_recent_app(self, app_id: str, app_name: str, icon: str = ""):
        try:
            with self._db() as conn:
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
            with self._db() as conn:
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
            with self._db() as conn:
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
            with self._db() as conn:
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
            with self._db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM app_notes WHERE id = ?", (note_id,))
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] Error deleting note: {e}")

    def log_user_activity(self, category: str, action: str, details: str = "", user_name: Optional[str] = None):
        """Records an action or event performed by the user into the persistent database."""
        if not self.get("activity_logging_enabled", True):
            return
        u_name = user_name or self.get("current_user_name", "Admin User")
        try:
            with self._db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_activity_records (user_name, category, action, details, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (u_name, category, action, details))
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] Error logging user activity: {e}")

    def get_user_activities(self, limit: int = 200, category: Optional[str] = None, search: Optional[str] = None):
        """Fetches recorded user activities with optional category filter and search query."""
        try:
            with self._db() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = "SELECT id, user_name, category, action, details, timestamp FROM user_activity_records"
                params = []
                clauses = []
                if category and category.lower() != "all":
                    clauses.append("category = ?")
                    params.append(category)
                if search and search.strip():
                    clauses.append("(action LIKE ? OR details LIKE ? OR user_name LIKE ?)")
                    term = f"%{search.strip()}%"
                    params.extend([term, term, term])

                if clauses:
                    query += " WHERE " + " AND ".join(clauses)

                query += " ORDER BY id DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            print(f"[AirOS Database] Error fetching user activities: {e}")
            return []

    def get_activity_stats(self) -> Dict[str, Any]:
        """Calculates summary statistics of recorded user interactions."""
        try:
            with self._db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_activity_records")
                total_count = cursor.fetchone()[0]

                cursor.execute("SELECT category, COUNT(*) FROM user_activity_records GROUP BY category ORDER BY COUNT(*) DESC")
                by_category = dict(cursor.fetchall())

                cursor.execute("SELECT action, COUNT(*) FROM user_activity_records WHERE category = 'App' GROUP BY action ORDER BY COUNT(*) DESC LIMIT 5")
                top_apps = cursor.fetchall()

                cursor.execute("SELECT action, COUNT(*) FROM user_activity_records WHERE category = 'Gesture' GROUP BY action ORDER BY COUNT(*) DESC LIMIT 5")
                top_gestures = cursor.fetchall()

                return {
                    "total_actions": total_count,
                    "by_category": by_category,
                    "top_apps": top_apps,
                    "top_gestures": top_gestures
                }
        except Exception as e:
            print(f"[AirOS Database] Error getting activity stats: {e}")
            return {"total_actions": 0, "by_category": {}, "top_apps": [], "top_gestures": []}

    def clear_user_activities(self):
        """Clears all recorded user activities."""
        try:
            with self._db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_activity_records")
                conn.commit()
        except Exception as e:
            print(f"[AirOS Database] Error clearing user activities: {e}")

    def export_activities_json(self, target_path: Optional[str] = None) -> str:
        """Exports user records to a formatted JSON file."""
        records = self.get_user_activities(limit=5000)
        out_path = Path(target_path) if target_path else self.config_dir / "user_activity_export.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=4)
            return str(out_path)
        except Exception as e:
            print(f"[AirOS Database] Error exporting activities: {e}")
            return ""
