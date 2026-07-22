"""Trip building and rating.

Matched positions become a trip. Duplicate fixes (same device and timestamp) are
dropped. The chainage covered on the tolled road is assembled into intervals,
bridging short gaps — a tunnel or a missed fix should not split one continuous
drive into two. Each tolled section is then charged only if the vehicle actually
traversed enough of it: a brief graze at a ramp falls below the coverage
threshold and is *not* charged, which is the core anti-overcharging rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .geo import Point
from .match import MatchResult, map_match
from .network import RoadNetwork, TollSection

MIN_COVERAGE = 0.50     # fraction of a section that must be traversed to charge it
BRIDGE_GAP_M = 2_500.0  # gaps up to this are treated as continuous travel


@dataclass
class SectionCharge:
    section_id: str
    coverage: float           # fraction of the section traversed 0..1
    distance_m: float         # metres of the section covered
    charged: bool
    amount: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "section_id": self.section_id, "coverage": round(self.coverage, 3),
            "distance_m": round(self.distance_m, 0), "charged": self.charged,
            "amount": round(self.amount, 2), "reason": self.reason,
        }


@dataclass
class TripCharge:
    device: str
    road_id: str
    section_charges: List[SectionCharge] = field(default_factory=list)
    total: float = 0.0
    matched_points: int = 0
    unmatched_points: int = 0
    low_confidence_points: int = 0

    def as_dict(self) -> dict:
        return {
            "device": self.device, "road_id": self.road_id,
            "total": round(self.total, 2),
            "matched_points": self.matched_points,
            "unmatched_points": self.unmatched_points,
            "low_confidence_points": self.low_confidence_points,
            "sections": [s.as_dict() for s in self.section_charges],
        }


def _merge_intervals(chainages: List[float], bridge_gap: float):
    """Turn a sorted list of covered chainages into merged [start, end] intervals,
    bridging gaps up to bridge_gap."""
    if not chainages:
        return []
    chainages = sorted(chainages)
    intervals = [[chainages[0], chainages[0]]]
    for c in chainages[1:]:
        if c - intervals[-1][1] <= bridge_gap:
            intervals[-1][1] = c
        else:
            intervals.append([c, c])
    return intervals


def _overlap(a0, a1, b0, b1) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def build_trip(positions: List[Point], net: RoadNetwork,
               min_coverage: float = MIN_COVERAGE,
               bridge_gap: float = BRIDGE_GAP_M) -> TripCharge:
    device = positions[0].device if positions else "OBU"

    # Deduplicate on (device, timestamp).
    seen = set()
    unique: List[Point] = []
    for p in positions:
        key = (p.device, p.t_ms)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    # Match and tally which tolled road (if any) carries the trip.
    matched = unmatched = low_conf = 0
    by_road: dict = {}
    for p in unique:
        m = map_match(p, net)
        if not m.matched:
            if m.snap_dist_m <= 25.0:   # was near a road but low confidence
                low_conf += 1
            else:
                unmatched += 1
            continue
        matched += 1
        by_road.setdefault(m.road_id, []).append(m.chainage_m)

    # Pick the tolled road with the most matched fixes as the trip's road.
    tolled_roads = {rid: cs for rid, cs in by_road.items() if net.roads[rid].tolled}
    if not tolled_roads:
        return TripCharge(device, "-", [], 0.0, matched, unmatched, low_conf)
    road_id = max(tolled_roads, key=lambda r: len(tolled_roads[r]))
    intervals = _merge_intervals(tolled_roads[road_id], bridge_gap)

    charges: List[SectionCharge] = []
    total = 0.0
    for sec in net.sections_for(road_id):
        covered = sum(_overlap(i0, i1, sec.start_m, sec.end_m) for i0, i1 in intervals)
        coverage = covered / sec.length_m() if sec.length_m() else 0.0
        if coverage >= min_coverage:
            amount = sec.tariff_per_km * (sec.length_m() / 1000.0)
            charges.append(SectionCharge(sec.section_id, coverage, covered, True, amount,
                                         f"coverage {coverage:.0%} >= {min_coverage:.0%}: charged {sec.length_m()/1000:.1f} km"))
            total += amount
        else:
            charges.append(SectionCharge(sec.section_id, coverage, covered, False, 0.0,
                                         f"coverage {coverage:.0%} below {min_coverage:.0%}: not charged (anti-overcharge)"))

    return TripCharge(device, road_id, charges, round(total, 2),
                      matched, unmatched, low_conf)
