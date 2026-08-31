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


def _decode_json_text(text: str, tool: str) -> Mapping[str, Any]:
    text = text.strip()
    if not text:
        raise QualificationPreflightError(f"empty MCP result for {tool}")
    try:
        payload = json.loads(text)
        if isinstance(payload, Mapping):
            return payload
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for marker in ("{", "["):
        start = text.find(marker)
        while start >= 0:
            try:
                payload, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                start = text.find(marker, start + 1)
                continue
            if isinstance(payload, Mapping):
                if isinstance(payload.get("ok"), bool):
                    return payload
                # MCP error wrappers sometimes carry a nested error object.
                nested = payload.get("error")
                if isinstance(nested, Mapping):
                    return {
                        "ok": False,
                        "status": "FAILED",
                        "tool": tool,
                        **nested,
                    }
                return payload
            break
    raise QualificationPreflightError(f"invalid MCP result for {tool}: {text[:500]}")


def _extract_payload(result: Any, tool: str) -> Mapping[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, Mapping):
        value = structured.get("result")
        if isinstance(value, str):
            return _decode_json_text(value, tool)
        if isinstance(value, Mapping):
            return value

    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", "")
        if text:
            return _decode_json_text(text, tool)

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
            if result.get("status") not in {"READY", "COMPLETED"} or result.get("ok") is False:
                return {
                    "ok": False,
                    "verified": False,
                    "scenario_id": scenario.scenario_id,
                    "capability_id": scenario.capability_id,
                    "state_version": state_version,
                    "evidence": evidence,
                    "error": result.get("message") or result.get("error") or f"operation failed: {operation['tool']}",
                    "tool": result.get("tool", operation["tool"]),
                    "code": result.get("code"),
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
