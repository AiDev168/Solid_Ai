from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any

from .aidesigner_assets import lower_boss, lower_fillet
from .motor_bracket_plan_v1 import MOTOR_BRACKET_V1, FeatureSpec, MotorBracketPlanV1, ordered_features
from .support_reference_v1 import (
    SketchFrame,
    frame_from_sketch_result,
    resolve_extrude_end_face,
    resolve_extrusion_boundary_edges,
)
from .reference_resolution_v1 import edge_evidence, face_evidence


@dataclass(frozen=True)
class RuntimeEvidence:
    feature_id: str
    tool: str
    state_version: int | None
    result: Any


@dataclass
class RuntimeReport:
    ok: bool = False
    feature_status: dict[str, str] = field(default_factory=dict)
    evidence: list[RuntimeEvidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse(result: Any) -> Any:
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
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                if text.startswith("Error calling tool"):
                    raise RuntimeError(text)
    return result


async def _call(session: Any, tool: str, arguments: dict[str, Any]) -> Any:
    return _parse(await session.call_tool(tool, arguments))


def _state(result: Any) -> int | None:
    return int(result["state_version"]) if isinstance(result, dict) and isinstance(result.get("state_version"), int) else None


def _check(result: Any, tool: str) -> None:
    if not isinstance(result, dict) or result.get("status") not in {"READY", "COMPLETED"}:
        raise RuntimeError(f"{tool}: unexpected result {result!r}")


def _support_matches(binding: dict[str, Any], sketch: dict[str, Any]) -> bool:
    geom = sketch.get("result_geometry")
    frame = geom.get("frame") if isinstance(geom, dict) else None
    if not isinstance(frame, dict):
        return False
    origin = frame.get("origin")
    xdir = frame.get("xdir")
    ydir = frame.get("ydir")
    if not all(isinstance(v, list) and len(v) >= 3 for v in (origin, xdir, ydir)):
        return False
    bpoint = binding.get("evidence", {}).get("point")
    bnormal = binding.get("evidence", {}).get("normal")
    if not (isinstance(bpoint, list) and isinstance(bnormal, list) and len(bpoint) >= 3 and len(bnormal) >= 3):
        return False

    def unit(v):
        n = math.sqrt(sum(float(x) ** 2 for x in v[:3]))
        return [float(x) / n for x in v[:3]] if n > 1e-12 else None

    xx, yy, nn = unit(xdir), unit(ydir), unit(bnormal)
    if xx is None or yy is None or nn is None:
        return False
    sn = unit([
        xx[1] * yy[2] - xx[2] * yy[1],
        xx[2] * yy[0] - xx[0] * yy[2],
        xx[0] * yy[1] - xx[1] * yy[0],
    ])
    if sn is None or abs(sum(sn[i] * nn[i] for i in range(3))) < 1.0 - 1e-6:
        return False

    delta = [float(origin[i]) - float(bpoint[i]) for i in range(3)]
    return abs(sum(delta[i] * nn[i] for i in range(3))) <= 1e-6


class MotorBracketRuntimeV2:
    def __init__(self, session: Any, plan: MotorBracketPlanV1 = MOTOR_BRACKET_V1):
        self.session = session
        self.plan = plan
        self.report = RuntimeReport()
        self.frames: dict[str, SketchFrame] = {}
        self.depths: dict[str, float] = {}

    async def _record(self, feature_id: str, tool: str, result: Any) -> Any:
        _check(result, tool)
        self.report.evidence.append(RuntimeEvidence(feature_id, tool, _state(result), result))
        return result

    async def _profile(self, feature: FeatureSpec) -> None:
        p = feature.params
        result = await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(self.session, "create_sketch", {"plane": p["plane"]}),
        )
        self.frames[feature.feature_id] = frame_from_sketch_result(result)
        hw, hh = p["width_m"] / 2.0, p["height_m"] / 2.0
        await self._record(
            feature.feature_id,
            "add_sketch_entity",
            await _call(
                self.session,
                "add_sketch_entity",
                {"entity_type": "rectangle", "x1": -hw, "y1": -hh, "x2": hw, "y2": hh},
            ),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _boss(self, feature: FeatureSpec) -> None:
        depth = float(feature.params["depth_m"])
        call = lower_boss(depth_m=depth)
        await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
        self.depths[feature.feature_id] = depth

        # The semantic feature "base" derives its support frame from the
        # producing sketch. Feature-frame references must never require the
        # backend to invent a new/world-aligned coordinate system.
        for dependency in feature.depends_on:
            if dependency in self.frames:
                self.frames[feature.feature_id] = self.frames[dependency]
                break

        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _resolve_support_face(self, feature: FeatureSpec, producer_id: str) -> dict[str, Any]:
        frame = self.frames[producer_id]
        depth = self.depths[producer_id]
        analysis = await _call(self.session, "analyze_model", {"analysis_type": "faces"})
        evidence = face_evidence(analysis, int(analysis["state_version"]))
        return resolve_extrude_end_face(
            evidence.candidates,
            frame=frame,
            depth_m=depth,
            reference_id=str(feature.params["support_ref"]["reference_id"]),
            state_version=evidence.state_version,
        )

    async def _sketch_on_support(self, feature: FeatureSpec):
        support = feature.params["support_ref"]
        producer = str(support["feature_id"])
        binding = await self._resolve_support_face(feature, producer)
        sketch = await self._record(
            feature.feature_id,
            "create_sketch",
            await _call(
                self.session,
                "create_sketch",
                {"on_face": True, "face_index": binding["backend_index"]},
            ),
        )
        if not _support_matches(binding, sketch):
            raise RuntimeError(
                "STALE_FACE_SELECTOR: measured sketch support disagrees with feature-frame support face"
            )
        self.frames[feature.feature_id] = frame_from_sketch_result(sketch)
        return binding, sketch

    async def _holes(self, feature: FeatureSpec) -> None:
        p = feature.params
        await self._sketch_on_support(feature)
        for cx, cy in p["centers_m"]:
            await self._record(
                feature.feature_id,
                "add_sketch_entity",
                await _call(
                    self.session,
                    "add_sketch_entity",
                    {"entity_type": "circle", "cx": cx, "cy": cy, "radius": p["diameter_m"] / 2.0},
                ),
            )
        await self._record(
            feature.feature_id,
            "extrude_feature",
            await _call(
                self.session,
                "extrude_feature",
                {
                    "depth": self.depths["base"],
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
        await self._sketch_on_support(feature)
        hw = p["width_m"] / 2.0
        await self._record(
            feature.feature_id,
            "add_sketch_entity",
            await _call(
                self.session,
                "add_sketch_entity",
                {"entity_type": "rectangle", "x1": p["x_center_m"] - hw, "y1": -0.025, "x2": p["x_center_m"] + hw, "y2": 0.025},
            ),
        )
        call = lower_boss(depth_m=p["height_m"])
        await self._record(feature.feature_id, call["tool"], await _call(self.session, call["tool"], call["params"]))
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def _fillet(self, feature: FeatureSpec) -> None:
        p = feature.params
        frame = self.frames["base"]
        analysis = await _call(self.session, "analyze_model", {"analysis_type": "edges"})
        evidence = edge_evidence(analysis, int(analysis["state_version"]))
        bounds = tuple(float(v) for v in p["selection"]["reference"]["criteria"]["bounds_uv_m"])
        edges = resolve_extrusion_boundary_edges(
            evidence.candidates,
            frame=frame,
            bounds_uv=bounds,
            reference_id=p["selection"]["reference"]["reference_id"],
            state_version=evidence.state_version,
        )
        indices = [int(item["backend_index"]) for item in edges]
        call = lower_fillet(
            radius_m=float(p["radius_m"]),
            edge_indices=json.dumps(indices, separators=(",", ":")),
        )
        await self._record(
            feature.feature_id,
            call["tool"],
            await _call(self.session, call["tool"], call["params"]),
        )
        self.report.feature_status[feature.feature_id] = "COMPLETED"

    async def run(self) -> RuntimeReport:
        try:
            ready = await _call(self.session, "ensure_ready", {})
            _check(ready, "ensure_ready")
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
                    raise RuntimeError(f"unsupported feature kind: {feature.kind}")
            final = await _call(self.session, "analyze_model", {"analysis_type": "geometry"})
            _check(final, "analyze_model")
            self.report.ok = True
        except Exception as exc:
            self.report.errors.append(str(exc))
        return self.report
