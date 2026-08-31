from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .capability_qualification_v1 import QualificationScenario


class QualificationPreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveQualificationEvidence:
    scenario_id: str
    capability_id: str
    status: str
    state_version: int | None = None
    evidence: Mapping[str, Any] | None = None
    error: str | None = None


def _extract_payload(result: Any, tool: str) -> Mapping[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, Mapping):
        value = structured.get("result")
        if isinstance(value, str):
            payload = json.loads(value)
            if isinstance(payload, Mapping):
                return payload
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", "")
        if text:
            payload = json.loads(text)
            if isinstance(payload, Mapping):
                return payload
    raise QualificationPreflightError(f"invalid MCP result for {tool}")


class LiveQualificationExecutorV1:
    """Execute an existing qualification scenario through MCP/SolidPilot.

    This layer collects live evidence only. Promotion remains a separate
    policy decision and therefore cannot happen accidentally during a run.
    """

    def __init__(self, session: Any) -> None:
        self.session = session

    async def _call(self, tool: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        result = await self.session.call_tool(tool, arguments=dict(params))
        return _extract_payload(result, tool)

    @staticmethod
    def _validate_shape(scenario: QualificationScenario) -> None:
        if not scenario.operations:
            raise QualificationPreflightError("scenario has no operations")
        for operation in scenario.operations:
            if not isinstance(operation, Mapping):
                raise QualificationPreflightError("scenario operation must be a mapping")
            tool = operation.get("tool")
            params = operation.get("params")
            if not isinstance(tool, str) or not tool:
                raise QualificationPreflightError("operation.tool is required")
            if not isinstance(params, Mapping):
                raise QualificationPreflightError(f"{tool}: operation.params must be a mapping")

    async def execute(self, scenario: QualificationScenario) -> Mapping[str, Any]:
        self._validate_shape(scenario)
        ready = await self._call("ensure_ready", {})
        if ready.get("status") not in {"READY", "COMPLETED"}:
            raise QualificationPreflightError(f"SolidPilot not ready: {ready}")

        opened = await self._call("open_new_part", {})
        evidence: list[dict[str, Any]] = [{"phase": "open_new_part", "result": opened}]
        state_version = opened.get("state_version")

        for index, operation in enumerate(scenario.operations, start=1):
            result = await self._call(str(operation["tool"]), operation["params"])
            state_version = result.get("state_version", state_version)
            evidence.append({"step": index, "tool": operation["tool"], "result": result})
            if result.get("status") not in {"READY", "COMPLETED"}:
                return {
                    "ok": False,
                    "verified": False,
                    "scenario_id": scenario.scenario_id,
                    "capability_id": scenario.capability_id,
                    "state_version": state_version,
                    "evidence": evidence,
                    "error": f"operation failed: {operation['tool']}",
                }

        geometry = await self._call("analyze_model", {"analysis_type": "geometry"})
        evidence.append({"phase": "verification", "tool": "analyze_model", "result": geometry})
        verified = geometry.get("status") == "COMPLETED" and bool(geometry.get("data"))
        return {
            "ok": verified,
            "verified": verified,
            "scenario_id": scenario.scenario_id,
            "capability_id": scenario.capability_id,
            "state_version": geometry.get("state_version", state_version),
            "evidence": evidence,
        }


__all__ = ["LiveQualificationEvidence", "LiveQualificationExecutorV1", "QualificationPreflightError"]
