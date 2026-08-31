from integration.topology_edge_v1 import edge_length, is_usable_edge, select_longest_usable_edge


def test_circular_edge_with_coincident_representative_points_is_usable_from_length():
    edge = {"i": 10, "start": [0, 0, 0.08], "end": [0, 0, 0.08], "mid": [0, 0, 0], "length": 0.037699}
    assert edge_length(edge) == 0.037699
    assert is_usable_edge(edge)


def test_straight_edge_without_explicit_length_uses_endpoint_distance():
    edge = {"i": 5, "start": [0, 0, 0], "end": [0, 0, 0.04]}
    assert abs(edge_length(edge) - 0.04) < 1e-12
    assert is_usable_edge(edge)


def test_zero_length_edge_without_measured_curve_length_is_rejected():
    edge = {"i": 7, "start": [0, 0, 0], "end": [0, 0, 0], "mid": [0, 0, 0]}
    assert edge_length(edge) is None
    assert not is_usable_edge(edge)


def test_longest_usable_edge_prefers_measured_analytic_curve():
    edges = [
        {"i": 1, "start": [0, 0, 0], "end": [0, 0, 0.02]},
        {"i": 2, "start": [0, 0, 0.08], "end": [0, 0, 0.08], "length": 0.188496},
        {"i": 3, "start": [0, 0, 0], "end": [0, 0, 0]},
    ]
    assert select_longest_usable_edge(edges) == (2, 0.188496)
