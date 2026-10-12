"""
AirOS Refined Natural Gesture State Machine with Dwell-Pinch Dual Mode.
Features:
1. Dynamic 1-Euro / Exponential Moving Average (EMA) cursor smoothing for zero-jitter glide.
2. DUAL CLICKING MODES:
   - Mode A (Instant Pinch-Release Click): Pinch thumb & index together (< 0.075 norm distance) and release.
   - Mode B (Hover Dwell Click): Simply hold your pointer over any application or button for 1.0 second.
3. Pinch & Drag: Pinch and hold while moving hand to drag windows or sliders.
4. Two-Finger Scroll: Move two fingers vertically to scroll.
5. Fist / Clench Toggle: Curl hand into a fist to toggle the spatial dock / launcher.
"""

import time
import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from airos.vision.landmarks import (
    HandDetection, Point3D,
    WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP,
    INDEX_PIP, MIDDLE_PIP, RING_PIP, PINKY_PIP, THUMB_IP,
    INDEX_MCP, MIDDLE_MCP
)

class GestureType(Enum):
    NONE = auto()
    HOVER = auto()
    PINCH_CLICK = auto()
    DWELL_CLICK = auto()
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
    dwell_progress: float = 0.0  # 0.0 to 1.0 for on-screen charging circle

class AdaptiveJitterGate:
    """
    Sub-pixel deadband gate that eliminates webcam sensor shimmer and micro-tremor
    without stickiness. Uses continuous quadratic ease-in above threshold.
    """
    def __init__(self, deadband: float = 0.0016):
        self.deadband = deadband
        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None

    def reset(self):
        self.last_x = None
        self.last_y = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self.last_x is None or self.last_y is None:
            self.last_x = x
            self.last_y = y
            return x, y

        dx = x - self.last_x
        dy = y - self.last_y
        dist = math.hypot(dx, dy)

        if dist < self.deadband:
            # Completely stationary - filter sensor shimmer to zero
            return self.last_x, self.last_y

        # Soft continuous transition above deadband: no rigid snapping
        ramp = min(1.0, (dist - self.deadband) / max(0.0001, self.deadband * 2.2))
        weight = ramp * ramp
        self.last_x = self.last_x + dx * weight
        self.last_y = self.last_y + dy * weight
        return self.last_x, self.last_y


class OneEuroFilter:
    """
    Casiez et al. 1-Euro Filter for human-computer interaction.
    Dynamically adjusts cutoff frequency based on movement speed:
    - Low speed / hovering: very low cutoff (0.15 Hz) -> zero jitter, rock-solid stability
    - High speed: higher cutoff (15-30 Hz) -> zero latency, instant response
    """
    def __init__(self, min_cutoff: float = 0.15, beta: float = 1.4, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    def reset(self):
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, rate: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * max(0.01, cutoff))
        te = 1.0 / max(0.01, rate)
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.x_prev = x
            self.t_prev = timestamp
            self.dx_prev = 0.0
            return x

        dt = timestamp - self.t_prev
        if dt <= 1e-5:
            return self.x_prev
        rate = 1.0 / dt

        # Estimate derivative (speed)
        dx = (x - self.x_prev) * rate
        alpha_d = self._alpha(rate, self.d_cutoff)
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # Dynamic cutoff frequency
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        alpha = self._alpha(rate, cutoff)

        x_hat = alpha * x + (1.0 - alpha) * self.x_prev
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = timestamp
        return x_hat


class GestureStateMachine:
    """
    High-precision gesture state machine with Touchless Air Mouse Engine:
    - Ergonomically stabilized biometric pointer anchor
    - Sub-pixel Adaptive Jitter Gate
    - 1-Euro continuous speed-adaptive cursor smoothing (zero-jitter + zero-lag)
    - Pre-pinch aim stabilization & Pinch Target Anchor (locks cursor during click)
    - Dwell-to-click with visual progress indicator
    - Pinch-to-drag with natural threshold
    - Smooth two-finger scrolling
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 1-Euro Filters tuned for Touchless Air Mouse
        smoothing_weight = float(self.config.get("cursor_smoothing", 0.85))
        # Higher smoothing weight -> lower min_cutoff (maximum stillness)
        min_cutoff = max(0.06, 0.42 - smoothing_weight * 0.36)
        beta = 1.2 + (1.0 - min(1.0, smoothing_weight)) * 0.8
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=1.0)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta, d_cutoff=1.0)
        self.jitter_gate = AdaptiveJitterGate(deadband=0.0016)

        # Smooth position state
        self.smoothed_x = 0.5
        self.smoothed_y = 0.5
        self.prev_x = 0.5
        self.prev_y = 0.5
        
        # Pinch / Click state & Target Anchor
        self.is_pinched = False
        self.pinch_start_time = 0.0
        self.pinch_anchor = (0.5, 0.5)
        self.last_click_time = 0.0
        self.is_dragging = False

        # Dwell Click state
        self.dwell_anchor = (0.5, 0.5)
        self.dwell_start_time = 0.0
        self.dwell_progress = 0.0
        self.dwell_cooldown = 0.0
        
        # Fist toggle tracking
        self.fist_start_time = 0.0
        self.fist_triggered = False

        # Scroll state
        self.prev_scroll_y = None
        self.swipe_history = []
        self.last_swipe_time = 0.0

    def reset(self):
        self.is_pinched = False
        self.is_dragging = False
        self.prev_scroll_y = None
        self.dwell_start_time = 0.0
        self.dwell_progress = 0.0
        self.swipe_history.clear()
        self.filter_x.reset()
        self.filter_y.reset()
        self.jitter_gate.reset()

    def _get_stabilized_anchor(self, hand: HandDetection, index_up: bool, middle_up: bool) -> Tuple[float, float]:
        """
        Calculates an ergonomically stabilized pointer anchor.
        Touchless air mice blend index tip with metacarpal joints to neutralize finger tremor.
        """
        idx_tip = hand.index_tip
        if len(hand.landmarks) <= INDEX_MCP:
            return (idx_tip.x, idx_tip.y)

        idx_mcp = hand.get(INDEX_MCP)

        if index_up and not middle_up:
            # Single-finger pointing pose: 75% tip + 25% knuckle
            return (idx_tip.x * 0.75 + idx_mcp.x * 0.25,
                    idx_tip.y * 0.75 + idx_mcp.y * 0.25)
        elif index_up and middle_up:
            # Multi-finger / Open palm: blend index & middle knuckles with tip
            mid_mcp = hand.get(MIDDLE_MCP)
            return (idx_mcp.x * 0.45 + mid_mcp.x * 0.35 + idx_tip.x * 0.20,
                    idx_mcp.y * 0.45 + mid_mcp.y * 0.35 + idx_tip.y * 0.20)
        else:
            return (idx_tip.x, idx_tip.y)

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
                    state_description="Tracking Lost (Drag Released)",
                    dwell_progress=0.0
                )
            self.reset()
            return GestureEvent(
                gesture=GestureType.NONE,
                cursor_pos=(self.smoothed_x, self.smoothed_y),
                raw_point=(self.smoothed_x, self.smoothed_y),
                confidence=0.0,
                timestamp=now,
                state_description="No Hand Detected",
                dwell_progress=0.0
            )

        # 1. Finger Extension Status
        index_up = hand.finger_extended(INDEX_TIP, INDEX_PIP)
        middle_up = hand.finger_extended(MIDDLE_TIP, MIDDLE_PIP)
        ring_up = hand.finger_extended(RING_TIP, RING_PIP)
        pinky_up = hand.finger_extended(PINKY_TIP, PINKY_PIP)

        # 2. Stabilized Biometric Pointer Anchor & Jitter Gate
        raw_x, raw_y = self._get_stabilized_anchor(hand, index_up, middle_up)
        gated_x, gated_y = self.jitter_gate.filter(raw_x, raw_y)

        # 3. Coordinate normalization and active area mapping
        margin = float(self.config.get("active_area_margin", 0.12))
        norm_x = (gated_x - margin) / max(0.01, (1.0 - 2 * margin))
        norm_y = (gated_y - margin) / max(0.01, (1.0 - 2 * margin))
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # 4. 1-Euro adaptive continuous speed-responsive smoothing
        filtered_x = self.filter_x.filter(norm_x, now)
        filtered_y = self.filter_y.filter(norm_y, now)

        # Scale-invariant pinch detection: combines absolute distance and hand-scale ratio
        pinch_dist = hand.index_tip.distance_2d(hand.thumb_tip)
        hand_scale = hand.wrist.distance_2d(hand.get(INDEX_MCP)) if len(hand.landmarks) > 5 else 0.20
        rel_pinch = pinch_dist / max(0.06, hand_scale)
        
        pinch_thresh = float(self.config.get("click_pinch_threshold", 0.070))
        currently_pinching = (pinch_dist < pinch_thresh) or (rel_pinch < 0.38)

        # Pre-pinch aim stabilization damping: damp movement when fingers contract to pinch
        # Prevents cursor from jumping or sliding away right before click threshold
        if pinch_dist < pinch_thresh * 1.45 and not self.is_dragging:
            pre_damp = max(0.18, (pinch_dist - pinch_thresh * 0.7) / max(0.01, pinch_thresh * 0.75))
            filtered_x = self.prev_x + (filtered_x - self.prev_x) * pre_damp
            filtered_y = self.prev_y + (filtered_y - self.prev_y) * pre_damp

        self.smoothed_x = filtered_x
        self.smoothed_y = filtered_y

        dx = self.smoothed_x - self.prev_x
        dy = self.smoothed_y - self.prev_y
        self.prev_x = self.smoothed_x
        self.prev_y = self.smoothed_y

        cursor_coords = (self.smoothed_x, self.smoothed_y)
        raw_coords = (raw_x, raw_y)

        # --- GESTURE 1: PINCH CLICK & DRAG WITH TARGET ANCHOR LOCK ---
        cooldown_sec = float(self.config.get("pinch_cooldown_ms", 140)) / 1000.0
        double_click_window = float(self.config.get("double_click_window_ms", 420)) / 1000.0

        if currently_pinching:
            # Cancel dwell when actively pinching
            self.dwell_start_time = 0.0
            self.dwell_progress = 0.0

            if not self.is_pinched:
                self.is_pinched = True
                self.pinch_start_time = now
                # Lock cursor to current point so finger squeeze doesn't displace cursor aim
                self.pinch_anchor = (self.smoothed_x, self.smoothed_y)
                self.is_dragging = False

            anchor_dist = math.hypot(self.smoothed_x - self.pinch_anchor[0], self.smoothed_y - self.pinch_anchor[1])

            # IMPORTANT: Drag activates ONLY when the user intentionally moves their hand while pinched (> 0.042)
            # Stationary pinch never aborts clicks into drags
            if anchor_dist > 0.042:
                self.is_dragging = True
                return GestureEvent(
                    gesture=GestureType.DRAG,
                    cursor_pos=cursor_coords,
                    raw_point=raw_coords,
                    delta=(dx, dy),
                    confidence=0.98,
                    timestamp=now,
                    state_description="Pinch Dragging",
                    dwell_progress=1.0
                )
            else:
                # Lock cursor to initial aim position during the squeeze
                cursor_coords = self.pinch_anchor
                return GestureEvent(
                    gesture=GestureType.HOVER,
                    cursor_pos=cursor_coords,
                    raw_point=raw_coords,
                    delta=(0.0, 0.0),
                    confidence=0.98,
                    timestamp=now,
                    state_description="Pinch Aiming...",
                    dwell_progress=0.0
                )

        else:
            if self.is_pinched:
                self.is_pinched = False
                
                if self.is_dragging:
                    self.is_dragging = False
                    return GestureEvent(
                        gesture=GestureType.HOVER,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=hand.confidence,
                        timestamp=now,
                        state_description="Drag Released",
                        dwell_progress=0.0
                    )

                # Released without dragging -> Trigger click at anchored target position!
                click_coords = self.pinch_anchor
                time_since_last_click = now - self.last_click_time

                if time_since_last_click >= cooldown_sec:
                    if time_since_last_click <= double_click_window and time_since_last_click >= 0.05:
                        self.last_click_time = now
                        return GestureEvent(
                            gesture=GestureType.DOUBLE_CLICK,
                            cursor_pos=click_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Double Click",
                            dwell_progress=0.0
                        )
                    else:
                        self.last_click_time = now
                        return GestureEvent(
                            gesture=GestureType.PINCH_CLICK,
                            cursor_pos=click_coords,
                            raw_point=raw_coords,
                            confidence=0.98,
                            timestamp=now,
                            state_description="Pinch Click",
                            dwell_progress=0.0
                        )

        # --- GESTURE 2: DWELL HOVER CLICK ---
        # If user holds pointer stationary over an icon or button, auto-trigger a click!
        dwell_enabled = bool(self.config.get("dwell_click_enabled", True))
        dwell_duration = float(self.config.get("intent_dwell_ms", 1200)) / 1000.0
        dwell_drift = math.hypot(self.smoothed_x - self.dwell_anchor[0], self.smoothed_y - self.dwell_anchor[1])

        if dwell_enabled and dwell_drift < 0.035 and (now - self.dwell_cooldown) > 1.2 and not currently_pinching:
            if self.dwell_start_time == 0.0:
                self.dwell_start_time = now
            else:
                dwell_elapsed = now - self.dwell_start_time
                self.dwell_progress = min(1.0, dwell_elapsed / max(0.5, dwell_duration))
                if self.dwell_progress >= 1.0:
                    self.dwell_start_time = 0.0
                    self.dwell_progress = 0.0
                    self.dwell_cooldown = now
                    self.last_click_time = now
                    return GestureEvent(
                        gesture=GestureType.DWELL_CLICK,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=0.99,
                        timestamp=now,
                        state_description="Dwell Hover Clicked!",
                        dwell_progress=0.0
                    )
        else:
            self.dwell_anchor = (self.smoothed_x, self.smoothed_y)
            self.dwell_start_time = 0.0
            self.dwell_progress = 0.0

        # --- GESTURE 3: CLOSED FIST TOGGLE MENU ---
        if not index_up and not middle_up and not ring_up and not pinky_up and not currently_pinching:
            if not self.fist_triggered:
                if self.fist_start_time == 0.0:
                    self.fist_start_time = now
                elif (now - self.fist_start_time) >= 0.55:
                    self.fist_triggered = True
                    return GestureEvent(
                        gesture=GestureType.FIST_TOGGLE_MENU,
                        cursor_pos=cursor_coords,
                        raw_point=raw_coords,
                        confidence=0.96,
                        timestamp=now,
                        state_description="Fist (App Launcher Toggled)",
                        dwell_progress=0.0
                    )
            return GestureEvent(
                gesture=GestureType.HOVER,
                cursor_pos=cursor_coords,
                raw_point=raw_coords,
                confidence=0.9,
                timestamp=now,
                state_description="Fist Closed",
                dwell_progress=0.0
            )
        else:
            self.fist_start_time = 0.0
            self.fist_triggered = False

        # --- GESTURE 4: TWO-FINGER SCROLL ---
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
                    state_description=f"Two-Finger Scroll ({scroll_delta:+.1f})",
                    dwell_progress=0.0
                )
        else:
            self.prev_scroll_y = None

        # Default Pointer Hover with Dwell Progress
        state_desc = "Hovering"
        if self.dwell_progress > 0.05:
            state_desc = f"Hover Clicking... {int(self.dwell_progress * 100)}%"

        return GestureEvent(
            gesture=GestureType.HOVER,
            cursor_pos=cursor_coords,
            raw_point=raw_coords,
            delta=(dx, dy),
            confidence=hand.confidence,
            timestamp=now,
            state_description=state_desc,
            dwell_progress=self.dwell_progress
        )
