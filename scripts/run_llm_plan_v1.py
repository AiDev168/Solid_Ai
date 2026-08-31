from __future__ import annotations

import argparse
import json
import os

from integration.feature_graph_v1 import graph_to_dict
from integration.llm_design_planner_v1 import LocalOpenAICompatibleTransport, SemanticLLMPlannerV1


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a validated semantic CAD FeatureGraph with a local LLM")
    parser.add_argument("prompt", nargs="?", default=(
        "یک براکت موتور 120 در 80 میلی‌متر بساز، ضخامت پایه 10 میلی‌متر، "
        "چهار سوراخ M8، دو ریب تقویتی و تمام لبه‌های بیرونی R5."
    ))
    parser.add_argument("--base-url", default=os.getenv("SOLID_AI_LLM_BASE_URL", "http://127.0.0.1:1234/v1"))
    parser.add_argument("--model", default=os.getenv("SOLID_AI_LLM_MODEL"))
    args = parser.parse_args()

    planner = SemanticLLMPlannerV1(
        LocalOpenAICompatibleTransport(base_url=args.base_url, model=args.model)
    )
    graph = planner.plan(args.prompt)
    print(json.dumps(graph_to_dict(graph), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
