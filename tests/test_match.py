"""Domain claims about geometry and map matching."""
from gnss_tolling.geo import Point, Segment, point_to_segment
from gnss_tolling.network import sample_network
from gnss_tolling.match import map_match, SNAP_WINDOW_M, MIN_CONFIDENCE


def test_perpendicular_distance_to_a_segment():
    seg = Segment(0, 0, 100, 0)          # along the x-axis
    d, frac = point_to_segment(50, 10, seg)
    assert round(d, 3) == 10.0
    assert round(frac, 3) == 0.5


def test_projection_is_clamped_beyond_the_ends():
    seg = Segment(0, 0, 100, 0)
    _, frac = point_to_segment(200, 0, seg)
    assert frac == 1.0


def test_a_point_on_the_mainline_matches_the_mainline():
    net = sample_network()
    m = map_match(Point(5000, 0.0, accuracy_m=5.0), net)
    assert m.matched is True
    assert m.road_id == "MAINLINE"


def test_a_point_on_the_service_road_matches_the_service_road():
    net = sample_network()
    m = map_match(Point(5000, 40.0, accuracy_m=5.0), net)
    assert m.matched is True
    assert m.road_id == "SERVICE"


def test_a_point_far_from_every_road_is_unmatched():
    net = sample_network()
    m = map_match(Point(5000, 500.0), net)
    assert m.matched is False


def test_good_accuracy_gives_higher_confidence_than_poor_accuracy():
    net = sample_network()
    good = map_match(Point(5000, 0.0, accuracy_m=3.0), net)
    poor = map_match(Point(5000, 0.0, accuracy_m=45.0), net)
    assert good.confidence > poor.confidence


def test_a_fix_between_the_two_roads_is_ambiguous():
    net = sample_network()
    m = map_match(Point(5000, 20.0, accuracy_m=10.0), net)
    assert m.ambiguous is True


def test_confidence_floor_blocks_a_weak_match():
    net = sample_network()
    # midway, poor accuracy -> ambiguous and weak -> should not match
    m = map_match(Point(5000, 20.0, accuracy_m=45.0), net)
    assert m.confidence < MIN_CONFIDENCE
    assert m.matched is False
