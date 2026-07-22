"""Domain claims about trip building and section rating."""
from gnss_tolling.geo import Point
from gnss_tolling.network import sample_network
from gnss_tolling.trip import build_trip
from gnss_tolling.assistant import advise
from gnss_tolling.scenarios import apply_scenario

NET = sample_network()


def test_clean_trip_charges_both_sections():
    trip = build_trip(apply_scenario("baseline"), NET)
    charged = [s for s in trip.section_charges if s.charged]
    assert {s.section_id for s in charged} == {"SEC-A", "SEC-B"}


def test_distance_based_charge_matches_tariff_times_length():
    trip = build_trip(apply_scenario("baseline"), NET)
    # SEC-A is 3 km at 0.12/km = 0.36; SEC-B is 3 km at 0.15/km = 0.45
    assert round(trip.total, 2) == 0.81


def test_tunnel_gap_is_bridged_and_the_section_is_still_charged():
    trip = build_trip(apply_scenario("tunnel_gap"), NET)
    sec_a = next(s for s in trip.section_charges if s.section_id == "SEC-A")
    assert sec_a.charged is True   # gap through SEC-A bridged


def test_ramp_graze_below_coverage_is_not_charged():
    trip = build_trip(apply_scenario("ramp_graze"), NET)
    assert trip.total == 0.0
    grazed = next(s for s in trip.section_charges if s.section_id == "SEC-B")
    assert grazed.charged is False
    assert "anti-overcharge" in grazed.reason


def test_poor_gps_produces_no_charge_and_flags_low_confidence():
    trip = build_trip(apply_scenario("poor_gps"), NET)
    assert trip.total == 0.0
    assert trip.low_confidence_points > 0
    assert advise(trip).priority == "elevated"


def test_duplicate_positions_are_deduplicated():
    p = Point(5000, 0.0, 5.0, t_ms=1000, device="OBU9")
    trip = build_trip([p, p, p], NET)
    # three identical fixes collapse to one matched point
    assert trip.matched_points == 1


def test_coverage_is_a_fraction_between_zero_and_one():
    trip = build_trip(apply_scenario("baseline"), NET)
    for s in trip.section_charges:
        assert 0.0 <= s.coverage <= 1.0


def test_service_road_only_trip_is_not_charged():
    pts = [Point(x, 40.0, 5.0, t_ms=i * 1000) for i, x in enumerate(range(0, 10001, 500))]
    trip = build_trip(pts, NET)
    assert trip.total == 0.0
