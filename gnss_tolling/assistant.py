"""Explainable assistant for the GNSS tolling engine.

Summarises the trip: how many fixes matched, which sections were charged, and —
importantly — calls out both poor-GNSS trips that need review and correctly
excluded ramp grazes, with the numbers behind each call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .trip import TripCharge


@dataclass
class Recommendation:
    priority: str
    headline: str
    actions: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "priority": self.priority, "headline": self.headline,
            "actions": list(self.actions), "trace": list(self.trace),
            "summary": dict(self.summary),
        }


def advise(trip: TripCharge) -> Recommendation:
    total_pts = trip.matched_points + trip.unmatched_points + trip.low_confidence_points
    total_pts = total_pts or 1
    charged = [s for s in trip.section_charges if s.charged]
    grazes = [s for s in trip.section_charges if not s.charged and s.coverage > 0]

    trace = [
        f"{trip.matched_points}/{total_pts} positions matched to a road "
        f"({trip.low_confidence_points} low-confidence, {trip.unmatched_points} off-network)",
        f"trip on {trip.road_id}; {len(charged)} section(s) charged, total {trip.total:.2f}",
    ]
    for s in trip.section_charges:
        trace.append(f"{s.section_id}: coverage {s.coverage:.0%} -> "
                     f"{'charged' if s.charged else 'not charged'}")
    actions: List[str] = []

    low_ratio = trip.low_confidence_points / total_pts
    if low_ratio >= 0.3:
        priority = "elevated"
        headline = "Poor GNSS quality on this trip: many fixes too weak to charge"
        actions.append("Flag for review: low-confidence fixes may under-capture chargeable distance")
    elif grazes:
        priority = "normal"
        headline = "Trip rated; ramp/graze sections correctly excluded"
        for g in grazes:
            actions.append(f"{g.section_id} grazed at {g.coverage:.0%} coverage — not charged (anti-overcharge)")
    elif not charged:
        priority = "normal"
        headline = "No tolled section traversed: nothing to charge"
    else:
        priority = "normal"
        headline = f"Trip rated cleanly: {len(charged)} section(s), {trip.total:.2f} total"

    if not actions:
        actions.append("No action required; charge report ready to deliver")
    return Recommendation(priority, headline, actions, trace, trip.as_dict())
