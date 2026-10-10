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
