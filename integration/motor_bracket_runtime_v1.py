from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from .aidesigner_assets import lower_boss, lower_fillet
from .motor_bracket_plan_v1 import (
    FeatureSpec,
    MotorBracketPlanV1,
    MOTOR_BRACKET_V1,
    ordered_features,
)
from .recovery_assets import RecoveryAssets, TopologyRecoveryEvidence, make_anchor, normalize_runtime_failure
from .reference_resolution_v1 import (
    ReferenceIntent,
    edge_evidence,
    edge_indices_json,
    face_evidence,
    face_index_json,
    resolve_reference,
)


class RuntimeSession(Protocol):
    async def call_tool(self, name: str, arguments: dict[str, Any]): ...


@dataclass(frozen=True)
class ExecutionEvidence:
    feature_id: str
    tool: str
    state_version: int | None
    result: Any


@dataclass
class MotorBracketRuntimeReport:
    ok: bool
    feature_status: dict[str, str] = field(default_factory=dict)
    evidence: list[ExecutionEvidence] = field(default_factory=list)
    recovery: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_result(result: Any) -> Any:
    if getattr(result, "isError", False):
        raise RuntimeError(str(result))
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and "result" in structured:
        value = structured["result"]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    for item in getattr(result, "content", None) or []:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            if text.startswith("Error calling tool"):
                raise RuntimeError(text)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return result


async def _call(session: RuntimeSession, tool: str, arguments: dict[str, Any]) -> Any:
    return _parse_result(await session.call_tool(tool, arguments))


def _state_version(result: Any) -> int | None:
    if not isinstance(result, dict):
        return None
    value = result.get("state_version", result.get("stateVersion"))
    return int(value) if isinstance(value, int) else None


def _ensure_status(result: Any, tool: str) -> None:
    if not isinstance(result, dict):
        raise RuntimeError(f"{tool}: unexpected result type")
    if result.get("status") not in {"COMPLETED", "READY"}:
        raise RuntimeError(f"{tool}: unexpected status {result.get('status')!r}: {result}")


class MotorBracketRuntimeV1:
    """Execute a semantic multi-feature plan through the live SolidPilot boundary."""

    def __init__(self, session: RuntimeSession, plan: MotorBracketPlanV1 = MOTOR_BRACKET_V1):
        self.session = session
        self.plan = plan
        self.recovery = RecoveryAssets()
        self.report = MotorBracketRuntimeReport(False)

    async def _record(self, feature_id: str, tool: str, result: Any) -> Any:
        _ensure_status(result, tool)
        self.report.evidence.append(
            ExecutionEvidence(feature_id, tool, _state_version(result), result)
        )
        return result

    async def _resolve_top_face(self, reference: Mapping[str, Any]):
        analysis = await _call(self.session, "analyze_model", {"analysis_type": "faces"})
        evidence = face_evidence(analysis, int(analysis.get("state_version", 0)))
        intent = ReferenceIntent(
            reference_id=str(reference["reference_id"]),
            kind="face",
            role=str(reference["role"]),
            feature_id=str(reference.get("feature_id", "")),
        )
        return resolve_reference(intent, evidence)

    async def _resolve_outer_edge(self, *, reference_id: str) -> Any:
        analysis = await _call(self.session, "analyze_model", {"analysis_type": "edges"})
        evidence = edge_evidence(analysis, int(analysis.get("state_version", 0)))
        intent = ReferenceIntent(
            reference_id=reference_id,
            kind="edge",
            role="outer_vertical",
            feature_id="",
            target_xyz=(0.0, 0.0, 0.0),
        )
        return resolve_reference(intent, evidence), analysis

    async def _profile(self, feature: FeatureSpec) -> None:
        p = feature.params
        await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(self.session, "create_sketch", {"plane": p["plane"]}),
        )
        half_w, half_h = p["width_m"] / 2.0, p["height_m"] / 2.0
        await self._record(
            feature.feature_id,
            "add_sketch_entity",
            await _call(self.session, "add_sketch_entity", {
                "entity_type": "rectangle",
                "x1": -half_w,
                "y1": -half_h,
                "x2": half_w,
                "y2": half_h,
            }),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _boss(self, feature: FeatureSpec) -> None:
        call = lower_boss(depth_m=float(feature.params["depth_m"]))
        await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _holes(self, feature: FeatureSpec) -> None:
        p = feature.params
        binding = await self._resolve_top_face(p["support_ref"])
        await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(self.session, "create_sketch", {"on_face": True, "face_index": face_index_json(binding)}),
        )
        for cx, cy in p["centers_m"]:
            await self._record(
                feature.feature_id,
                "add_sketch_entity",
                await _call(self.session, "add_sketch_entity", {
                    "entity_type": "circle",
                    "cx": cx,
                    "cy": cy,
                    "radius": p["diameter_m"] / 2.0,
                }),
            )
        await self._record(
            feature.feature_id,
            "extrude_feature",
            await _call(self.session, "extrude_feature", {
                "depth": 0.01,
                "feature_type": "cut",
                "reverse": False,
                "through": True,
                "up_to_face_index": -1,
                "mid_plane": False,
            }),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _rib(self, feature: FeatureSpec) -> None:
        p = feature.params
        binding = await self._resolve_top_face(p["support_ref"])
        await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(self.session, "create_sketch", {"on_face": True, "face_index": face_index_json(binding)}),
        )
        half_width = p["width_m"] / 2.0
        await self._record(
            feature.feature_id,
            "add_sketch_entity",
            await _call(self.session, "add_sketch_entity", {
                "entity_type": "rectangle",
                "x1": p["x_center_m"] - half_width,
                "y1": -0.025,
                "x2": p["x_center_m"] + half_width,
                "y2": 0.025,
            }),
        )
        call = lower_boss(depth_m=float(p["height_m"]))
        await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _fillet(self, feature: FeatureSpec) -> None:
        binding, before = await self._resolve_outer_edge(reference_id="outer_vertical_edge_for_fillet")
        try:
            call = lower_fillet(
                radius_m=float(feature.params["radius_m"]),
                edge_indices=edge_indices_json(binding),
            )
            await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
            self.report.feature_status[feature.feature_id] = "COMPLETED"
            return
        except RuntimeError as exc:
            failure = normalize_runtime_failure(exc)

        fresh = await _call(self.session, "analyze_model", {"analysis_type": "edges"})
        fresh_evidence = edge_evidence(fresh, int(fresh.get("state_version", 0)))
        anchor = make_anchor({"kind": "edge", **binding.evidence, "backend_index": binding.backend_index}, source_state_version=binding.state_version)
        diagnosis, recovery = self.recovery.controller.diagnose_and_recover(
            code=failure.code,
            message=failure.message,
            evidence=TopologyRecoveryEvidence(
                edge_anchor=anchor,
                edge_candidates=fresh_evidence.candidates,
                target_edge_state_version=fresh_evidence.state_version,
            ),
            max_attempts=1,
        )
        self.report.recovery.append({"diagnosis": diagnosis, "recovery": recovery})
        if recovery is None or not recovery.recovered:
            raise RuntimeError(f"{failure.code}: topology recovery did not recover the fillet reference")
        rebound = recovery.attempts[-1].result.edge_binding
        if rebound is None:
            raise RuntimeError("topology recovery returned no edge binding")
        call = lower_fillet(
            radius_m=float(feature.params["radius_m"]),
            edge_indices=json.dumps([rebound.backend_index], separators=(",", ":")),
        )
        await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def run(self) -> MotorBracketRuntimeReport:
        try:
            ready = await _call(self.session, "ensure_ready", {})
            _ensure_status(ready, "ensure_ready")
            await _call(self.session, "open_new_part", {})
            for feature in ordered_features(self.plan):
                if feature.kind == "profile":
                    await self._profile(feature)
                elif feature.kind == "extrude_boss":
                    await self._boss(feature)
                elif feature.kind == "hole_pattern":
                    await self._holes(feature)
                elif feature.kind == "rib":
                    await self._rib(feature)
                elif feature.kind == "fillet":
                    await self._fillet(feature)
                else:
                    raise RuntimeError(f"unsupported semantic feature kind: {feature.kind}")
            final = await _call(self.session, "analyze_model", {"analysis_type": "geometry"})
            _ensure_status(final, "analyze_model")
            self.report.ok = True
        except Exception as exc:
            self.report.ok = False
            self.report.errors.append(str(exc))
        return self.report


__all__ = ["ExecutionEvidence", "MotorBracketRuntimeReport", "MotorBracketRuntimeV1"]
