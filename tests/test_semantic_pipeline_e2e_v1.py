from __future__ import annotations

import json

import pytest

from integration.feature_graph_v1 import FeatureGraphValidationError
from integration.llm_fidelity_gate_v1 import (
    LLMSemanticFidelityError,
    assert_explicit_constraints_preserved,
    assert_no_implicit_m8_drill_conversion,
)


class FakeGateway:
    def __init__(self, requirements_payload: dict, intent_payload: dict):
        self.requirements_payload = requirements_payload
        self.intent_payload = intent_payload
        self.calls: list[str] = []

    def complete_validated(self, request, parser):
        self.calls.append(request.user_prompt)
        payload = self.requirements_payload if len(self.calls) == 1 else self.intent_payload
        return type("Response", (), {"content": json.dumps(payload)})()


def _requirements() -> dict:
    return {
        "schema": "ai-designer.engineering-requirements.v2",
        "request_id": "e2e-001",
        "description": "motor bracket 120x80, base thickness 10, four M8 holes, two ribs, R5 outer edges",
        "load_cases": [{"id": "design", "force_n": 100, "direction": [0, 0, 1]}],
        "envelope": {"x_mm": 120, "y_mm": 80, "z_mm": 10},
        "material": "unspecified",
        "manufacturing_constraints": [],
        "explicit_constraints": [
            {"id": "c1", "kind": "dimension", "target": "width", "value": 120, "unit": "mm"},
            {"id": "c2", "kind": "dimension", "target": "height", "value": 80, "unit": "mm"},
            {"id": "c3", "kind": "dimension", "target": "thickness", "value": 10, "unit": "mm"},
            {"id": "c4", "kind": "fastener", "target": "bolt_hole_size", "value": "M8", "unit": "nominal"},
            {"id": "c5", "kind": "count", "target": "hole_count", "value": 4, "unit": "count"},
            {"id": "c6", "kind": "count", "target": "rib_count", "value": 2, "unit": "count"},
            {"id": "c7", "kind": "radius", "target": "outer_fillet_radius", "value": 5, "unit": "mm"},
        ],
    }


def _graph() -> dict:
    return {
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "motor_bracket_120x80",
        "design_intent": "motor bracket",
        "units": "mm",
        "features": [
            {"feature_id": "base_profile", "kind": "profile", "depends_on": [], "params": {"width": 120, "height": 80, "requirement_refs": ["c1", "c2"]}},
            {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["base_profile"], "params": {"thickness": 10, "requirement_refs": ["c3"]}},
            {"feature_id": "holes", "kind": "hole_pattern", "depends_on": ["base"], "params": {"fastener": "M8", "count": 4, "requirement_refs": ["c4", "c5"]}},
            {"feature_id": "ribs", "kind": "pattern", "depends_on": ["base"], "params": {"count": 2, "requirement_refs": ["c6"]}},
            {"feature_id": "fillet", "kind": "fillet", "depends_on": ["base", "holes", "ribs"], "params": {"radius_mm": 5, "selection": "all_outer_edges", "requirement_refs": ["c7"]}},
        ],
    }


def test_semantic_e2e_preserves_requirements_before_feature_graph_execution():
    requirements = _requirements()
    graph = _graph()
    assert_explicit_constraints_preserved(graph, requirements)
    assert_no_implicit_m8_drill_conversion(graph, requirements)
    assert all(node["kind"] in {"profile", "extrude_boss", "hole_pattern", "pattern", "fillet"} for node in graph["features"])


def test_semantic_e2e_rejects_known_bad_llm_plan():
    requirements = _requirements()
    bad = _graph()
    bad["features"][2]["params"] = {"diameter_mm": 8.5, "count": 4}
    with pytest.raises(LLMSemanticFidelityError):
        assert_no_implicit_m8_drill_conversion(bad, requirements)


def test_feature_graph_stage_stays_deterministic_after_semantic_gate():
    graph = _graph()
    from integration.feature_graph_v1 import feature_graph_from_dict

    parsed = feature_graph_from_dict(graph)
    assert [node.feature_id for node in parsed.features] == [
        "base_profile", "base", "holes", "ribs", "fillet"
    ]
