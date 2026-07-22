"""The road network and its tolled sections.

A network is a set of roads, each a chain of segments laid out by chainage (metres
from the road's start). Some roads are tolled and carry sections — a start/end
chainage and a per-kilometre tariff. The sample network is a tolled mainline
running parallel to an untolled service road, so map matching has a real decision
to make: a vehicle on the service road must not be charged for the mainline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .geo import Point, Segment


@dataclass
class TollSection:
    section_id: str
    road_id: str
    start_m: float          # chainage where the section begins
    end_m: float            # chainage where it ends
    tariff_per_km: float    # charge per kilometre traversed

    def length_m(self) -> float:
        return self.end_m - self.start_m


@dataclass
class Road:
    road_id: str
    y_offset: float         # lateral position of this road on the grid
    length_m: float
    tolled: bool
    seg_len_m: float = 1000.0

    def segments(self) -> List[Segment]:
        segs = []
        x = 0.0
        while x < self.length_m - 1e-6:
            end = min(x + self.seg_len_m, self.length_m)
            segs.append(Segment(x, self.y_offset, end, self.y_offset))
            x = end
        return segs


@dataclass
class RoadNetwork:
    roads: Dict[str, Road] = field(default_factory=dict)
    sections: List[TollSection] = field(default_factory=list)

    def add_road(self, road: Road) -> None:
        self.roads[road.road_id] = road

    def add_section(self, section: TollSection) -> None:
        self.sections.append(section)

    def sections_for(self, road_id: str) -> List[TollSection]:
        return [s for s in self.sections if s.road_id == road_id]


def sample_network() -> RoadNetwork:
    """A 10 km tolled mainline (y=0) beside a 10 km untolled service road (y=40),
    with two tolled sections on the mainline."""
    net = RoadNetwork()
    net.add_road(Road("MAINLINE", y_offset=0.0, length_m=10_000, tolled=True))
    net.add_road(Road("SERVICE", y_offset=40.0, length_m=10_000, tolled=False))
    net.add_section(TollSection("SEC-A", "MAINLINE", 1_000, 4_000, tariff_per_km=0.12))
    net.add_section(TollSection("SEC-B", "MAINLINE", 6_000, 9_000, tariff_per_km=0.15))
    return net
