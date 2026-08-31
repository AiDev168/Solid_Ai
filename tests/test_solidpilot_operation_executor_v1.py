import asyncio

import pytest

from integration.feature_graph_compiler_v1 import Operation
from integration.feature_graph_execution_v1 import CompiledPlanExecutor
from integration.solidpilot_operation_executor_v1 import (
    SolidPilotExecutionError,
    SolidPilotOperationExecutor,
)
from integration.solidpilot_capability_catalog_v1 import SolidPilotCapabilityCatalogV1


class Response:
    def __init__(self, payload, is_error=False):
        self.structuredContent = {"result": payload}
        self.content = []
        self.isError = is_error


class FakeSession:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, dict(arguments)))
        payloads = {
            "ensure_ready": {"ok": True, "status": "READY", "state_version": 0},
            "open_new_part": {"ok": True, "status": "COMPLETED", "state_version": 1},
            "create_sketch": {"ok": True, "status": "COMPLETED", "state_version": 2},
            "add_sketch_entity": {"ok": True, "status": "COMPLETED", "state_version": 3, "result_geometry": {"kind": "rectangle"}},
            "extrude_feature": {"ok": True, "status": "COMPLETED", "state_version": 4, "result_geometry": {"volume": 1.0}},
            "analyze_model": {"ok": True, "status": "COMPLETED", "state_version": 4, "data": ["bodies=1"]},
        }
        return Response(payloads[name])


def test_real_executor_prepares_and_executes_without_second_execution_stack():
    async def scenario():
        session = FakeSession()
        executor = SolidPilotOperationExecutor(session)
        operations = [
            Operation("base", "part.create_sketch", "create_sketch", {"plane": "Top Plane"}),
            Operation("base", "part.create_sketch", "add_sketch_entity", {"entity_type": "rectangle", "x1": -0.05, "y1": -0.03, "x2": 0.05, "y2": 0.03}),
            Operation("base", "part.extrude_boss", "extrude_feature", {"depth": 0.01, "feature_type": "boss"}),
        ]

        class Plan:
            features = [type("CF", (), {"feature_id": "base", "operations": operations})()]

        report = await executor.execute_plan(Plan())
        assert report.ok is True
        assert report.executed_features == ["base"]
        assert [c[0] for c in session.calls] == [
            "ensure_ready", "open_new_part", "create_sketch", "add_sketch_entity", "extrude_feature", "analyze_model"
        ]

    asyncio.run(scenario())


def test_executor_rejects_unlowered_operations():
    async def scenario():
        session = FakeSession()
        executor = SolidPilotOperationExecutor(session)
        op = Operation("holes", "part.hole", "extrude_feature", {"hole_intent": "M8"}, phase="lower")
        with pytest.raises(SolidPilotExecutionError, match="UNLOWERED_OPERATION"):
            await executor.call(op)
        assert session.calls == []

    asyncio.run(scenario())


def test_catalog_keeps_discovered_tools_as_candidates():
    async def scenario():
        class Tool:
            name = "create_rib"
            inputSchema = {"type": "object"}

        class Session:
            async def list_tools(self):
                return type("Page", (), {"tools": [Tool()]})()

        catalog = SolidPilotCapabilityCatalogV1()
        records = await catalog.discover_from_session(Session())
        found = catalog.get("solidpilot.tool.create_rib")
        assert found is not None
        assert found.status == "candidate"
        assert any(item.status == "proven" for item in records)

    asyncio.run(scenario())


def test_sync_executor_remains_an_injected_boundary():
    calls = []

    class E:
        def execute(self, operation):
            calls.append(operation.tool)
            return {"ok": True}

    plan = type("Plan", (), {"features": [type("CF", (), {"feature_id": "x", "operations": [Operation("x", "c", "t", {})]})()]})()
    report = CompiledPlanExecutor(E()).execute(plan)
    assert report.ok is True
    assert calls == ["t"]
