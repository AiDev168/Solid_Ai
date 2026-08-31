import json

import pytest

from app.llm_feature_graph_v1 import (
    FeatureGraphPlanningError,
    LocalLLMConfig,
    _extract_json,
    validate_feature_graph,
)


def valid_graph():
    return {
        "schema_version": "feature-graph-v0.5.6-draft",
        "units": "meters",
        "nodes": [
            {"id": "n1", "type": "box", "width": 0.12, "depth": 0.08, "height": 0.01},
            {"id": "n2", "type": "hole", "ref": {"node_face": {"node": "n1", "selector": "top"}}},
        ],
    }


def test_extract_plain_and_fenced_json():
    graph = valid_graph()
    assert _extract_json(json.dumps(graph))["nodes"][0]["id"] == "n1"
    fenced = "```json\n" + json.dumps(graph) + "\n```"
    assert _extract_json(fenced)["nodes"][1]["type"] == "hole"


def test_validate_feature_graph_accepts_cad_neutral_graph():
    result = validate_feature_graph(valid_graph())
    assert result["units"] == "meters"
    assert len(result["nodes"]) == 2


def test_validate_rejects_raw_tool_calls():
    graph = valid_graph()
    graph["tool"] = "extrude_feature"
    with pytest.raises(FeatureGraphPlanningError):
        validate_feature_graph(graph)


def test_validate_rejects_future_node_reference():
    graph = valid_graph()
    graph["nodes"][0]["feature"] = "n99"
    with pytest.raises(FeatureGraphPlanningError):
        validate_feature_graph(graph)


def test_validate_rejects_unknown_feature_type():
    graph = valid_graph()
    graph["nodes"][0]["type"] = "magic_feature"
    with pytest.raises(FeatureGraphPlanningError):
        validate_feature_graph(graph)


def test_local_llm_config_rejects_non_local_endpoint():
    with pytest.raises(FeatureGraphPlanningError):
        LocalLLMConfig(base_url="https://example.com/v1").validate_local_only()


def test_local_llm_config_accepts_lm_studio_default():
    LocalLLMConfig(base_url="http://127.0.0.1:1234/v1").validate_local_only()
