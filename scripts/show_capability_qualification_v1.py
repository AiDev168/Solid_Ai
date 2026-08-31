from __future__ import annotations

import json

from integration.capability_qualification_v1 import QualificationHarnessV1, build_core_modeling_scenarios


def main() -> int:
    harness = QualificationHarnessV1(build_core_modeling_scenarios())
    print(json.dumps([harness.to_dict(s) for s in harness.scenarios], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
