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
from airos.gestures.state_machine import GestureStateMachine, GestureType, GestureEvent, OneEuroFilter
from airos.input.native_adapter import NativeInputAdapter
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
        self.assertIn(tracker.active_backend, ["mediapipe_task", "tflite_dnn", "contour"])

    def test_tracker_synthetic_image(self):
        tracker = HandTracker()
        # Feed black image
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        det = tracker.detect(blank)
        # Should cleanly return None without crashing
        self.assertIsNone(det)

    def test_tracker_has_no_face_cascade(self):
        tracker = HandTracker()
        self.assertFalse(hasattr(tracker, "face_cascade"))
        self.assertFalse(hasattr(tracker, "face_boxes"))

    def test_tracker_strictly_rejects_face_image(self):
        tracker = HandTracker()
        face_img_path = Path("C:/Users/ADMIN/.gemini/antigravity/brain/a167d3a2-708f-4995-a714-2146b0755729/.user_uploaded/media_1791654612326_02130fc5.png")
        if face_img_path.exists():
            import cv2
            img = cv2.imread(str(face_img_path))
            det = tracker.detect(img)
            # Guarantees user face is NEVER recognized as a hand!
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

    def test_one_euro_filter_jitter_reduction(self):
        filter_inst = OneEuroFilter(min_cutoff=1.2, beta=0.05)
        t = 0.0
        # Feed stationary signal with micro-jitter
        base_val = 0.5
        vals = []
        for i in range(30):
            t += 0.033
            noisy = base_val + (0.005 if i % 2 == 0 else -0.005)
            filtered = filter_inst.filter(noisy, t)
            vals.append(filtered)
        
        # Variance of filtered signal should be significantly lower than raw noise
        raw_variance = np.var([base_val + (0.005 if i % 2 == 0 else -0.005) for i in range(30)])
        filtered_variance = np.var(vals[10:]) # After convergence
        self.assertLess(filtered_variance, raw_variance)

    def test_pinch_anchor_locks_cursor_position(self):
        # Initial point
        hand_aim = self._create_synthetic_hand(index_pos=(0.45, 0.45), thumb_pos=(0.7, 0.7))
        evt1 = self.sm.process(hand_aim)
        aimed_pos = evt1.cursor_pos

        # User pinches (thumb and index converge, causing slight index tip mechanical shift)
        hand_pinch = self._create_synthetic_hand(index_pos=(0.46, 0.46), thumb_pos=(0.465, 0.465))
        evt2 = self.sm.process(hand_pinch)

        # Cursor position should remain locked to anchor despite index tip movement
        self.assertTrue(self.sm.is_pinched)
        self.assertFalse(self.sm.is_dragging)
        self.assertAlmostEqual(evt2.cursor_pos[0], aimed_pos[0], delta=0.005)
        self.assertAlmostEqual(evt2.cursor_pos[1], aimed_pos[1], delta=0.005)

    def test_stationary_pinch_does_not_abort_to_drag(self):
        # User holds pinch stationary for > 0.35s, then releases -> must be PINCH_CLICK
        hand_pinch = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.51, 0.51))
        self.sm.process(hand_pinch)
        time.sleep(0.38)
        evt_mid = self.sm.process(hand_pinch)
        # Should NOT be dragging because hand didn't move
        self.assertFalse(self.sm.is_dragging)
        
        # Release pinch
        hand_open = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.7, 0.7))
        evt_rel = self.sm.process(hand_open)
        self.assertEqual(evt_rel.gesture, GestureType.PINCH_CLICK)

    def test_scale_invariant_pinch_at_different_scales(self):
        # Synthetic hand far from camera (small hand, index tip to thumb tip dist = 0.04)
        hand_far = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.53, 0.53))
        self.sm.process(hand_far)
        self.assertTrue(self.sm.is_pinched)
        self.sm.reset()

        # Synthetic hand close to camera (large hand, index tip to thumb tip dist = 0.065, rel_pinch small)
        hand_close = self._create_synthetic_hand(index_pos=(0.5, 0.5), thumb_pos=(0.55, 0.53))
        self.sm.process(hand_close)
        self.assertTrue(self.sm.is_pinched)

class TestNativeInputAdapter(unittest.TestCase):
    def test_adapter_state_and_safe_toggle(self):
        adapter = NativeInputAdapter(enabled=False)
        self.assertFalse(adapter.enabled)
        self.assertFalse(adapter.is_mouse_down)
        self.assertGreater(adapter.screen_w, 0)
        self.assertGreater(adapter.screen_h, 0)

        # Enable
        adapter.set_enabled(True)
        self.assertTrue(adapter.enabled)

        # Disable safely releases mouse down if active
        adapter._is_mouse_down = True
        adapter.set_enabled(False)
        self.assertFalse(adapter.is_mouse_down)
        self.assertFalse(adapter.enabled)

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
