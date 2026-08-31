from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.feature_graph_v1 import graph_to_dict
from integration.llm_design_planner_v1 import SemanticLLMPlannerV1
from integration.llm_provider_v1 import build_transport


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a validated semantic CAD FeatureGraph with an OpenAI-compatible LLM"
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=(
            "یک براکت موتور 120 در 80 میلی‌متر بساز، ضخامت پایه 10 میلی‌متر، "
            "چهار سوراخ M8، دو ریب تقویتی و تمام لبه‌های بیرونی R5."
        ),
    )
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()

    if args.provider:
        os.environ["BENCHMARK_PROVIDER"] = args.provider
    if args.base_url:
        os.environ["BENCHMARK_BASE_URL"] = args.base_url
        os.environ["SOLID_AI_LLM_BASE_URL"] = args.base_url
    if args.model:
        os.environ["BENCHMARK_MODEL"] = args.model
        os.environ["SOLID_AI_LLM_MODEL"] = args.model

    planner = SemanticLLMPlannerV1(build_transport())
    graph = planner.plan(args.prompt)
    print(json.dumps(graph_to_dict(graph), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
