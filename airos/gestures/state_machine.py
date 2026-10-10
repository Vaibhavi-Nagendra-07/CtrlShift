"""
AirOS Refined Natural Gesture State Machine.
Streamlined Gestures:
1. Move Pointer: Point index finger (smooth 1-Euro/EMA adaptive filter).
2. Pinch Click: Pinch index and thumb together (natural pinch gesture, works from lap or air).
3. Hold Pinch & Move: Drag window or item.
4. Two-Finger Scroll: Move two fingers up/down to scroll.
5. Fist / Clench: Close hand to toggle Start Menu / App Launcher.
6. Open Palm: Show Quick Action control center.
"""

import time
import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from airos.vision.landmarks import (
    HandDetection, Point3D,
    WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP, THUMB_IP
)

class GestureType(Enum):
    NONE = auto()
    HOVER = auto()
    PINCH_CLICK = auto()
    DOUBLE_CLICK = auto()
    DRAG = auto()
    SCROLL = auto()
    OPEN_PALM = auto()
    FIST_TOGGLE_MENU = auto()
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()
    TOGGLE_KEYBOARD = auto()

@dataclass
class GestureEvent:
    gesture: GestureType
    cursor_pos: Tuple[float, float]
    raw_point: Tuple[float, float]
    delta: Tuple[float, float] = (0.0, 0.0)
    confidence: float = 0.0
    timestamp: float = 0.0
    state_description: str = ""

class GestureStateMachine:
    """
    Optimized gesture state machine with high-precision motion smoothing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Smooth position state
        self.smoothed_x = 0.5
        self.smoothed_y = 0.5
        self.prev_x = 0.5
        self.prev_y = 0.5
        
        # Pinch / Click state
        self.is_pinched = False
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.is_dragging = False
        
        # Fist / Clench toggle tracking (replaces open palm confusion)
        self.fist_start_time = 0.0
        self.fist_triggered = False

        # Open Palm tracking
        self.palm_open_start = 0.0
        self.palm_triggered = False

        # Scroll state
        self.prev_scroll_y = None
        self.swipe_history = []
        self.last_swipe_time = 0.0

    def reset(self):
        self.is_pinched = False
        self.is_dragging = False
        self.prev_scroll_y = None
        self.swipe_history.clear()

    def process(self, hand: Optional[HandDetection], screen_w: int = 1920, screen_h: int = 1080) -> GestureEvent:
        now = time.time()
        
        if hand is None or not hand.is_valid:
            if self.is_dragging:
                self.is_dragging = False
                self.is_pinched = False
                return GestureEvent(
                    gesture=GestureType.NONE,
                    cursor_pos=(self.smoothed_x, self.smoothed_y),
                    raw_point=(self.smoothed_x, self.smoothed_y),
                    confidence=0.0,
                    timestamp=now,
                    state_description="Tracking Lost (Drag Released)"
                )
            self.reset()
            return GestureEvent(
                gesture=GestureType.NONE,
                cursor_pos=(self.smoothed_x, self.smoothed_y),
                raw_point=(self.smoothed_x, self.smoothed_y),
                confidence=0.0,
                timestamp=now,
                state_description="No Hand Detected"
            )

        # 1. Coordinate normalization and pointer mapping
        margin = float(self.config.get("active_area_margin", 0.12))
        idx_tip = hand.index_tip
        raw_x = idx_tip.x
        raw_y = idx_tip.y

        norm_x = (raw_x - margin) / max(0.01, (1.0 - 2 * margin))
        norm_y = (raw_y - margin) / max(0.01, (1.0 - 2 * margin))
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        dist_moved = math.hypot(norm_x - self.smoothed_x, norm_y - self.smoothed_y)
        if dist_moved > 0.08:
            alpha = 0.40
        elif dist_moved > 0.02:
            alpha = 0.65
        else:
            alpha = 0.85

        self.smoothed_x = alpha * self.smoothed_x + (1.0 - alpha) * norm_x
        self.smoothed_y = alpha * self.smoothed_y + (1.0 - alpha) * norm_y

        dx = self.smoothed_x - self.prev_x
        dy = self.smoothed_y - self.prev_y
        self.prev_x = self.smoothed_x
        self.prev_y = self.smoothed_y

        cursor_coords = (self.smoothed_x, self.smoothed_y)
        raw_coords = (raw_x, raw_y)

        # 2. Finger Extension Status
        index_up = hand.finger_extended(INDEX_TIP, INDEX_PIP)
        middle_up = hand.finger_extended(MIDDLE_TIP, MIDDLE_PIP)
        ring_up = hand.finger_extended(RING_TIP, RING_PIP)
        pinky_up = hand.finger_extended(PINKY_TIP, PINKY_PIP)

        pinch_dist = hand.index_tip.distance_2d(hand.thumb_tip)
        pinch_thresh = float(self.config.get("click_pinch_threshold", 0.055))
        currently_pinching = pinch_dist < pinch_thresh

        # GESTURE: PINCH CLICK & DRAG (Evaluate first so pinch release generates click cleanly)
        intent_dwell_sec = float(self.config.get("intent_dwell_ms", 120)) / 1000.0
        cooldown_sec = float(self.config.get("pinch_cooldown_ms", 260)) / 1000.0
        double_click_window = float(self.config.get("double_click_window_ms", 380)) / 1000.0

        if currently_pinching:
            if not self.is_pinched:
                self.is_pinched = True
                self.pinch_start_time = now
            else:
                pinch_duration = now - self.pinch_start_time
                if pinch_duration > 0.32:
                    self.is_dragging = True
                    return GestureEvent(
                        gesture=GestureType.DRAG,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        delta=(dx, dy),
                        confidence=0.95,
                        timestamp=now,
                        state_description="Pinch Dragging"
                    )
        else:
            if self.is_pinched:
                pinch_duration = now - self.pinch_start_time
                self.is_pinched = False
                
                if self.is_dragging:
                    self.is_dragging = False
                    return GestureEvent(
                        gesture=GestureType.HOVER,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=hand.confidence,
                        timestamp=now,
                        state_description="Drag Released"
                    )

                if (now - self.last_click_time) >= cooldown_sec:
                    if (now - self.last_click_time) <= double_click_window:
                        self.last_click_time = now
                        return GestureEvent(
                            gesture=GestureType.DOUBLE_CLICK,
                            cursor_pos=cursor_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Double Click"
                        )
                    else:
                        self.last_click_time = now
                        return GestureEvent(
                            gesture=GestureType.PINCH_CLICK,
                            cursor_pos=cursor_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Pinch Click"
                        )

        # GESTURE: CLOSED FIST (All fingers curled, not in a pinch) -> Toggle Start Menu
        if not index_up and not middle_up and not ring_up and not pinky_up and not currently_pinching:
            if not self.fist_triggered:
                if self.fist_start_time == 0.0:
                    self.fist_start_time = now
                elif (now - self.fist_start_time) >= 0.4:
                    self.fist_triggered = True
                    return GestureEvent(
                        gesture=GestureType.FIST_TOGGLE_MENU,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=0.96,
                        timestamp=now,
                        state_description="Fist (App Launcher Toggled)"
                    )
            return GestureEvent(
                gesture=GestureType.HOVER,
                cursor_pos=cursor_coords,
                raw_point=raw_coords,
                confidence=0.9,
                timestamp=now,
                state_description="Fist Closed"
            )
        else:
            self.fist_start_time = 0.0
            self.fist_triggered = False

        # GESTURE: TWO-FINGER SCROLL
        if index_up and middle_up and not ring_up and not pinky_up and not currently_pinching:
            separation = hand.index_tip.distance_2d(hand.middle_tip)
            if separation <= 0.06:
                curr_scroll_y = (hand.index_tip.y + hand.middle_tip.y) * 0.5
                scroll_delta = 0.0
                if self.prev_scroll_y is not None:
                    scroll_delta = (self.prev_scroll_y - curr_scroll_y) * float(self.config.get("scroll_sensitivity", 28.0))
                self.prev_scroll_y = curr_scroll_y

                return GestureEvent(
                    gesture=GestureType.SCROLL,
                    cursor_pos=cursor_coords,
                    raw_point=raw_coords,
                    delta=(0.0, scroll_delta),
                    confidence=0.92,
                    timestamp=now,
                    state_description=f"Two-Finger Scroll ({scroll_delta:+.1f})"
                )
        else:
            self.prev_scroll_y = None


        # Default Pointer Hover
        return GestureEvent(
            gesture=GestureType.HOVER,
            cursor_pos=cursor_coords,
            raw_point=raw_coords,
            delta=(dx, dy),
            confidence=hand.confidence,
            timestamp=now,
            state_description="Tracking Pointer"
        )
