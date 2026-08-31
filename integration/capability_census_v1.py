from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .aidesigner_assets import get_capability


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    semantic_kind: str
    backend_tools: tuple[str, ...]
    strategy_family: str
    status: str
    local_evidence: str | None = None
    historical_aidesigner_evidence: str | None = None
    source: str = ""


_STRATEGY_BY_TOOL = {
    "create_sketch": "sketch_support",
    "add_sketch_entity": "sketch_entity",
    "add_sketch_entities": "batch_sketch",
    "extrude_feature": "sketch_then_feature",
    "add_edge_feature": "edge_modifier",
}

_PREFERRED_IDS = {
    "boss": "part.extrude_boss",
    "cut": "part.cut_extrude",
    "revolve": "part.revolve",
    "revolve_cut": "part.revolve_cut",
    "fillet": "edge.fillet",
    "chamfer": "edge.chamfer",
    "circle": "sketch.circle",
    "rectangle": "sketch.rectangle",
    "line": "sketch.line",
    "arc": "sketch.arc",
    "ellipse": "sketch.ellipse",
    "spline": "sketch.spline",
    "sweep": "part.sweep",
    "loft": "part.loft",
}

_HISTORICAL_AIDESIGNER = {
    "revolve": "feature.revolve.v1",
    "sweep": "feature.sweep.v1",
    "loft": "feature.loft.v1",
    "chamfer": "feature.chamfer.v1",
}


def _literal_values(node: ast.AST) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(node, ast.Subscript):
        target = node.value
        target_name = target.id if isinstance(target, ast.Name) else ""
        if target_name == "Literal":
            payload = node.slice
            elements = payload.elts if isinstance(payload, ast.Tuple) else [payload]
            for item in elements:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    values.append(item.value)
    return tuple(values)


def discover_legacy_server(path: str | Path) -> tuple[CapabilityRecord, ...]:
    """Static inventory; never imports or executes the SolidWorks server."""
    source_path = Path(path)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    records: dict[str, CapabilityRecord] = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tool_name = node.name
        for arg in node.args.args:
            for value in _literal_values(arg.annotation):
                preferred = _PREFERRED_IDS.get(value)
                capability_id = preferred or f"{tool_name}.{value}"
                local = get_capability(capability_id)
                status = local.status if local else "candidate"
                historical = _HISTORICAL_AIDESIGNER.get(value)
                records[capability_id] = CapabilityRecord(
                    capability_id=capability_id,
                    semantic_kind=value,
                    backend_tools=(tool_name,),
                    strategy_family=_STRATEGY_BY_TOOL.get(tool_name, "direct_tool"),
                    status=status,
                    local_evidence=local.evidence if local else None,
                    historical_aidesigner_evidence=historical,
                    source=str(source_path),
                )
    return tuple(records[key] for key in sorted(records))


def census_from_repository(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root)
    server = root / "vendor" / "q3ds-solidworks-mcp" / "adapters" / "claude" / "legacy_server.py"
    records = discover_legacy_server(server)

    proven = sum(item.status == "proven" for item in records)
    candidates = sum(item.status == "candidate" for item in records)
    blocked = sum(item.status == "blocked" for item in records)
    return {
        "schema": "solid-ai.capability-census.v1",
        "backend": "q3ds-solidworks-mcp",
        "source": str(server),
        "counts": {
            "total_discovered": len(records),
            "proven_local": proven,
            "candidate": candidates,
            "blocked": blocked,
        },
        "records": [asdict(item) for item in records],
        "policy": {
            "discovery_is_not_proof": True,
            "historical_aidesigner_evidence_is_not_local_promotion": True,
            "promotion_requires_live_evidence": True,
        },
    }


def write_census(repository_root: str | Path, output_path: str | Path) -> dict[str, Any]:
    report = census_from_repository(repository_root)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


__all__ = ["CapabilityRecord", "census_from_repository", "discover_legacy_server", "write_census"]
