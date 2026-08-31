import pytest

from integration.feature_graph_compiler_v1 import (
    FeatureGraphCompileError,
    compile_feature_graph,
)
from integration.feature_graph_v1 import feature_graph_from_dict


BRACKET_GRAPH = feature_graph_from_dict({
    "schema": "solid-ai.feature-graph.v1",
    "part_id": "motor_bracket_120x80",
    "design_intent": "motor bracket 120x80x10 with four M8 holes, two ribs and R5 outer fillets",
    "units": "mm",
    "features": [
        {"feature_id": "base_profile", "kind": "profile", "depends_on": [],
         "params": {"width": 120, "height": 80}},
        {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["base_profile"],
         "params": {"thickness": 10}},
        {"feature_id": "holes", "kind": "hole_pattern", "depends_on": ["base"],
         "params": {"fastener": "M8", "count": 4, "spacing_x": 100, "spacing_y": 60,
                    "depth": "through_all"}},
        {"feature_id": "rib_left", "kind": "rib", "depends_on": ["base"],
         "params": {"position": "left", "height": 10, "thickness": 5}},
        {"feature_id": "fillet", "kind": "fillet", "depends_on": ["base", "holes", "rib_left"],
         "params": {"radius_mm": 5, "selection": "all_outer_edges"}},
    ],
})


def test_compiler_binds_each_semantic_kind_to_a_capability():
    compiled = compile_feature_graph(BRACKET_GRAPH)
    assert [item.capability.capability_id for item in compiled.features] == [
        "part.create_sketch",
        "part.extrude_boss",
        "part.hole",
        "part.rib",
        "edge.fillet",
    ]


def test_profile_compiles_to_sketch_and_entity_operations():
    compiled = compile_feature_graph(BRACKET_GRAPH)
    operations = compiled.features[0].operations
    assert [op.tool for op in operations] == ["create_sketch", "add_sketch_entity"]
    assert operations[1].params["x1"] == pytest.approx(-0.06)
    assert operations[1].params["y1"] == pytest.approx(-0.04)


def test_compiler_keeps_m8_semantic_intent_without_inventing_drill_diameter():
    compiled = compile_feature_graph(BRACKET_GRAPH)
    operation = compiled.features[2].operations[0]
    assert operation.params["hole_intent"] == "M8"
    assert "diameter_m" not in operation.params


def test_compiler_normalizes_mm_dimensions_to_meters_at_backend_boundary():
    compiled = compile_feature_graph(BRACKET_GRAPH)
    profile = compiled.features[0].operations[0]
    base = compiled.features[1].operations[0]
    assert profile.params["plane"] == "Top Plane"
    assert compiled.features[0].operations[1].params["x2"] == pytest.approx(0.06)
    assert base.params["depth"] == pytest.approx(0.01)


def test_compiler_requires_semantic_fillet_selection():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "bad",
        "design_intent": "bad",
        "units": "mm",
        "features": [{
            "feature_id": "f", "kind": "fillet", "depends_on": [],
            "params": {"radius_mm": 5},
        }],
    })
    with pytest.raises(FeatureGraphCompileError):
        compile_feature_graph(graph)


def test_compiler_is_execution_free():
    compiled = compile_feature_graph(BRACKET_GRAPH)
    assert all(operation.phase in {"execute", "lower"} for feature in compiled.features for operation in feature.operations)
