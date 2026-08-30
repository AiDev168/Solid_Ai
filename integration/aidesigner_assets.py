"""Evidence-backed CAD capability assets ported from Ai_Designer."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    CapabilitySpec("part.open_new", "solidpilot", "open_new_part", "proven", "SolidPilot tool", "COMPLETED + verified", "Ai_Designer proven runtime evidence"),
    CapabilitySpec("part.create_sketch", "solidpilot", "create_sketch", "proven", "plane/on_face", "COMPLETED + geometry frame", "Ai_Designer proven runtime evidence"),
    CapabilitySpec("sketch.circle", "solidpilot", "add_sketch_entity", "proven", "circle; meters", "result_geometry.kind=arc/circle", "Ai_Designer proven runtime evidence"),
    CapabilitySpec("part.extrude_boss", "solidpilot", "extrude_feature", "proven", "boss; depth meters", "COMPLETED + body geometry", "Ai_Designer proven runtime evidence"),
    CapabilitySpec("model.analyze_geometry", "solidpilot", "analyze_model", "proven", "analysis_type=geometry", "geometry evidence present", "Ai_Designer proven runtime evidence"),
    CapabilitySpec("part.hole", "solidpilot", "extrude_feature", "proven", "circle sketch + cut/through", "COMPLETED; body preserved; volume decreases", "Ai_Designer SOLIDPILOT HOLE+FILLET LIVE V1.2"),
    CapabilitySpec("edge.fillet", "solidpilot", "add_edge_feature", "proven", "fillet + edge selector", "COMPLETED; topology changes", "Ai_Designer SOLIDPILOT HOLE+FILLET LIVE V1.2", "Prefer edge_indices from analyze_model over coordinate selection."),
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
    if diameter_m <= 0 or depth_m <= 0:
        raise ValueError("diameter_m and depth_m must be > 0")
    return [
        {"tool": "create_sketch", "params": {"plane": plane, "on_face": on_face}},
        {"tool": "add_sketch_entity", "params": {"entity_type": "circle", "cx": cx, "cy": cy, "radius": diameter_m / 2.0, "construction": False}},
        {"tool": "extrude_feature", "params": {"depth": depth_m, "feature_type": "cut", "reverse": False, "through": through, "up_to_face_index": -1, "mid_plane": False}},
    ]


def lower_fillet(*, radius_m: float, edge_indices: str | None = None,
                 ex: float | None = None, ey: float | None = None, ez: float | None = None) -> dict[str, Any]:
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
    return {"tool": "extrude_feature", "params": {"depth": depth_m, "feature_type": "boss", "reverse": reverse, "through": through, "up_to_face_index": up_to_face_index, "mid_plane": mid_plane}}


def describe_capabilities() -> str:
    lines = ["Ai_Designer proven CAD assets bound to SolidPilot:"]
    lines.extend(f"- {s.capability_id} -> {s.tool} [{s.status}]" for s in CAPABILITIES)
    return "\n".join(lines)


def select_fillet_edges(edge_analysis: dict[str, Any], *, z_min: float | None = None, z_max: float | None = None) -> str:
    """Select runtime edge indices from analyze_model output instead of guessing coordinates.

    Expected edge_analysis is a dict containing ``edges``. Each edge may expose
    ``index`` and optional coordinate/endpoint metadata. Selection remains conservative:
    only edges with an explicit integer index are returned.
    """
    edges = edge_analysis.get("edges", [])
    selected: list[int] = []
    for edge in edges:
        if not isinstance(edge, dict) or not isinstance(edge.get("index"), int):
            continue
        if z_min is not None or z_max is not None:
            z_values: list[float] = []
            for key in ("z", "z1", "z2", "center_z"):
                value = edge.get(key)
                if isinstance(value, (int, float)):
                    z_values.append(float(value))
            if z_values:
                if z_min is not None and max(z_values) < z_min:
                    continue
                if z_max is not None and min(z_values) > z_max:
                    continue
        selected.append(edge["index"])
    return str(selected)
