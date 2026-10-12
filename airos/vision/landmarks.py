"""
AirOS Hand Landmark Data Model.
Standardizes 21 3D hand keypoints adhering to the canonical Hand Landmark topology.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import math

# Landmark Indices
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20

# Canonical Bone Connections for Visual Rendering
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index finger
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle finger
    (9, 10), (10, 11), (11, 12),
    # Ring finger
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm Base
    (5, 9), (9, 13), (13, 17)
]

@dataclass
class Point3D:
    x: float  # Normalized 0.0 - 1.0 (horizontal)
    y: float  # Normalized 0.0 - 1.0 (vertical)
    z: float = 0.0  # Depth estimate

    def distance_to(self, other: "Point3D") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)

    def distance_2d(self, other: "Point3D") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

@dataclass
class HandDetection:
    landmarks: List[Point3D] = field(default_factory=list) # Exactly 21 keypoints
    handedness: str = "right"  # "right" or "left"
    confidence: float = 0.0
    bounding_box: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0) # (x, y, w, h) normalized
    backend: str = "tflite_dnn"

    @property
    def is_valid(self) -> bool:
        return len(self.landmarks) == 21

    @property
    def is_anatomical_hand(self) -> bool:
        """
        Validates whether the 21 landmarks correspond to a plausible human hand topology.
        Filters out false positive detections triggered on background textures, wall edges, or clothing.
        """
        if len(self.landmarks) != 21:
            return False

        # 1. Palm length check (wrist 0 to middle MCP 9)
        # Normal hand palm in normalized frame is between ~0.035 and ~0.48
        wrist = self.landmarks[WRIST]
        mid_mcp = self.landmarks[MIDDLE_MCP]
        palm_dist = wrist.distance_2d(mid_mcp)
        if palm_dist < 0.035 or palm_dist > 0.48:
            return False

        # 2. Knuckle chain ordering & distances
        # Knuckles: index_mcp(5), mid_mcp(9), ring_mcp(13), pinky_mcp(17)
        idx_mcp = self.landmarks[INDEX_MCP]
        ring_mcp = self.landmarks[RING_MCP]
        pky_mcp = self.landmarks[PINKY_MCP]

        d_5_9 = idx_mcp.distance_2d(mid_mcp)
        d_9_13 = mid_mcp.distance_2d(ring_mcp)
        d_13_17 = ring_mcp.distance_2d(pky_mcp)

        # Knuckle span shouldn't exceed 1.25x palm distance or be microscopic
        if d_5_9 > (palm_dist * 1.25) or d_9_13 > (palm_dist * 1.25) or d_13_17 > (palm_dist * 1.25):
            return False

        # Total knuckle span from index base (5) to pinky base (17)
        knuckle_span = idx_mcp.distance_2d(pky_mcp)
        if knuckle_span < (palm_dist * 0.18) or knuckle_span > (palm_dist * 1.85):
            return False

        # 3. Overall bounding box extent relative to palm distance
        # A human hand (palm + fingers) is at most ~3.5x the palm base length
        xs = [p.x for p in self.landmarks]
        ys = [p.y for p in self.landmarks]
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        max_span = max(span_x, span_y)
        if max_span > (palm_dist * 3.6) or max_span < (palm_dist * 0.5):
            return False

        # 4. Finger segment length sanity (no exploded / collapsed bones)
        # Check index and middle finger segments
        finger_chains = [
            (5, 6, 7, 8),     # Index
            (9, 10, 11, 12),  # Middle
            (13, 14, 15, 16), # Ring
            (17, 18, 19, 20)  # Pinky
        ]
        for mcp_idx, pip_idx, dip_idx, tip_idx in finger_chains:
            mcp = self.landmarks[mcp_idx]
            pip = self.landmarks[pip_idx]
            dip = self.landmarks[dip_idx]
            tip = self.landmarks[tip_idx]
            seg1 = mcp.distance_2d(pip)
            seg2 = pip.distance_2d(dip)
            seg3 = dip.distance_2d(tip)
            # Bone segments cannot be massively larger than palm
            if seg1 > (palm_dist * 1.3) or seg2 > (palm_dist * 1.3) or seg3 > (palm_dist * 1.3):
                return False

        return True

    def get(self, idx: int) -> Point3D:
        return self.landmarks[idx]

    @property
    def index_tip(self) -> Point3D:
        return self.landmarks[INDEX_TIP]

    @property
    def thumb_tip(self) -> Point3D:
        return self.landmarks[THUMB_TIP]

    @property
    def middle_tip(self) -> Point3D:
        return self.landmarks[MIDDLE_TIP]

    @property
    def wrist(self) -> Point3D:
        return self.landmarks[WRIST]

    def finger_extended(self, tip_idx: int, pip_idx: int) -> bool:
        """Determines if a finger is extended relative to the palm base / wrist."""
        wrist = self.landmarks[WRIST]
        tip = self.landmarks[tip_idx]
        pip = self.landmarks[pip_idx]
        # Distance from wrist to tip is significantly greater than wrist to PIP
        return tip.distance_2d(wrist) > (pip.distance_2d(wrist) * 1.15)
