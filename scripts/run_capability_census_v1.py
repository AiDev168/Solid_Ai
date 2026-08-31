from __future__ import annotations

import json
from pathlib import Path

from integration.capability_census_v1 import census_from_repository


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = census_from_repository(root)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
