"""
AirOS Gesture Definitions and State Machine.
Recognizes:
- Pointer Move (index finger point)
- Click (pinch index + thumb)
- Drag (hold pinch while moving)
- Double-Click (two rapid pinches)
- Two-Finger Scroll (index + middle fingers extended)
- Open Palm (quick-action / Start menu)
- Horizontal Swipe (application / workspace switch)
- Peace Sign / V-Gesture (toggle virtual keyboard)
- Emergency Pause (fist or sustained gesture)
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
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()
    TOGGLE_KEYBOARD = auto()
    EMERGENCY_PAUSE = auto()

@dataclass
class GestureEvent:
    gesture: GestureType
    cursor_pos: Tuple[float, float] # (norm_x, norm_y) [0.0, 1.0]
    raw_point: Tuple[float, float]
    delta: Tuple[float, float] = (0.0, 0.0) # (dx, dy)
    confidence: float = 0.0
    timestamp: float = 0.0
    state_description: str = ""

class GestureStateMachine:
    """
    Robust gesture state machine featuring:
    - IntentLock dwell confirmation to prevent accidental clicks
    - Exponential Moving Average (EMA) cursor smoothing
    - Edge-triggered click generation (no runaway repeat clicks during sustained hold)
    - Two-finger scrolling delta accumulator
    - Horizontal swipe velocity detector
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # State tracking
        self.smoothed_x = 0.5
        self.smoothed_y = 0.5
        self.prev_x = 0.5
        self.prev_y = 0.5
        
        # Pinch / Click state
        self.is_pinched = False
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.is_dragging = False
        self.click_count = 0
        
        # Swipe tracking
        self.swipe_history = [] # list of (time, x)
        self.last_swipe_time = 0.0
        
        # Open Palm tracking
        self.palm_open_start = 0.0
        self.palm_triggered = False

        # V-sign / Keyboard toggle tracking
        self.vsign_start = 0.0
        self.vsign_triggered = False

        # Scroll previous position
        self.prev_scroll_y = None

        # Pause / Resume state
        self.is_paused = False

    def reset(self):
        self.is_pinched = False
        self.is_dragging = False
        self.prev_scroll_y = None
        self.swipe_history.clear()

    def process(self, hand: Optional[HandDetection], screen_w: int = 1920, screen_h: int = 1080) -> GestureEvent:
        now = time.time()
        
        if hand is None or not hand.is_valid:
            if self.is_dragging:
                # Release drag safety trigger
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
        # Active control region mapping (user doesn't need to reach frame edges)
        margin = float(self.config.get("active_area_margin", 0.15))
        idx_tip = hand.index_tip
        raw_x = idx_tip.x
        raw_y = idx_tip.y

        norm_x = (raw_x - margin) / max(0.01, (1.0 - 2 * margin))
        norm_y = (raw_y - margin) / max(0.01, (1.0 - 2 * margin))
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # 2. Adaptive Cursor Smoothing (Exponential Moving Average)
        alpha = float(self.config.get("cursor_smoothing", 0.65))
        # Large target mode applies higher smoothing
        if self.config.get("large_target_mode", False):
            alpha = 0.45

        self.smoothed_x = alpha * self.smoothed_x + (1.0 - alpha) * norm_x
        self.smoothed_y = alpha * self.smoothed_y + (1.0 - alpha) * norm_y

        dx = self.smoothed_x - self.prev_x
        dy = self.smoothed_y - self.prev_y
        self.prev_x = self.smoothed_x
        self.prev_y = self.smoothed_y

        cursor_coords = (self.smoothed_x, self.smoothed_y)
        raw_coords = (raw_x, raw_y)

        # 3. Finger Extension Status
        index_up = hand.finger_extended(INDEX_TIP, INDEX_PIP)
        middle_up = hand.finger_extended(MIDDLE_TIP, MIDDLE_PIP)
        ring_up = hand.finger_extended(RING_TIP, RING_PIP)
        pinky_up = hand.finger_extended(PINKY_TIP, PINKY_PIP)

        # Pinch distance between index and thumb tip
        pinch_dist = hand.index_tip.distance_2d(hand.thumb_tip)
        pinch_thresh = float(self.config.get("click_pinch_threshold", 0.055))
        currently_pinching = pinch_dist < pinch_thresh

        # --- GESTURE DECISION LOGIC ---

        # GESTURE: OPEN PALM (All 5 fingers extended) -> Start menu / Quick actions
        if index_up and middle_up and ring_up and pinky_up and not currently_pinching:
            if not self.palm_triggered:
                if self.palm_open_start == 0.0:
                    self.palm_open_start = now
                elif (now - self.palm_open_start) >= 0.45:
                    self.palm_triggered = True
                    return GestureEvent(
                        gesture=GestureType.OPEN_PALM,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=0.95,
                        timestamp=now,
                        state_description="Open Palm Triggered"
                    )
            return GestureEvent(
                gesture=GestureType.HOVER,
                cursor_pos=cursor_coords,
                raw_point=raw_coords,
                confidence=hand.confidence,
                timestamp=now,
                state_description="Open Palm (Holding)"
            )
        else:
            self.palm_open_start = 0.0
            self.palm_triggered = False

        # GESTURE: V-SIGN / PEACE SIGN (Index & Middle up, ring & pinky down) -> Toggle Virtual Keyboard
        if index_up and middle_up and not ring_up and not pinky_up and not currently_pinching:
            # Check if index and middle tips are separated (V shape)
            separation = hand.index_tip.distance_2d(hand.middle_tip)
            if separation > 0.05:
                if not self.vsign_triggered:
                    if self.vsign_start == 0.0:
                        self.vsign_start = now
                    elif (now - self.vsign_start) >= 0.5:
                        self.vsign_triggered = True
                        return GestureEvent(
                            gesture=GestureType.TOGGLE_KEYBOARD,
                            cursor_pos=cursor_coords,
                            raw_point=raw_coords,
                            confidence=0.92,
                            timestamp=now,
                            state_description="V-Sign (Keyboard Toggle)"
                        )
                return GestureEvent(
                    gesture=GestureType.HOVER,
                    cursor_pos=cursor_coords,
                    raw_point=raw_coords,
                    confidence=0.9,
                    timestamp=now,
                    state_description="V-Sign Holding"
                )
        else:
            self.vsign_start = 0.0
            self.vsign_triggered = False

        # GESTURE: TWO-FINGER SCROLL (Index & Middle close together and extended, Ring & Pinky curled)
        if index_up and middle_up and not ring_up and not pinky_up and not currently_pinching:
            separation = hand.index_tip.distance_2d(hand.middle_tip)
            if separation <= 0.05:
                # Two fingers close together -> SCROLL
                curr_scroll_y = (hand.index_tip.y + hand.middle_tip.y) * 0.5
                scroll_delta = 0.0
                if self.prev_scroll_y is not None:
                    # Inverted natural scrolling delta
                    scroll_delta = (self.prev_scroll_y - curr_scroll_y) * float(self.config.get("scroll_sensitivity", 24.0))
                self.prev_scroll_y = curr_scroll_y

                return GestureEvent(
                    gesture=GestureType.SCROLL,
                    cursor_pos=cursor_coords,
                    raw_point=raw_coords,
                    delta=(0.0, scroll_delta),
                    confidence=0.9,
                    timestamp=now,
                    state_description=f"Two-Finger Scroll ({scroll_delta:+.1f})"
                )
        else:
            self.prev_scroll_y = None

        # GESTURE: HORIZONTAL SWIPE (Fast sideways movement of palm / index)
        self.swipe_history.append((now, self.smoothed_x))
        # Keep 0.3s history
        self.swipe_history = [(t, x) for (t, x) in self.swipe_history if now - t <= 0.35]
        if len(self.swipe_history) >= 4 and (now - self.last_swipe_time) > 0.8:
            dt = self.swipe_history[-1][0] - self.swipe_history[0][0]
            if dt > 0.08:
                vx = (self.swipe_history[-1][1] - self.swipe_history[0][1]) / dt
                threshold = float(self.config.get("swipe_velocity_threshold", 1.2))
                if vx > threshold:
                    self.last_swipe_time = now
                    self.swipe_history.clear()
                    return GestureEvent(
                        gesture=GestureType.SWIPE_RIGHT,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        delta=(vx, 0.0),
                        confidence=0.88,
                        timestamp=now,
                        state_description="Swipe Right (Next Workspace)"
                    )
                elif vx < -threshold:
                    self.last_swipe_time = now
                    self.swipe_history.clear()
                    return GestureEvent(
                        gesture=GestureType.SWIPE_LEFT,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        delta=(vx, 0.0),
                        confidence=0.88,
                        timestamp=now,
                        state_description="Swipe Left (Prev Workspace)"
                    )

        # GESTURE: PINCH CLICK / DRAG (IntentLock confirmation)
        intent_lock_enabled = bool(self.config.get("intent_lock_enabled", True))
        intent_dwell_sec = float(self.config.get("intent_dwell_ms", 200)) / 1000.0
        cooldown_sec = float(self.config.get("pinch_cooldown_ms", 320)) / 1000.0
        double_click_window = float(self.config.get("double_click_window_ms", 420)) / 1000.0

        if currently_pinching:
            if not self.is_pinched:
                # Pinch initiated
                self.is_pinched = True
                self.pinch_start_time = now
            else:
                pinch_duration = now - self.pinch_start_time
                dwell_met = pinch_duration >= intent_dwell_sec if intent_lock_enabled else True

                # Check if drag threshold is crossed
                if dwell_met and pinch_duration > 0.35:
                    self.is_dragging = True
                    return GestureEvent(
                        gesture=GestureType.DRAG,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        delta=(dx, dy),
                        confidence=0.95,
                        timestamp=now,
                        state_description="Pinch Dragging Window/Item"
                    )
        else:
            if self.is_pinched:
                # Pinch was released
                pinch_duration = now - self.pinch_start_time
                self.is_pinched = False
                
                if self.is_dragging:
                    # Released from drag
                    self.is_dragging = False
                    return GestureEvent(
                        gesture=GestureType.HOVER,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=hand.confidence,
                        timestamp=now,
                        state_description="Drag Released"
                    )

                dwell_met = pinch_duration >= (intent_dwell_sec * 0.7) if intent_lock_enabled else True
                if dwell_met and (now - self.last_click_time) >= cooldown_sec:
                    # Valid click trigger
                    if (now - self.last_click_time) <= double_click_window:
                        # Double click
                        self.last_click_time = now
                        self.click_count = 0
                        return GestureEvent(
                            gesture=GestureType.DOUBLE_CLICK,
                            cursor_pos=cursor_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Double Click Triggered"
                        )
                    else:
                        # Single click
                        self.last_click_time = now
                        self.click_count = 1
                        return GestureEvent(
                            gesture=GestureType.PINCH_CLICK,
                            cursor_pos=cursor_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Click Triggered"
                        )

        # Default fallback: Cursor Hover / Movement
        return GestureEvent(
            gesture=GestureType.HOVER,
            cursor_pos=cursor_coords,
            raw_point=raw_coords,
            delta=(dx, dy),
            confidence=hand.confidence,
            timestamp=now,
            state_description="Tracking Index (Hover)"
        )
