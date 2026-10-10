"""
AirOS Webcam Capture Worker Thread.
Runs background OpenCV VideoCapture with robust failure handling and PySide6 signals.
"""

import time
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from airos.vision.tracker import HandTracker
from airos.vision.landmarks import HandDetection

class CameraWorker(QThread):
    """Camera thread handling video acquisition and hand landmark detection."""
    
    # Signals
    frame_ready = Signal(np.ndarray, object) # (raw_bgr_frame, Optional[HandDetection])
    camera_status = Signal(bool, str)        # (is_active, status_message)
    fps_updated = Signal(float)              # (measured_fps)

    def __init__(self, camera_index: int = 0, target_fps: int = 30):
        super().__init__()
        self.camera_index = camera_index
        self.target_fps = target_fps
        self._is_running = True
        self._is_paused = False
        self.tracker = None
        self.last_frame_time = time.time()

    def run(self):
        print(f"[AirOS Camera] Initializing camera index {self.camera_index}...")
        self.tracker = HandTracker()

        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY)
        if not cap.isOpened():
            # Try default backend without DSHOW
            cap = cv2.VideoCapture(self.camera_index)
        
        if not cap.isOpened():
            self.camera_status.emit(False, f"Unable to open camera {self.camera_index}")
            print(f"[AirOS Camera] Error: Camera {self.camera_index} could not be opened.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.camera_status.emit(True, "Camera active")
        frame_interval = 1.0 / max(10, self.target_fps)
        prev_time = time.time()
        fps_counter = 0
        fps_start = time.time()

        while self._is_running:
            start_loop = time.time()
            if self._is_paused:
                time.sleep(0.05)
                continue

            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            # Mirror horizontally for intuitive natural mirror-reflection interaction
            frame = cv2.flip(frame, 1)

            # Perform detection
            detection = self.tracker.detect(frame)

            # Emit frame
            self.frame_ready.emit(frame, detection)

            # Compute and emit FPS
            fps_counter += 1
            now = time.time()
            if now - fps_start >= 1.0:
                fps = fps_counter / (now - fps_start)
                self.fps_updated.emit(fps)
                fps_counter = 0
                fps_start = now

            elapsed = time.time() - start_loop
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)

        cap.release()
        self.camera_status.emit(False, "Camera stopped")

    def pause_tracking(self, paused: bool):
        self._is_paused = paused

    def stop(self):
        self._is_running = False
        self.wait(1500)
