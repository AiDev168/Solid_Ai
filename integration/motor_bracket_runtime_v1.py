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
from .recovery_assets import (
    RecoveryAssets,
    TopologyRecoveryEvidence,
    make_anchor,
    normalize_runtime_failure,
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


def _edges(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
        raise RuntimeError("analyze_model returned no data")
    raw = result["data"].get("edges")
    if not isinstance(raw, list):
        raise RuntimeError("analyze_model returned no edges")
    return [
        edge for edge in raw
        if isinstance(edge, dict) and isinstance(edge.get("i"), int)
    ]


def _dist2(edge: dict[str, Any], target: tuple[float, float, float]) -> float:
    mid = edge.get("mid")
    if not isinstance(mid, list) or len(mid) < 3:
        return float("inf")
    return sum((float(mid[i]) - target[i]) ** 2 for i in range(3))


def _outer_vertical_edge(edges: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for edge in edges:
        start, end = edge.get("start"), edge.get("end")
        if not (
            isinstance(start, list)
            and isinstance(end, list)
            and len(start) >= 3
            and len(end) >= 3
        ):
            continue
        dx = abs(float(end[0]) - float(start[0]))
        dy = abs(float(end[1]) - float(start[1]))
        dz = abs(float(end[2]) - float(start[2]))
        if dz > 0.02 and dx < 1e-8 and dy < 1e-8:
            candidates.append(edge)
    if not candidates:
        raise RuntimeError("no outer vertical edge candidate found")
    return min(candidates, key=lambda edge: _dist2(edge, (0.0, 0.04, 0.04)))


class MotorBracketRuntimeV1:
    def __init__(
        self,
        session: RuntimeSession,
        plan: MotorBracketPlanV1 = MOTOR_BRACKET_V1,
    ):
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
            await _call(
                self.session,
                "add_sketch_entity",
                {
                    "entity_type": "rectangle",
                    "x1": -half_w,
                    "y1": -half_h,
                    "x2": half_w,
                    "y2": half_h,
                },
            ),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _boss(self, feature: FeatureSpec) -> None:
        call = lower_boss(depth_m=float(feature.params["depth_m"]))
        await self._record(
            feature.feature_id,
            call["tool"],
            await _call(self.session, call["tool"], call["params"]),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _holes(self, feature: FeatureSpec) -> None:
        p = feature.params
        await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(
                self.session,
                "create_sketch",
                {"on_face": True, "face_x": 0.0, "face_y": 0.005, "face_z": 0.04},
            ),
        )
        for cx, cy in p["centers_m"]:
            await self._record(
                feature.feature_id,
                "add_sketch_entity",
                await _call(
                    self.session,
                    "add_sketch_entity",
                    {
                        "entity_type": "circle",
                        "cx": cx,
                        "cy": cy,
                        "radius": p["diameter_m"] / 2.0,
                    },
                ),
            )
        await self._record(
            feature.feature_id,
            "extrude_feature",
            await _call(
                self.session,
                "extrude_feature",
                {
                    "depth": 0.01,
                    "feature_type": "cut",
                    "reverse": False,
                    "through": True,
                    "up_to_face_index": -1,
                    "mid_plane": False,
                },
            ),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _rib(self, feature: FeatureSpec) -> None:
        p = feature.params
        await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(
                self.session,
                "create_sketch",
                {"on_face": True, "face_x": p["x_center_m"], "face_y": 0.005, "face_z": 0.005},
            ),
        )
        half_width = p["width_m"] / 2.0
        await self._record(
            feature.feature_id,
            "add_sketch_entity",
            await _call(
                self.session,
                "add_sketch_entity",
                {
                    "entity_type": "rectangle",
                    "x1": p["x_center_m"] - half_width,
                    "y1": -0.025,
                    "x2": p["x_center_m"] + half_width,
                    "y2": 0.025,
                },
            ),
        )
        call = lower_boss(depth_m=float(p["height_m"]))
        await self._record(
            feature.feature_id,
            call["tool"],
            await _call(self.session, call["tool"], call["params"]),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _fillet(self, feature: FeatureSpec) -> None:
        before = await _call(self.session, "analyze_model", {"analysis_type": "edges"})
        edges_before = _edges(before)
        candidate = _outer_vertical_edge(edges_before)
        anchor = make_anchor(
            {"kind": "edge", **candidate, "backend_index": int(candidate["i"])},
            source_state_version=int(before.get("state_version", 0)),
        )
        initial = None
        try:
            call = lower_fillet(
                radius_m=float(feature.params["radius_m"]),
                edge_indices=json.dumps([anchor.backend_index]),
            )
            initial = await _call(self.session, call["tool"], call["params"])
            await self._record(feature.feature_id, call["tool"], initial)
            self.report.feature_status[feature.feature_id] = "COMPLETED"
            return
        except RuntimeError as exc:
            failure = normalize_runtime_failure(exc)

        fresh = await _call(self.session, "analyze_model", {"analysis_type": "edges"})
        fresh_edges = _edges(fresh)
        evidence = TopologyRecoveryEvidence(
            edge_anchor=anchor,
            edge_candidates=[
                {"kind": "edge", **edge, "backend_index": int(edge["i"])}
                for edge in fresh_edges
            ],
            target_edge_state_version=int(fresh.get("state_version", 0)),
        )
        diagnosis, recovery = self.recovery.controller.diagnose_and_recover(
            code=failure.code,
            message=failure.message,
            evidence=evidence,
            max_attempts=1,
        )
        self.report.recovery.append(
            {"diagnosis": diagnosis, "recovery": recovery}
        )
        if recovery is None or not recovery.recovered:
            raise RuntimeError(
                f"{failure.code}: topology recovery did not produce a binding"
            )
        binding = recovery.attempts[-1].result.edge_binding
        if binding is None:
            raise RuntimeError("topology recovery completed without edge binding")
        call = lower_fillet(
            radius_m=float(feature.params["radius_m"]),
            edge_indices=json.dumps([binding.backend_index]),
        )
        result = await _call(self.session, call["tool"], call["params"])
        await self._record(feature.feature_id, call["tool"], result)
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
                    raise RuntimeError(
                        f"unsupported semantic feature kind: {feature.kind}"
                    )
            final = await _call(
                self.session, "analyze_model", {"analysis_type": "geometry"}
            )
            _ensure_status(final, "analyze_model")
            self.report.ok = True
        except Exception as exc:
            self.report.ok = False
            self.report.errors.append(str(exc))
        return self.report


__all__ = [
    "ExecutionEvidence",
    "MotorBracketRuntimeReport",
    "MotorBracketRuntimeV1",
]
