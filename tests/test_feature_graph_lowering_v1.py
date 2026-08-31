import pytest

from integration.feature_graph_compiler_v1 import compile_feature_graph
from integration.feature_graph_lowering_v1 import (
    FeatureGraphLoweringError,
    build_default_lowering_registry,
)
from integration.feature_graph_v1 import feature_graph_from_dict


def test_hole_pattern_lowers_only_with_explicit_diameter_and_centers():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "p",
        "design_intent": "four mounting holes",
        "units": "mm",
        "features": [{
            "feature_id": "holes",
            "kind": "hole_pattern",
            "depends_on": [],
            "params": {
                "fastener": "M8",
                "count": 4,
                "diameter_mm": 8.0,
                "centers_mm": [[-50, -30], [50, -30], [50, 30], [-50, 30]],
            },
        }],
    })
    lowered = build_default_lowering_registry().lower_plan(compile_feature_graph(graph))
    ops = lowered.features[0].operations
    assert [op.tool for op in ops] == [
        "create_sketch",
        "add_sketch_entity",
        "add_sketch_entity",
        "add_sketch_entity",
        "add_sketch_entity",
        "extrude_feature",
    ]
    assert ops[1].params["radius"] == pytest.approx(0.004)
    assert ops[1].params["cx"] == pytest.approx(-0.05)
    assert ops[-1].params["feature_type"] == "cut"
    assert ops[-1].params["through"] is True


def test_m8_alone_never_gets_converted_to_a_backend_diameter():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "p",
        "design_intent": "four M8 mounting holes",
        "units": "mm",
        "features": [{
            "feature_id": "holes",
            "kind": "hole_pattern",
            "depends_on": [],
            "params": {
                "fastener": "M8",
                "count": 4,
                "centers_mm": [[-50, -30], [50, -30], [50, 30], [-50, 30]],
            },
        }],
    })
    with pytest.raises(FeatureGraphLoweringError, match="diameter_mm"):
        build_default_lowering_registry().lower_plan(compile_feature_graph(graph))


def test_fillet_requires_explicitly_resolved_edge_indices():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "p",
        "design_intent": "R5 fillet",
        "units": "mm",
        "features": [{
            "feature_id": "fillet",
            "kind": "fillet",
            "depends_on": [],
            "params": {"radius_mm": 5, "selection": "all_outer_edges"},
        }],
    })
    with pytest.raises(FeatureGraphLoweringError, match="edge_indices"):
        build_default_lowering_registry().lower_plan(compile_feature_graph(graph))


def test_fillet_lowers_after_reference_resolution():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "p",
        "design_intent": "R5 fillet",
        "units": "mm",
        "features": [{
            "feature_id": "fillet",
            "kind": "fillet",
            "depends_on": [],
            "params": {
                "radius_mm": 5,
                "selection": "all_outer_edges",
                "edge_indices": [2, 7, 9],
            },
        }],
    })
    lowered = build_default_lowering_registry().lower_plan(compile_feature_graph(graph))
    op = lowered.features[0].operations[0]
    assert op.tool == "add_edge_feature"
    assert op.phase == "execute"
    assert op.params["radius_or_distance"] == pytest.approx(0.005)
    assert op.params["edge_indices"] == "[2, 7, 9]"
