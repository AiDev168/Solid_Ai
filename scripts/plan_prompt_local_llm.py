from __future__ import annotations

import argparse
import json

from app.llm_feature_graph_v1 import LocalLLMConfig, OpenAICompatibleLocalClient, plan_prompt


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan an engineering prompt into CAD-neutral Feature Graph IR")
    parser.add_argument("prompt", nargs="?", help="engineering prompt")
    parser.add_argument("--model", help="local model id; defaults to SOLID_AI_LLM_MODEL")
    args = parser.parse_args()

    prompt = args.prompt or input("Engineering prompt: ").strip()
    config = LocalLLMConfig.from_environment()
    if args.model:
        config = LocalLLMConfig(
            base_url=config.base_url,
            model=args.model,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )

    graph = plan_prompt(prompt, client=OpenAICompatibleLocalClient(config))
    print(json.dumps(graph, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
