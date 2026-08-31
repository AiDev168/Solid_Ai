from __future__ import annotations

import os
from dataclasses import dataclass

from .llm_design_planner_v1 import LocalOpenAICompatibleTransport


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    base_url: str
    model: str | None
    api_key: str
    timeout_s: float = 90.0


def load_llm_provider_config() -> LLMProviderConfig:
    provider = os.getenv("BENCHMARK_PROVIDER") or os.getenv("SOLID_AI_LLM_PROVIDER") or "local"
    provider = provider.strip().lower()

    if provider in {"api-provider", "gapgpt", "api"}:
        base_url = os.getenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
        model = os.getenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
        api_key = os.getenv("BENCHMARK_API_KEY", "")
        if not api_key:
            raise RuntimeError("BENCHMARK_API_KEY is required for api-provider")
        return LLMProviderConfig(provider="api-provider", base_url=base_url, model=model, api_key=api_key)

    base_url = os.getenv("SOLID_AI_LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    model = os.getenv("SOLID_AI_LLM_MODEL") or None
    api_key = os.getenv("SOLID_AI_LLM_API_KEY", "not-needed")
    return LLMProviderConfig(provider="local", base_url=base_url, model=model, api_key=api_key)


def build_transport() -> LocalOpenAICompatibleTransport:
    config = load_llm_provider_config()
    return LocalOpenAICompatibleTransport(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout_s=config.timeout_s,
        model=config.model,
    )
