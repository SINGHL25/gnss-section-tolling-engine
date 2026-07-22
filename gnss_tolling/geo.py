"""Minimal planar geometry.

GNSS tolling is fundamentally a geometry problem: where is the vehicle relative to
the road? To keep it dependency-free and testable, positions are modelled on a
local planar grid in metres rather than on the ellipsoid — the perpendicular
distance from a point to a road segment, and how far along that segment the point
projects, are all that map matching needs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Point:
    x: float          # metres east
    y: float          # metres north
    accuracy_m: float = 5.0   # reported GNSS accuracy (lower is better)
    t_ms: int = 0             # position timestamp
    device: str = "OBU"


@dataclass
class Segment:
    ax: float
    ay: float
    bx: float
    by: float

    def length(self) -> float:
        return math.hypot(self.bx - self.ax, self.by - self.ay)


def point_to_segment(px: float, py: float, seg: Segment):
    """Return (perpendicular_distance, projection_fraction) for a point.

    projection_fraction is 0 at endpoint a, 1 at endpoint b, clamped to [0, 1].
    """
    dx, dy = seg.bx - seg.ax, seg.by - seg.ay
    denom = dx * dx + dy * dy
    if denom == 0:
        return math.hypot(px - seg.ax, py - seg.ay), 0.0
    t = ((px - seg.ax) * dx + (py - seg.ay) * dy) / denom
    t = max(0.0, min(1.0, t))
    cx, cy = seg.ax + t * dx, seg.ay + t * dy
    return math.hypot(px - cx, py - cy), t
