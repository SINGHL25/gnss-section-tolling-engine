"""Map matching.

Each GNSS position is snapped to the nearest road, and the match carries a
confidence: it is high when the point is close to a road and the reported GNSS
accuracy is good, and it is deliberately dragged down when two roads are almost
equally close (an ambiguous fix that should not be trusted to charge). Positions
outside the snap window, or with a confidence below the floor, are not matched —
better to leave a passage unrated than to charge the wrong road.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .geo import Point, point_to_segment, Segment
from .network import RoadNetwork

SNAP_WINDOW_M = 25.0    # a point beyond this from every road is unmatched
ACC_REF_M = 50.0        # accuracy at/above which the GNSS score is fully degraded
AMBIGUITY_M = 8.0       # if the two nearest roads are within this, the fix is ambiguous
MIN_CONFIDENCE = 0.40   # matches below this are not used for charging


@dataclass
class MatchResult:
    matched: bool
    road_id: Optional[str]
    chainage_m: float          # distance along the road
    snap_dist_m: float
    confidence: float
    ambiguous: bool = False

    def as_dict(self) -> dict:
        return {
            "matched": self.matched, "road_id": self.road_id,
            "chainage_m": round(self.chainage_m, 1),
            "snap_dist_m": round(self.snap_dist_m, 2),
            "confidence": round(self.confidence, 3), "ambiguous": self.ambiguous,
        }


def _nearest_on_road(pt: Point, road) -> tuple:
    """Return (snap_distance, chainage) of the closest point on a road."""
    best_d, best_chain = float("inf"), 0.0
    base = 0.0
    for seg in road.segments():
        d, frac = point_to_segment(pt.x, pt.y, seg)
        if d < best_d:
            best_d = d
            best_chain = base + frac * seg.length()
        base += seg.length()
    return best_d, best_chain


def map_match(pt: Point, net: RoadNetwork) -> MatchResult:
    candidates = []
    for road in net.roads.values():
        d, chain = _nearest_on_road(pt, road)
        candidates.append((d, chain, road.road_id))
    candidates.sort(key=lambda c: c[0])
    best_d, best_chain, best_road = candidates[0]

    if best_d > SNAP_WINDOW_M:
        return MatchResult(False, None, 0.0, best_d, 0.0)

    snap_score = max(0.0, 1.0 - best_d / SNAP_WINDOW_M)
    acc_score = max(0.0, 1.0 - pt.accuracy_m / ACC_REF_M)
    confidence = snap_score * (0.5 + 0.5 * acc_score)

    ambiguous = len(candidates) > 1 and (candidates[1][0] - best_d) < AMBIGUITY_M
    if ambiguous:
        confidence *= 0.5

    matched = confidence >= MIN_CONFIDENCE
    return MatchResult(matched, best_road if matched else None,
                       best_chain, best_d, round(confidence, 3), ambiguous)
