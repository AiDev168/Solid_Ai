from integration.llm_provider_v1 import load_llm_provider_config


def test_default_provider_is_local(monkeypatch):
    for name in (
        "BENCHMARK_PROVIDER",
        "BENCHMARK_BASE_URL",
        "BENCHMARK_MODEL",
        "BENCHMARK_API_KEY",
        "SOLID_AI_LLM_BASE_URL",
        "SOLID_AI_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    config = load_llm_provider_config()
    assert config.provider == "local"
    assert config.base_url == "http://127.0.0.1:1234/v1"


def test_gapgpt_benchmark_contract(monkeypatch):
    monkeypatch.setenv("BENCHMARK_PROVIDER", "api-provider")
    monkeypatch.setenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
    monkeypatch.setenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
    monkeypatch.setenv("BENCHMARK_API_KEY", "test-key")
    config = load_llm_provider_config()
    assert config.provider == "api-provider"
    assert config.base_url == "https://api.gapgpt.app/v1"
    assert config.model == "gapgpt-qwen-3.5"
    assert config.api_key == "test-key"


def test_gapgpt_requires_key(monkeypatch):
    monkeypatch.setenv("BENCHMARK_PROVIDER", "api-provider")
    monkeypatch.setenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
    monkeypatch.setenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
    monkeypatch.delenv("BENCHMARK_API_KEY", raising=False)
    try:
        load_llm_provider_config()
    except RuntimeError as exc:
        assert "BENCHMARK_API_KEY" in str(exc)
    else:
        raise AssertionError("expected missing-key failure")
