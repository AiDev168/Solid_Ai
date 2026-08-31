import pytest

from integration.aidesigner_assets import CapabilitySpec
from integration.feature_capability_registry_v1 import (
    FeatureCapabilityRegistryV1,
    build_default_feature_capability_registry,
)
from integration.feature_graph_compiler_v1 import compile_feature_graph
from integration.feature_graph_v1 import feature_graph_from_dict


def test_default_registry_keeps_explicit_bindings():
    registry = build_default_feature_capability_registry()
    assert registry.require("profile").capability_id == "part.create_sketch"
    assert registry.require("hole_pattern").capability_id == "part.hole"
    assert registry.capability_for("not-a-feature") is None


def test_candidate_capability_can_be_compiled_without_becoming_proven():
    candidate = CapabilitySpec(
        "candidate.demo_profile",
        "solidpilot",
        "candidate_tool",
        "candidate",
        "candidate input",
        "live verification required",
        "runtime discovery",
    )
    registry = FeatureCapabilityRegistryV1()
    registry.register("profile", candidate)
    graph = feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "candidate",
        "design_intent": "candidate profile",
        "units": "mm",
        "features": [{
            "feature_id": "p",
            "kind": "profile",
            "depends_on": [],
            "params": {"width": 10, "height": 20},
        }],
    })
    plan = compile_feature_graph(graph, capability_registry=registry)
    assert plan.features[0].capability.capability_id == "candidate.demo_profile"
    assert plan.features[0].capability.status == "candidate"
