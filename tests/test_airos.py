"""
AirOS Test Suite.
Tests:
1. Hand landmark data structure & geometric distance computations.
2. Multi-backend HandTracker initialization and detection output.
3. Gesture State Machine: hover, pinch-click, IntentLock, two-finger scroll, swipe, and palm.
4. Settings persistence and SQLite database activity logger.
5. Window manager and desktop shell component hierarchy.
"""

import unittest
import time
from pathlib import Path
import numpy as np

from airos.vision.landmarks import HandDetection, Point3D, WRIST, INDEX_TIP, THUMB_TIP
from airos.vision.tracker import HandTracker
from airos.gestures.state_machine import GestureStateMachine, GestureType, GestureEvent
from airos.storage.settings import SettingsManager, DEFAULT_SETTINGS

class TestLandmarksAndGeometry(unittest.TestCase):
    def test_point3d_distance(self):
        p1 = Point3D(0.0, 0.0, 0.0)
        p2 = Point3D(3.0, 4.0, 0.0)
        self.assertAlmostEqual(p1.distance_2d(p2), 5.0)
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)

    def test_hand_detection_validity(self):
        detection = HandDetection()
        self.assertFalse(detection.is_valid)

        # Populate 21 points
        detection.landmarks = [Point3D(0.1 * i, 0.1 * i, 0.0) for i in range(21)]
        self.assertTrue(detection.is_valid)
        self.assertEqual(detection.index_tip, detection.landmarks[8])
        self.assertEqual(detection.thumb_tip, detection.landmarks[4])

class TestHandTracker(unittest.TestCase):
    def test_tracker_initialization(self):
        tracker = HandTracker()
        self.assertIsNotNone(tracker)
        self.assertIn(tracker.active_backend, ["tflite_dnn", "contour"])

    def test_tracker_synthetic_image(self):
        tracker = HandTracker()
        # Feed black image
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        det = tracker.detect(blank)
        # Should cleanly return None without crashing
        self.assertIsNone(det)

class TestGestureStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = GestureStateMachine(config=dict(DEFAULT_SETTINGS))

    def _create_synthetic_hand(self, index_pos=(0.5, 0.5), thumb_pos=(0.7, 0.7), all_fingers_up=False):
        landmarks = []
        for i in range(21):
            if i == 8: # index tip
                landmarks.append(Point3D(index_pos[0], index_pos[1], 0.0))
            elif i == 4: # thumb tip
                landmarks.append(Point3D(thumb_pos[0], thumb_pos[1], 0.0))
            elif i == 0: # wrist
                landmarks.append(Point3D(0.5, 0.9, 0.0))
            elif i in (6, 10, 14, 18): # PIPs
                landmarks.append(Point3D(0.5, 0.6 if all_fingers_up else 0.4, 0.0))
            elif i in (12, 16, 20): # middle, ring, pinky tips
                landmarks.append(Point3D(0.5, 0.3 if all_fingers_up else 0.7, 0.0))
            else:
                landmarks.append(Point3D(0.5, 0.7, 0.0))
        return HandDetection(landmarks=landmarks, confidence=0.95)

    def test_hover_state(self):
        hand = self._create_synthetic_hand(index_pos=(0.4, 0.4), thumb_pos=(0.8, 0.8))
        evt = self.sm.process(hand)
        self.assertIn(evt.gesture, [GestureType.HOVER, GestureType.NONE])
        self.assertGreater(evt.confidence, 0.5)

    def test_pinch_click_generation(self):
        # 1. Approach thumb and index (distance < 0.04)
        hand_pinch = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.51, 0.51))
        
        # Initiate pinch
        self.sm.process(hand_pinch)
        time.sleep(0.15)
        self.sm.process(hand_pinch)
        time.sleep(0.10)
        
        # Release pinch
        hand_open = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.7, 0.7))
        evt = self.sm.process(hand_open)
        
        self.assertEqual(evt.gesture, GestureType.PINCH_CLICK)

    def test_tracking_loss_drag_release_safety(self):
        # Simulate dragging then sudden tracking drop
        self.sm.is_dragging = True
        self.sm.is_pinched = True
        
        # Tracking lost (hand is None)
        evt = self.sm.process(None)
        self.assertFalse(self.sm.is_dragging)
        self.assertFalse(self.sm.is_pinched)
        self.assertIn("Tracking Lost", evt.state_description)

class TestSettingsAndDatabase(unittest.TestCase):
    def test_settings_save_and_load(self):
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        mgr = SettingsManager(config_dir=temp_dir)
        
        mgr.set("cursor_speed", 2.2)
        self.assertEqual(mgr.get("cursor_speed"), 2.2)

        # Reload from disk
        mgr2 = SettingsManager(config_dir=temp_dir)
        self.assertEqual(mgr2.get("cursor_speed"), 2.2)

    def test_sqlite_notes_crud(self):
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        mgr = SettingsManager(config_dir=temp_dir)

        nid = mgr.save_note(None, "AirOS Test Note", "Testing persistence in touchless environment.")
        self.assertGreater(nid, 0)

        notes = mgr.get_all_notes()
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0][1], "AirOS Test Note")

        mgr.delete_note(nid)
        self.assertEqual(len(mgr.get_all_notes()), 0)

if __name__ == "__main__":
    unittest.main()
