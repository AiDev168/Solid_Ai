from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.motor_bracket_plan_v1 import MOTOR_BRACKET_V1, ordered_features

def main() -> int:
    order = [feature.feature_id for feature in ordered_features()]
    expected = ["base_profile", "base", "mounting_holes", "rib_left", "rib_right", "outer_fillets"]
    if order != expected:
        raise SystemExit(f"unexpected dependency order: {order!r}")
    plan = MOTOR_BRACKET_V1
    if plan.features[2].params["diameter_m"] != 0.008:
        raise SystemExit("M8 diameter mismatch")
    if len(plan.features[2].params["centers_m"]) != 4:
        raise SystemExit("mounting-hole count mismatch")
    if plan.features[-1].params["radius_m"] != 0.005:
        raise SystemExit("R5 fillet mismatch")
    print("PASS: motor bracket semantic plan v1")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())