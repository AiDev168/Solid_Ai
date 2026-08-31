import pytest

from integration.aidesigner_assets import get_capability
from integration.feature_capability_registry_v1 import build_default_feature_capability_registry
from integration.feature_graph_compiler_v1 import FeatureGraphCompileError, compile_feature_graph
from integration.feature_graph_v1 import feature_graph_from_dict


def test_revolve_and_revolve_cut_are_promoted_from_live_evidence():
    assert get_capability("part.revolve").status == "proven"
    assert get_capability("part.revolve_cut").status == "proven"


def test_rib_is_explicit_candidate_and_never_aliases_extrude_boss():
    registry = build_default_feature_capability_registry()
    binding = registry.binding_for("rib")
    assert binding is not None
    assert binding.capability_id == "part.rib"
    assert binding.capability.status == "candidate"
    assert binding.capability.tool == "create_rib"


def test_revolve_compiles_only_with_explicit_axis_endpoints():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "shaft",
        "design_intent": "stepped shaft",
        "units": "mm",
        "features": [{
            "feature_id": "revolve",
            "kind": "revolve",
            "depends_on": ["profile"],
            "params": {"angle_deg": 360, "axis_endpoints": [[0, 0], [0, 120]]},
        }],
    })
    compiled = compile_feature_graph(graph)
    op = compiled.features[0].operations[0]
    assert op.capability_id == "part.revolve"
    assert op.params["feature_type"] == "revolve"
    assert op.params["axis_x2"] == 0.0
    assert op.params["axis_y2"] == 120.0


def test_revolve_rejects_missing_axis_instead_of_guessing():
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "shaft",
        "design_intent": "stepped shaft",
        "units": "mm",
        "features": [{
            "feature_id": "revolve",
            "kind": "revolve",
            "depends_on": [],
            "params": {"angle_deg": 360},
        }],
    })
    with pytest.raises(FeatureGraphCompileError, match="axis_endpoints"):
        compile_feature_graph(graph)
