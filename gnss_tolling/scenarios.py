"""Scenario position streams.

Each scenario is one vehicle's GNSS trace showing a distinct condition: a clean
mainline drive, a tunnel gap that must be bridged, a service-road drive that only
grazes a tolled section, and a poor-accuracy trace whose fixes fall below the
confidence floor.
"""
from __future__ import annotations

import copy
from typing import Callable, Dict, List

from .geo import Point


def _main(x, acc=5.0, t=0):
    return Point(x, 0.0, acc, t)


def _service(x, acc=5.0, t=0):
    return Point(x, 40.0, acc, t)


def baseline() -> List[Point]:
    """A clean drive along the full tolled mainline: both sections charged."""
    return [_main(x, t=i * 1000) for i, x in enumerate(range(0, 10_001, 250))]


def tunnel_gap() -> List[Point]:
    """Mainline drive with a positioning gap through section A (a tunnel): the
    gap is bridged and the section is still charged."""
    pts = []
    i = 0
    for x in range(0, 10_001, 250):
        if 2_000 < x < 3_000:
            continue
        pts.append(_main(x, t=i * 1000))
        i += 1
    return pts


def ramp_graze() -> List[Point]:
    """Vehicle stays on the service road, only clipping the start of section B:
    coverage stays below the threshold and nothing is charged."""
    pts = [_service(x, t=i * 1000) for i, x in enumerate(range(0, 10_001, 250))]
    pts.append(_main(6_000, t=999_000))
    pts.append(_main(6_150, t=999_500))
    return pts


def poor_gps() -> List[Point]:
    """A drive with degraded accuracy midway between the two roads: many fixes
    are ambiguous and fall below the confidence floor."""
    return [Point(x, 20.0, accuracy_m=45.0, t_ms=i * 1000)
            for i, x in enumerate(range(0, 10_001, 250))]


SCENARIOS: Dict[str, Callable[[], List[Point]]] = {
    "baseline": baseline,
    "tunnel_gap": tunnel_gap,
    "ramp_graze": ramp_graze,
    "poor_gps": poor_gps,
}


def apply_scenario(name: str) -> List[Point]:
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario: {name}")
    return copy.deepcopy(SCENARIOS[name]())
