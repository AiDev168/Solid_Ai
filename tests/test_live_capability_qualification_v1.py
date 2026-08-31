from __future__ import annotations

import asyncio

from integration.capability_qualification_v1 import QualificationScenario
from integration.live_capability_qualification_v1 import LiveQualificationExecutorV1, QualificationPreflightError


class _Item:
    def __init__(self, text: str):
        self.text = text


class _Result:
    def __init__(self, payload):
        self.structuredContent = {"result": __import__("json").dumps(payload)}
        self.content = [_Item(__import__("json").dumps(payload))]


class _Session:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "ensure_ready":
            return _Result({"ok": True, "status": "READY", "state_version": 0})
        if name == "open_new_part":
            return _Result({"ok": True, "status": "COMPLETED", "state_version": 1})
        if name == "analyze_model":
            return _Result({"ok": True, "status": "COMPLETED", "state_version": 3, "data": ["bodies=1"]})
        return _Result({"ok": True, "status": "COMPLETED", "state_version": 2})


def test_live_qualification_executes_and_collects_final_evidence():
    session = _Session()
    scenario = QualificationScenario(
        "Q-TEST-001", "part.cut_extrude", "prismatic", "test", "test",
        (
            {"tool": "create_sketch", "params": {"plane": "Top Plane"}},
            {"tool": "add_sketch_entity", "params": {"entity_type": "rectangle", "x1": -0.01, "y1": -0.01, "x2": 0.01, "y2": 0.01}},
            {"tool": "extrude_feature", "params": {"depth": 0.001, "feature_type": "cut"}},
        ),
        ("COMPLETED",),
    )
    report = asyncio.run(LiveQualificationExecutorV1(session).execute(scenario))
    assert report["ok"] is True
    assert report["verified"] is True
    assert report["capability_id"] == "part.cut_extrude"
    assert session.calls[-1] == ("analyze_model", {"analysis_type": "geometry"})


def test_live_qualification_rejects_empty_scenario_before_execution():
    session = _Session()
    scenario = QualificationScenario("Q-TEST-EMPTY", "x", "x", "x", "x", tuple(), tuple())
    try:
        asyncio.run(LiveQualificationExecutorV1(session).execute(scenario))
    except QualificationPreflightError as exc:
        assert "no operations" in str(exc)
    else:
        raise AssertionError("expected QualificationPreflightError")
    assert session.calls == []
