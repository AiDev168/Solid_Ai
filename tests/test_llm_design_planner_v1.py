import json

import pytest

from integration.feature_graph_v1 import FeatureGraphValidationError
from integration.llm_design_planner_v1 import SemanticLLMPlannerV1


class FakeTransport:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.payload


def test_llm_plan_is_parsed_and_validated():
    transport = FakeTransport(json.dumps({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "bracket",
        "design_intent": "motor bracket 120x80x10 with four M8 mounting holes, two ribs and R5 outer fillets",
        "units": "mm",
        "features": [
            {"feature_id": "base_profile", "kind": "profile", "depends_on": [], "params": {"width_mm": 120, "height_mm": 80}},
            {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["base_profile"], "params": {"depth_mm": 10}},
            {"feature_id": "holes", "kind": "hole_pattern", "depends_on": ["base"], "params": {"nominal": "M8", "through": True}},
            {"feature_id": "ribs", "kind": "rib", "depends_on": ["base"], "params": {"count": 2}},
            {"feature_id": "fillets", "kind": "fillet", "depends_on": ["holes", "ribs"], "params": {"radius_mm": 5}},
        ],
    }))
    graph = SemanticLLMPlannerV1(transport).plan("Build a motor bracket 120 by 80 by 10, four M8 holes, two ribs, R5 outer edges")
    assert graph.part_id == "bracket"
    assert [node.kind for node in graph.features] == ["profile", "extrude_boss", "hole_pattern", "rib", "fillet"]
    assert transport.calls


def test_llm_plan_rejects_unsupported_feature_kind():
    transport = FakeTransport(json.dumps({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "bad",
        "design_intent": "bad",
        "units": "mm",
        "features": [
            {"feature_id": "x", "kind": "raw_com_call", "depends_on": [], "params": {}}
        ],
    }))
    with pytest.raises(FeatureGraphValidationError):
        SemanticLLMPlannerV1(transport).plan("do anything")


def test_llm_plan_rejects_dependency_cycle():
    transport = FakeTransport(json.dumps({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "cycle",
        "design_intent": "cycle",
        "units": "mm",
        "features": [
            {"feature_id": "a", "kind": "profile", "depends_on": ["b"], "params": {}},
            {"feature_id": "b", "kind": "extrude_boss", "depends_on": ["a"], "params": {}},
        ],
    }))
    with pytest.raises(FeatureGraphValidationError):
        SemanticLLMPlannerV1(transport).plan("cycle")
