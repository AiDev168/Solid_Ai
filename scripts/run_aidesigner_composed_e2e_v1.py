from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.aidesigner_composition_v1 import AiDesignerCompositionError, execute_canonical, prepare_and_plan

DEFAULT_PROMPT = ("Create a motor mounting bracket, 120 mm by 80 mm footprint, "
                  "10 mm thick, four M8 mounting holes, two structural ribs, and R5 outer fillets.")

def main() -> int:
    parser = argparse.ArgumentParser(description="Run Ai_Designer canonical pipeline against SolidPilot.")
    parser.add_argument("prompt", nargs="*")
    parser.add_argument("--solidpilot-url", default=os.getenv("SOLIDPILOT_BASE_URL", "http://localhost:5000"))
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    prompt = " ".join(args.prompt).strip() or os.getenv("SOLID_AI_PROMPT", DEFAULT_PROMPT)
    try:
        if args.plan_only:
            request, planning = prepare_and_plan(prompt, solidpilot_base_url=args.solidpilot_url, request_id="solid-ai-aidesigner-composed-e2e-v1")
            payload = {"ok": planning.execution_plan_v3 is not None, "stage": "PLAN",
                       "request_schema": getattr(request, "schema", None),
                       "part_id": getattr(request.intent, "part_id", None),
                       "feature_count": len(request.intent.features),
                       "feature_kinds": [str(f.get("kind", "")) for f in request.intent.features],
                       "execution_plan": planning.execution_plan_v3.to_dict() if planning.execution_plan_v3 is not None else None}
        else:
            result = execute_canonical(prompt, solidpilot_base_url=args.solidpilot_url, operation_prefix="AIDESIGNER-COMPOSED-E2E-V1")
            payload = {"ok": result.execution.all_verified, "stage": "EXECUTION",
                       "part_id": result.request.intent.part_id,
                       "feature_count": len(result.request.intent.features),
                       "feature_order": list(result.planning.planning.feature_order),
                       "execution_count": len(result.execution.executions),
                       "final_result": result.execution.final_result}
    except AiDesignerCompositionError as exc:
        payload = {"ok": False, "code": "AIDESIGNER_COMPOSITION_ERROR", "error": str(exc)}
    except Exception as exc:
        payload = {"ok": False, "code": type(exc).__name__, "error": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if payload.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())