from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


ALLOWED_FEATURE_KINDS = frozenset({
    "profile",
    "extrude_boss",
    "revolve",
    "revolve_cut",
    "hole_pattern",
    "rib",
    "fillet",
    "chamfer",
    "pattern",
})


class FeatureGraphValidationError(ValueError):
    pass


@dataclass(frozen=True)
class FeatureNode:
    feature_id: str
    kind: str
    depends_on: tuple[str, ...]
    params: Mapping[str, Any]


@dataclass(frozen=True)
class FeatureGraph:
    schema: str
    part_id: str
    design_intent: str
    units: str
    features: tuple[FeatureNode, ...]


def feature_graph_from_dict(payload: Mapping[str, Any]) -> FeatureGraph:
    required = ("schema", "part_id", "design_intent", "units", "features")
    missing = [key for key in required if key not in payload]
    if missing:
        raise FeatureGraphValidationError(f"missing graph fields: {missing}")
    raw_features = payload["features"]
    if not isinstance(raw_features, list) or not raw_features:
        raise FeatureGraphValidationError("features must be a non-empty list")

    seen: set[str] = set()
    nodes: list[FeatureNode] = []
    for raw in raw_features:
        if not isinstance(raw, Mapping):
            raise FeatureGraphValidationError("feature entries must be objects")
        feature_id = raw.get("feature_id")
        kind = raw.get("kind")
        deps = raw.get("depends_on", [])
        params = raw.get("params", {})
        if not isinstance(feature_id, str) or not feature_id.strip():
            raise FeatureGraphValidationError("feature_id must be non-empty")
        if feature_id in seen:
            raise FeatureGraphValidationError(f"duplicate feature_id: {feature_id}")
        if kind not in ALLOWED_FEATURE_KINDS:
            raise FeatureGraphValidationError(f"unsupported feature kind: {kind}")
        if not isinstance(deps, list) or not all(isinstance(dep, str) for dep in deps):
            raise FeatureGraphValidationError(f"depends_on must be string list for {feature_id}")
        if not isinstance(params, Mapping):
            raise FeatureGraphValidationError(f"params must be object for {feature_id}")
        seen.add(feature_id)
        nodes.append(FeatureNode(feature_id, kind, tuple(deps), dict(params)))

    unknown = {dep for node in nodes for dep in node.depends_on if dep not in seen}
    if unknown:
        raise FeatureGraphValidationError(f"unknown dependencies: {sorted(unknown)}")

    _assert_acyclic(nodes)
    units = payload["units"]
    if units not in {"m", "mm"}:
        raise FeatureGraphValidationError(f"unsupported units: {units}")

    return FeatureGraph(
        schema=str(payload["schema"]),
        part_id=str(payload["part_id"]),
        design_intent=str(payload["design_intent"]),
        units=units,
        features=tuple(nodes),
    )


def _assert_acyclic(nodes: list[FeatureNode]) -> None:
    deps = {node.feature_id: set(node.depends_on) for node in nodes}
    remaining = set(deps)
    while remaining:
        ready = {node for node in remaining if not (deps[node] & remaining)}
        if not ready:
            raise FeatureGraphValidationError("feature graph contains a dependency cycle")
        remaining -= ready


def graph_to_dict(graph: FeatureGraph) -> dict[str, Any]:
    return {
        "schema": graph.schema,
        "part_id": graph.part_id,
        "design_intent": graph.design_intent,
        "units": graph.units,
        "features": [
            {
                "feature_id": node.feature_id,
                "kind": node.kind,
                "depends_on": list(node.depends_on),
                "params": dict(node.params),
            }
            for node in graph.features
        ],
    }
