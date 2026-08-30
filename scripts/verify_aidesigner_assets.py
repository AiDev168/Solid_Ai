from __future__ import annotations

import sys
from pathlib import Path

# Make the repository root importable when this script is invoked directly as:
#   python scripts\verify_aidesigner_assets.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.aidesigner_assets import (  # noqa: E402
    CAPABILITIES,
    lower_boss,
    lower_fillet,
    lower_hole,
    require_capability,
)


def main() -> int:
    expected = {
        "part.open_new": "open_new_part",
        "part.create_sketch": "create_sketch",
        "sketch.circle": "add_sketch_entity",
        "part.extrude_boss": "extrude_feature",
        "model.analyze_geometry": "analyze_model",
        "part.hole": "extrude_feature",
        "edge.fillet": "add_edge_feature",
    }
    actual = {item.capability_id: item.tool for item in CAPABILITIES}
    if actual != expected:
        raise SystemExit(f"Capability mapping mismatch: {actual!r}")

    if lower_boss(depth_m=0.01)["tool"] != "extrude_feature":
        raise SystemExit("Boss lowering mismatch")
    hole = lower_hole(cx=0.0, cy=0.0, diameter_m=0.01, depth_m=0.02)
    if [step["tool"] for step in hole] != ["create_sketch", "add_sketch_entity", "extrude_feature"]:
        raise SystemExit("Hole lowering sequence mismatch")
    fillet = lower_fillet(radius_m=0.005, edge_indices="[1]")
    if fillet["tool"] != "add_edge_feature" or fillet["params"].get("edge_indices") != "[1]":
        raise SystemExit("Fillet lowering mismatch")

    require_capability("edge.fillet")
    print(f"PASS: verified {len(CAPABILITIES)} Ai_Designer capability mappings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
