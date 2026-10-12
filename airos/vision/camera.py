"""
AirOS Ultra-High Refresh (90 FPS) Webcam Capture & Motion Engine.
Runs decoupled high-speed frame acquisition, asynchronous landmark detection,
and 90 FPS optical keypoint kinematics with microsecond Windows multimedia timer precision.
"""

import time
import threading
import ctypes
from typing import Optional, List, Tuple
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from airos.vision.tracker import HandTracker
from airos.vision.landmarks import HandDetection, Point3D


class _FrameGrabber(threading.Thread):
    """Dedicated background thread to continuously pull frames from hardware with zero buffer lag."""

    def __init__(self, cap: cv2.VideoCapture):
        super().__init__(daemon=True)
        self.cap = cap
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_id: int = 0
        self.running: bool = True
        self.lock = threading.Lock()

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                # Mirror horizontally for natural mirror-reflection interaction
                mirrored = cv2.flip(frame, 1)
                with self.lock:
                    self.latest_frame = mirrored
                    self.frame_id += 1
            else:
                time.sleep(0.005)

    def get_latest_frame(self) -> Tuple[Optional[np.ndarray], int]:
        with self.lock:
            return self.latest_frame, self.frame_id

    def stop(self):
        self.running = False


class _AsyncHandDetector(threading.Thread):
    """Background worker running ML landmark inference without stalling 90 FPS rendering."""

    def __init__(self, tracker: HandTracker):
        super().__init__(daemon=True)
        self.tracker = tracker
        self.pending_frame: Optional[np.ndarray] = None
        self.new_frame_event = threading.Event()
        self.latest_detection: Optional[HandDetection] = None
        self.is_fresh: bool = False
        self.running: bool = True
        self.lock = threading.Lock()

    def submit_frame(self, frame: np.ndarray):
        with self.lock:
            # Overwrite with newest frame (drop-to-latest pattern)
            self.pending_frame = frame.copy()
            self.new_frame_event.set()

    def run(self):
        while self.running:
            self.new_frame_event.wait(0.04)
            if not self.running:
                break

            frame_to_process = None
            with self.lock:
                if self.pending_frame is not None:
                    frame_to_process = self.pending_frame
                    self.pending_frame = None
                self.new_frame_event.clear()

            if frame_to_process is not None:
                detection = self.tracker.detect(frame_to_process)
                with self.lock:
                    self.latest_detection = detection
                    self.is_fresh = True

    def get_detection(self) -> Tuple[Optional[HandDetection], bool]:
        with self.lock:
            fresh = self.is_fresh
            self.is_fresh = False
            return self.latest_detection, fresh

    def stop(self):
        self.running = False
        self.new_frame_event.set()


class CameraWorker(QThread):
    """
    High-refresh 90 FPS camera thread handling zero-latency frame acquisition,
    LK optical keypoint motion synthesis, and ultra-smooth gesture dispatch.
    """

    # Signals
    frame_ready = Signal(np.ndarray, object) # (raw_bgr_frame, Optional[HandDetection])
    camera_status = Signal(bool, str)        # (is_active, status_message)
    fps_updated = Signal(float)              # (measured_fps)

    def __init__(self, camera_index: int = 0, target_fps: int = 90, backend: str = "auto"):
        super().__init__()
        self.camera_index = camera_index
        self.target_fps = max(30, int(target_fps))
        self.backend = backend
        self._is_running = True
        self._is_paused = False
        self.tracker: Optional[HandTracker] = None

        # Tracking state
        self.current_landmarks: Optional[List[Point3D]] = None
        self.landmark_velocities: Optional[List[Tuple[float, float, float]]] = None
        self.prev_gray: Optional[np.ndarray] = None
        self.handedness: str = "right"
        self.confidence: float = 0.0
        self.frames_without_detection: int = 0

    def run(self):
        print(f"[AirOS Camera] Initializing camera index {self.camera_index} at {self.target_fps} FPS target...")

        # Enable 1ms multimedia timer on Windows for rock-solid 90 FPS timing
        has_winmm = False
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
            has_winmm = True
        except Exception:
            pass

        self.tracker = HandTracker(backend=self.backend)

        # Open camera with DirectShow backend for lowest latency and high refresh rates on Windows
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else cv2.CAP_ANY)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            self.camera_status.emit(False, f"Unable to open camera {self.camera_index}")
            print(f"[AirOS Camera] Error: Camera {self.camera_index} could not be opened.")
            if has_winmm:
                try:
                    ctypes.windll.winmm.timeEndPeriod(1)
                except Exception:
                    pass
            return

        # Optimize DirectShow: MJPG uncompressed streaming unlocks 60-90 FPS on modern webcams
        try:
            if hasattr(cv2, "CAP_PROP_FOURCC") and hasattr(cv2, "VideoWriter_fourcc"):
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.camera_status.emit(True, f"Camera active ({self.target_fps} FPS Motion Engine)")

        grabber = _FrameGrabber(cap)
        grabber.start()

        detector = _AsyncHandDetector(self.tracker)
        detector.start()

        # Wait briefly for initial frame
        for _ in range(50):
            initial_frame, _ = grabber.get_latest_frame()
            if initial_frame is not None:
                detector.submit_frame(initial_frame)
                break
            time.sleep(0.01)

        target_interval = 1.0 / self.target_fps
        next_tick = time.perf_counter()
        fps_counter = 0
        fps_start = time.time()
        last_submitted_id = -1

        while self._is_running:
            next_tick += target_interval
            now = time.time()

            if self._is_paused:
                time.sleep(0.05)
                next_tick = time.perf_counter()
                continue

            frame, frame_id = grabber.get_latest_frame()
            if frame is None:
                time.sleep(0.005)
                continue

            # Submit newest frame to ML detector if we received a fresh camera capture
            if frame_id != last_submitted_id:
                detector.submit_frame(frame)
                last_submitted_id = frame_id

            # 1. Check for fresh ML detection result
            det, fresh_det = detector.get_detection()
            if fresh_det:
                if det is not None and det.is_valid and det.is_anatomical_hand and det.confidence >= 0.50:
                    self.frames_without_detection = 0
                    if self.current_landmarks is None:
                        # Initial acquisition: direct assignment
                        self.current_landmarks = [Point3D(x=p.x, y=p.y, z=p.z) for p in det.landmarks]
                        self.landmark_velocities = [(0.0, 0.0, 0.0) for _ in range(21)]
                    else:
                        # Smooth fusion (60% fresh detection, 40% current position to eliminate snap)
                        alpha = 0.60
                        dt = target_interval
                        fused_lms = []
                        fused_vels = []
                        for old_p, new_p in zip(self.current_landmarks, det.landmarks):
                            fx = float(np.clip(old_p.x * (1.0 - alpha) + new_p.x * alpha, 0.0, 1.0))
                            fy = float(np.clip(old_p.y * (1.0 - alpha) + new_p.y * alpha, 0.0, 1.0))
                            fz = float(old_p.z * (1.0 - alpha) + new_p.z * alpha)
                            vx = (fx - old_p.x) / dt
                            vy = (fy - old_p.y) / dt
                            fused_lms.append(Point3D(x=fx, y=fy, z=fz))
                            fused_vels.append((vx, vy, 0.0))
                        self.current_landmarks = fused_lms
                        self.landmark_velocities = fused_vels

                    self.handedness = det.handedness
                    self.confidence = det.confidence
                else:
                    self.frames_without_detection += 1
                    # Fast extinction: drop tracking after 2 detector cycles with no valid hand (~120ms)
                    if self.frames_without_detection >= 2:
                        self.current_landmarks = None
                        self.landmark_velocities = None
                        self.confidence = 0.0

            # 2. 90 FPS Landmark motion synthesis & optical tracking
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = frame.shape[:2]

            if self.current_landmarks is not None and self.prev_gray is not None and not fresh_det:
                # Perform fast sub-millisecond Lucas-Kanade optical tracking on 21 landmarks
                try:
                    prev_pts = np.array([[[p.x * w, p.y * h]] for p in self.current_landmarks], dtype=np.float32)
                    next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                        self.prev_gray, curr_gray, prev_pts, None,
                        winSize=(15, 15), maxLevel=2,
                        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 8, 0.03)
                    )
                    tracked_count = int(np.sum(status)) if status is not None else 0
                    if tracked_count >= 15:
                        updated_lms = []
                        updated_vels = []
                        dt = target_interval
                        for i in range(21):
                            if status[i][0] == 1:
                                nx = float(np.clip(next_pts[i][0][0] / w, 0.0, 1.0))
                                ny = float(np.clip(next_pts[i][0][1] / h, 0.0, 1.0))
                                nz = self.current_landmarks[i].z
                                vx = (nx - self.current_landmarks[i].x) / dt
                                vy = (ny - self.current_landmarks[i].y) / dt
                                updated_lms.append(Point3D(x=nx, y=ny, z=nz))
                                updated_vels.append((vx, vy, 0.0))
                            else:
                                # Extrapolate occluded keypoint using previous velocity with damping
                                old_p = self.current_landmarks[i]
                                vx, vy, vz = self.landmark_velocities[i] if self.landmark_velocities else (0.0, 0.0, 0.0)
                                nx = float(np.clip(old_p.x + vx * dt * 0.85, 0.0, 1.0))
                                ny = float(np.clip(old_p.y + vy * dt * 0.85, 0.0, 1.0))
                                updated_lms.append(Point3D(x=nx, y=ny, z=old_p.z))
                                updated_vels.append((vx * 0.85, vy * 0.85, 0.0))
                        
                        # Validate continuous anatomical consistency during optical tracking
                        temp_det = HandDetection(landmarks=updated_lms)
                        if temp_det.is_anatomical_hand:
                            self.current_landmarks = updated_lms
                            self.landmark_velocities = updated_vels
                        else:
                            # Optical flow warped the points into a non-hand shape: extinguish
                            self.current_landmarks = None
                            self.landmark_velocities = None
                            self.confidence = 0.0
                    else:
                        # Lost keypoints: extinguish immediately to prevent ghost drift
                        self.current_landmarks = None
                        self.landmark_velocities = None
                        self.confidence = 0.0
                except Exception:
                    pass

            self.prev_gray = curr_gray

            # Construct finalized HandDetection object
            final_detection: Optional[HandDetection] = None
            if self.current_landmarks is not None and len(self.current_landmarks) == 21:
                cand_det = HandDetection(
                    landmarks=self.current_landmarks,
                    handedness=self.handedness,
                    confidence=self.confidence
                )
                if cand_det.is_anatomical_hand and cand_det.confidence >= 0.50:
                    xs = [p.x for p in self.current_landmarks]
                    ys = [p.y for p in self.current_landmarks]
                    x_min = max(0.0, min(xs) - 0.035)
                    y_min = max(0.0, min(ys) - 0.035)
                    x_max = min(1.0, max(xs) + 0.035)
                    y_max = min(1.0, max(ys) + 0.035)

                    final_detection = HandDetection(
                        landmarks=list(self.current_landmarks),
                        handedness=self.handedness,
                        confidence=self.confidence,
                        bounding_box=(x_min, y_min, x_max - x_min, y_max - y_min),
                        backend="hybrid_90fps"
                    )
                else:
                    self.current_landmarks = None
                    self.landmark_velocities = None
                    self.confidence = 0.0

            # Emit frame & detection at steady 90 FPS
            self.frame_ready.emit(frame, final_detection)

            # Compute and emit FPS statistics
            fps_counter += 1
            if now - fps_start >= 1.0:
                fps = fps_counter / (now - fps_start)
                self.fps_updated.emit(fps)
                fps_counter = 0
                fps_start = now

            # Hybrid precision sleep to hit exactly 90.0 FPS
            while time.perf_counter() < next_tick:
                rem = next_tick - time.perf_counter()
                if rem > 0.002:
                    time.sleep(rem - 0.001)

        # Teardown
        grabber.stop()
        detector.stop()
        cap.release()
        if has_winmm:
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        self.camera_status.emit(False, "Camera stopped")

    def pause_tracking(self, paused: bool):
        self._is_paused = paused

    def stop(self):
        self._is_running = False
        self.wait(1500)
