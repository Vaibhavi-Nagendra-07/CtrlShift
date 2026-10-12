"""
Unit and Integration Tests for AirOS User Activity Records and Biometric Fingerprint Login.
"""

import sys
import unittest
import tempfile
import json
from pathlib import Path

from PySide6.QtWidgets import QApplication
from airos.storage.settings import SettingsManager
from airos.apps.user_records_app import UserRecordsApp
from airos.desktop.login_overlay import BiometricLoginOverlay, FingerprintSensorWidget
from airos.voice.voice_engine import VoiceCommandParser


app = QApplication.instance() or QApplication(sys.argv)


class TestUserActivityRecords(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = SettingsManager(config_dir=Path(self.temp_dir.name))

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_log_and_fetch_activity(self):
        self.settings.log_user_activity("App", "Opened File Explorer", "id=files")
        self.settings.log_user_activity("Gesture", "Pinch Click", "at (100, 200)")
        self.settings.log_user_activity("Auth", "Fingerprint Scan Success", "method=fp")

        records = self.settings.get_user_activities(limit=10)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["category"], "Auth")
        self.assertEqual(records[1]["category"], "Gesture")
        self.assertEqual(records[2]["category"], "App")

    def test_category_and_search_filter(self):
        self.settings.log_user_activity("App", "Opened Calculator", "id=calc")
        self.settings.log_user_activity("App", "Opened Browser", "id=browser")
        self.settings.log_user_activity("Voice", "Voice: Screen locked", "id=lock")

        app_records = self.settings.get_user_activities(category="App")
        self.assertEqual(len(app_records), 2)

        voice_records = self.settings.get_user_activities(category="Voice")
        self.assertEqual(len(voice_records), 1)

        search_records = self.settings.get_user_activities(search="Calculator")
        self.assertEqual(len(search_records), 1)
        self.assertEqual(search_records[0]["action"], "Opened Calculator")

    def test_activity_stats(self):
        self.settings.log_user_activity("App", "Opened Notes", "id=notes")
        self.settings.log_user_activity("App", "Opened Notes", "id=notes")
        self.settings.log_user_activity("Gesture", "Pinch Click")

        stats = self.settings.get_activity_stats()
        self.assertEqual(stats["total_actions"], 3)
        self.assertEqual(stats["by_category"].get("App"), 2)
        self.assertEqual(stats["by_category"].get("Gesture"), 1)

    def test_export_and_clear_records(self):
        self.settings.log_user_activity("System", "Theme Changed", "theme=dark")
        export_file = self.settings.export_activities_json()
        self.assertTrue(Path(export_file).exists())

        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertGreaterEqual(len(data), 1)

        self.settings.clear_user_activities()
        records_after = self.settings.get_user_activities()
        self.assertEqual(len(records_after), 0)


class TestUserRecordsAppUI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = SettingsManager(config_dir=Path(self.temp_dir.name))
        self.records_app = UserRecordsApp(settings_mgr=self.settings)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_records_app_initialization(self):
        self.assertIsNotNone(self.records_app)
        self.assertEqual(self.records_app.table.columnCount(), 5)
        self.assertIsNotNone(self.records_app.card_total)
        self.assertIsNotNone(self.records_app.card_gestures)

    def test_records_app_refresh(self):
        self.settings.log_user_activity("App", "Launched Music", "id=music")
        self.records_app._refresh_records()
        self.assertEqual(self.records_app.table.rowCount(), 1)
        self.assertEqual(self.records_app.card_total.val_lbl.text(), "1")


class TestBiometricFingerprintLogin(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings = SettingsManager(config_dir=Path(self.temp_dir.name))
        self.overlay = BiometricLoginOverlay(settings_mgr=self.settings)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_sensor_scan_trigger(self):
        sensor = FingerprintSensorWidget()
        sensor.start_scan()
        self.assertTrue(sensor.is_scanning)
        self.assertEqual(sensor.scan_state, "scanning")

        sensor.cancel_scan()
        self.assertFalse(sensor.is_scanning)
        self.assertEqual(sensor.scan_state, "idle")

    def test_login_overlay_lock_unlock(self):
        self.overlay.lock()
        self.assertTrue(self.overlay.is_locked)
        self.assertTrue(self.overlay.isVisible())

        unlocked_user = []
        self.overlay.unlocked.connect(lambda u: unlocked_user.append(u))

        # Test fingerprint success path
        self.overlay._on_fingerprint_success(True)
        # Verify activity was logged in DB
        records = self.settings.get_user_activities(category="Auth")
        self.assertTrue(any("Fingerprint Biometrics" in r["action"] for r in records))

    def test_pin_verification(self):
        self.overlay.lock()
        self.settings.set("security_pin", "4321")

        # Wrong PIN
        self.overlay.pin_input.setText("9999")
        self.overlay._verify_pin()
        self.assertTrue(self.overlay.is_locked)

        # Correct PIN
        self.overlay.pin_input.setText("4321")
        self.overlay._verify_pin()
        self.assertFalse(self.overlay.is_locked)
        records = self.settings.get_user_activities(category="Auth")
        self.assertTrue(any("PIN Code" in r["action"] for r in records))


class TestVoiceCommandsForNewFeatures(unittest.TestCase):
    def test_records_voice_command(self):
        cmd = VoiceCommandParser.parse("open user records")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd.params.get("app_id"), "records")

        cmd2 = VoiceCommandParser.parse("activity log")
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd2.params.get("app_id"), "records")

    def test_lock_screen_voice_command(self):
        cmd = VoiceCommandParser.parse("lock screen")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_LOCK_SCREEN")

        cmd2 = VoiceCommandParser.parse("lock computer")
        self.assertIsNotNone(cmd2)
        self.assertEqual(cmd2.command_id, "CMD_LOCK_SCREEN")


if __name__ == "__main__":
    unittest.main()
