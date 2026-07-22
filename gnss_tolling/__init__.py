"""gnss_tolling: a GNSS section-based (distance) tolling engine.

Ingest GNSS position reports, map-match them to a road network, detect which
tolled sections were traversed, and rate each trip by distance. Zero third-party
dependencies. Standard library only.
"""
from .geo import Point, Segment, point_to_segment
from .network import RoadNetwork, TollSection, Road, sample_network
from .match import map_match, MatchResult, SNAP_WINDOW_M, MIN_CONFIDENCE
from .trip import build_trip, TripCharge, SectionCharge, MIN_COVERAGE, BRIDGE_GAP_M
from .assistant import advise, Recommendation
from .scenarios import SCENARIOS, apply_scenario, baseline

__all__ = [
    "Point", "Segment", "point_to_segment", "RoadNetwork", "TollSection", "Road",
    "sample_network", "map_match", "MatchResult", "SNAP_WINDOW_M",
    "MIN_CONFIDENCE", "build_trip", "TripCharge", "SectionCharge", "MIN_COVERAGE",
    "BRIDGE_GAP_M", "advise", "Recommendation", "SCENARIOS", "apply_scenario",
    "baseline",
]
