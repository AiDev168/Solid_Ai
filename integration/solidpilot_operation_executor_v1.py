from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from .feature_graph_compiler_v1 import CompiledPlan, Operation


class SolidPilotExecutionError(RuntimeError):
    """Raised when a compiled operation cannot be safely executed."""


class AsyncToolSession(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True)
class OperationResult:
    feature_id: str
    capability_id: str
    tool: str
    state_version: int | None
    result: Any


@dataclass
class SolidPilotExecutionReport:
    ok: bool = False
    prepared: bool = False
    executed_features: list[str] = field(default_factory=list)
    operations: list[OperationResult] = field(default_factory=list)
    final_evidence: Any = None
    errors: list[str] = field(default_factory=list)


def parse_solidpilot_result(response: Any) -> Any:
    if getattr(response, "isError", False):
        raise SolidPilotExecutionError(str(response))
    structured = getattr(response, "structuredContent", None)
    if isinstance(structured, Mapping) and "result" in structured:
        value = structured["result"]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    for item in getattr(response, "content", ()) or ():
        text = getattr(item, "text", None)
        if isinstance(text, str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return response


class SolidPilotOperationExecutor:
    """Execute compiled operations through the real SolidPilot MCP session.

    This adapter deliberately contains no LLM reasoning and no semantic
    feature selection. The compiler decides what may execute; reference and
    recovery layers remain responsible for resolving semantic selectors.
    """

    def __init__(self, session: AsyncToolSession, *, auto_prepare: bool = True):
        self.session = session
        self.auto_prepare = auto_prepare
        self.report = SolidPilotExecutionReport()

    async def call(self, operation: Operation) -> OperationResult:
        if operation.phase != "execute":
            raise SolidPilotExecutionError(
                f"UNLOWERED_OPERATION: {operation.feature_id}/{operation.tool} has phase={operation.phase}"
            )
        response = await self.session.call_tool(operation.tool, dict(operation.params))
        result = parse_solidpilot_result(response)
        if not isinstance(result, Mapping):
            raise SolidPilotExecutionError(
                f"{operation.tool}: expected structured result, got {type(result).__name__}"
            )
        status = result.get("status")
        if result.get("ok") is False or status not in {"READY", "COMPLETED"}:
            raise SolidPilotExecutionError(
                f"{operation.tool}: backend rejected operation: {result}"
            )
        state_version = result.get("state_version")
        return OperationResult(
            feature_id=operation.feature_id,
            capability_id=operation.capability_id,
            tool=operation.tool,
            state_version=state_version if isinstance(state_version, int) else None,
            result=result,
        )

    async def prepare(self) -> None:
        ready = parse_solidpilot_result(
            await self.session.call_tool("ensure_ready", {})
        )
        if not isinstance(ready, Mapping) or ready.get("status") != "READY":
            raise SolidPilotExecutionError(f"ensure_ready failed: {ready}")
        opened = parse_solidpilot_result(
            await self.session.call_tool("open_new_part", {})
        )
        if not isinstance(opened, Mapping) or opened.get("status") != "COMPLETED":
            raise SolidPilotExecutionError(f"open_new_part failed: {opened}")
        self.report.prepared = True

    async def execute_plan(self, plan: CompiledPlan) -> SolidPilotExecutionReport:
        try:
            if self.auto_prepare and not self.report.prepared:
                await self.prepare()
            for feature in plan.features:
                for operation in feature.operations:
                    outcome = await self.call(operation)
                    self.report.operations.append(outcome)
                self.report.executed_features.append(feature.feature_id)
            evidence = parse_solidpilot_result(
                await self.session.call_tool("analyze_model", {"analysis_type": "geometry"})
            )
            if not isinstance(evidence, Mapping) or evidence.get("status") != "COMPLETED":
                raise SolidPilotExecutionError(f"final geometry verification failed: {evidence}")
            self.report.final_evidence = evidence
            self.report.ok = True
        except Exception as exc:
            self.report.errors.append(str(exc))
        return self.report


__all__ = [
    "OperationResult",
    "SolidPilotExecutionError",
    "SolidPilotExecutionReport",
    "SolidPilotOperationExecutor",
    "parse_solidpilot_result",
]
