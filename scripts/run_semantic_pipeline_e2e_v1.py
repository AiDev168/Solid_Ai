from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.feature_graph_v1 import feature_graph_from_dict, graph_to_dict
from integration.llm_fidelity_gate_v1 import (
    assert_explicit_constraints_preserved,
    assert_no_implicit_m8_drill_conversion,
)


def main() -> int:
    requirements = {
        "explicit_constraints": [
            {"id": "c1", "target": "width", "value": 120, "unit": "mm"},
            {"id": "c2", "target": "height", "value": 80, "unit": "mm"},
            {"id": "c3", "target": "thickness", "value": 10, "unit": "mm"},
            {"id": "c4", "target": "bolt_hole_size", "value": "M8", "unit": "nominal"},
            {"id": "c5", "target": "hole_count", "value": 4, "unit": "count"},
            {"id": "c6", "target": "rib_count", "value": 2, "unit": "count"},
            {"id": "c7", "target": "outer_fillet_radius", "value": 5, "unit": "mm"},
        ]
    }
    graph_payload = {
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "motor_bracket_120x80",
        "design_intent": "motor bracket 120x80x10 with four M8 holes, two ribs and R5 outer fillets",
        "units": "mm",
        "features": [
            {"feature_id": "base_profile", "kind": "profile", "depends_on": [], "params": {"width": 120, "height": 80, "requirement_refs": ["c1", "c2"]}},
            {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["base_profile"], "params": {"thickness": 10, "requirement_refs": ["c3"]}},
            {"feature_id": "holes", "kind": "hole_pattern", "depends_on": ["base"], "params": {"fastener": "M8", "count": 4, "requirement_refs": ["c4", "c5"]}},
            {"feature_id": "ribs", "kind": "pattern", "depends_on": ["base"], "params": {"count": 2, "requirement_refs": ["c6"]}},
            {"feature_id": "fillet", "kind": "fillet", "depends_on": ["base", "holes", "ribs"], "params": {"radius_mm": 5, "selection": "all_outer_edges", "requirement_refs": ["c7"]}},
        ],
    }
    assert_explicit_constraints_preserved(graph_payload, requirements)
    assert_no_implicit_m8_drill_conversion(graph_payload, requirements)
    graph = feature_graph_from_dict(graph_payload)
    print("PASS: semantic pipeline gate")
    print(json.dumps(graph_to_dict(graph), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
