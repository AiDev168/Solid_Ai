from integration.feature_graph_compiler_v1 import compile_feature_graph
from integration.feature_graph_v1 import feature_graph_from_dict


def _graph():
    return feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "generic_motor_bracket_120x80",
        "design_intent": "motor bracket 120x80x10 with four M8 mounting holes, two ribs and R5 outer fillets",
        "units": "mm",
        "features": [
            {"feature_id": "base_profile", "kind": "profile", "depends_on": [], "params": {"width_mm": 120, "height_mm": 80}},
            {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["base_profile"], "params": {"thickness": 10}},
            {"feature_id": "holes", "kind": "hole_pattern", "depends_on": ["base"], "params": {
                "fastener": "M8", "count": 4, "diameter_mm": 8.0,
                "centers_mm": [[-45, -25], [45, -25], [-45, 25], [45, 25]],
                "depth": "through_all", "through_depth_m": 0.01,
                "support_reference": {"reference_id": "base_end", "kind": "face", "role": "extrude_end_face", "feature_id": "base"},
            }},
            {"feature_id": "rib_left", "kind": "rib", "depends_on": ["base"], "params": {
                "x_center_mm": -30, "width_mm": 8, "span_mm": 50, "height_mm": 45,
                "support_reference": {"reference_id": "rib_left_support", "kind": "face", "role": "extrude_end_face", "feature_id": "base"},
            }},
            {"feature_id": "rib_right", "kind": "rib", "depends_on": ["base"], "params": {
                "x_center_mm": 30, "width_mm": 8, "span_mm": 50, "height_mm": 45,
                "support_reference": {"reference_id": "rib_right_support", "kind": "face", "role": "extrude_end_face", "feature_id": "base"},
            }},
            {"feature_id": "fillet", "kind": "fillet", "depends_on": ["holes", "rib_left", "rib_right"], "params": {
                "radius_mm": 5,
                "selection_reference": {"reference_id": "base_outer_edges", "kind": "edge", "role": "outer_extrusion_boundary", "feature_id": "base", "criteria": {"bounds_uv_m": [-0.06, 0.06, -0.04, 0.04]}},
            }},
        ],
    })


def test_generic_motor_bracket_graph_contains_only_semantic_references():
    graph = _graph()
    compiled = compile_feature_graph(graph)
    hole_params = dict(compiled.features[2].operations[0].params)
    fillet_params = dict(compiled.features[-1].operations[0].params)
    assert "support_reference" in hole_params
    assert "support_face_index" in hole_params and hole_params["support_face_index"] is None
    assert isinstance(fillet_params["selection_reference"], dict)
    assert "edge_indices" not in fillet_params


def test_generic_motor_bracket_rib_is_not_native_capability_alias():
    compiled = compile_feature_graph(_graph())
    rib = compiled.features[3]
    assert rib.capability.capability_id == "part.rib"
    assert rib.operations[0].phase == "lower"
    assert dict(rib.operations[0].params)["support_reference"]["reference_id"] == "rib_left_support"
