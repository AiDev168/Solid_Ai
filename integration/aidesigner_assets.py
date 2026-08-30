"""Evidence-backed CAD capability assets ported from Ai_Designer.

This module intentionally contains only the reusable capability metadata and lowering
logic. It does not import the previous Ai_Designer planner, agent swarm, CAD-IR, or LLM
stack. Source reference: AiDev168/Ai_Designer, src/ai_designer/capabilities/registry.py
and lowering.py (main, inspected 2026-08-30).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    backend: str
    tool: str
    status: str
    input_contract: str
    verification: str
    evidence: str
    notes: str = ""


CAPABILITIES: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("part.open_new", "solidpilot", "open_new_part", "proven",
                   "SolidPilot tool", "COMPLETED + verified", "Ai_Designer SOLIDPILOT-REUSABLE-RUNTIME evidence"),
    CapabilitySpec("part.create_sketch", "solidpilot", "create_sketch", "proven",
                   "plane/on_face", "COMPLETED + geometry frame", "Ai_Designer SOLIDPILOT-REUSABLE-RUNTIME evidence"),
    CapabilitySpec("sketch.circle", "solidpilot", "add_sketch_entity", "proven",
                   "entity_type=circle; meters", "result_geometry.kind=arc/circle", "Ai_Designer SOLIDPILOT-REUSABLE-RUNTIME evidence"),
    CapabilitySpec("part.extrude_boss", "solidpilot", "extrude_feature", "proven",
                   "feature_type=boss; depth meters", "COMPLETED + body geometry", "Ai_Designer SOLIDPILOT-REUSABLE-RUNTIME evidence"),
    CapabilitySpec("model.analyze_geometry", "solidpilot", "analyze_model", "proven",
                   "analysis_type=geometry", "geometry evidence present", "Ai_Designer SOLIDPILOT-REUSABLE-RUNTIME evidence"),
    CapabilitySpec("part.hole", "solidpilot", "extrude_feature", "proven",
                   "circle sketch + cut/through", "COMPLETED; body preserved; volume decreases", "Ai_Designer SOLIDPILOT HOLE+FILLET LIVE V1.2"),
    CapabilitySpec("edge.fillet", "solidpilot", "add_edge_feature", "proven",
                   "fillet + edge selector", "COMPLETED; topology changes", "Ai_Designer SOLIDPILOT HOLE+FILLET LIVE V1.2",
                   "Prefer edge_indices from analyze_model over coordinate selection."),
)


def get_capability(capability_id: str) -> CapabilitySpec | None:
    return next((item for item in CAPABILITIES if item.capability_id == capability_id), None)


def require_capability(capability_id: str) -> CapabilitySpec:
    spec = get_capability(capability_id)
    if spec is None:
        raise KeyError(f"Unknown capability: {capability_id}")
    return spec


def lower_hole(*, cx: float, cy: float, diameter_m: float, depth_m: float, through: bool = True,
               plane: str = "Front Plane", on_face: bool = False) -> list[dict[str, Any]]:
    """Port of Ai_Designer hole lowering, with explicit optional face placement."""
    if diameter_m <= 0 or depth_m <= 0:
        raise ValueError("diameter_m and depth_m must be > 0")
    return [
        {"tool": "create_sketch", "params": {"plane": plane, "on_face": on_face}},
        {"tool": "add_sketch_entity", "params": {
            "entity_type": "circle", "cx": cx, "cy": cy,
            "radius": diameter_m / 2.0, "construction": False,
        }},
        {"tool": "extrude_feature", "params": {
            "depth": depth_m, "feature_type": "cut", "reverse": False,
            "through": through, "up_to_face_index": -1, "mid_plane": False,
        }},
    ]


def lower_fillet(*, radius_m: float, edge_indices: str | None = None,
                 ex: float | None = None, ey: float | None = None, ez: float | None = None) -> dict[str, Any]:
    """Port of Ai_Designer fillet lowering; coordinates remain a fallback."""
    if radius_m <= 0:
        raise ValueError("radius_m must be > 0")
    params: dict[str, Any] = {"feature_type": "fillet", "radius_or_distance": radius_m}
    if edge_indices is not None:
        params["edge_indices"] = edge_indices
    else:
        if ex is None or ey is None or ez is None:
            raise ValueError("edge_indices or ex/ey/ez is required")
        params.update({"ex": ex, "ey": ey, "ez": ez})
    return {"tool": "add_edge_feature", "params": params}


def lower_boss(*, depth_m: float, reverse: bool = False, through: bool = False,
               up_to_face_index: int = -1, mid_plane: bool = False) -> dict[str, Any]:
    if depth_m <= 0:
        raise ValueError("depth_m must be > 0")
    return {"tool": "extrude_feature", "params": {
        "depth": depth_m, "feature_type": "boss", "reverse": reverse,
        "through": through, "up_to_face_index": up_to_face_index, "mid_plane": mid_plane,
    }}


def describe_capabilities() -> str:
    lines = ["Ai_Designer proven CAD assets bound to SolidPilot:"]
    lines.extend(f"- {s.capability_id} -> {s.tool} [{s.status}]" for s in CAPABILITIES)
    return "\n".join(lines)
