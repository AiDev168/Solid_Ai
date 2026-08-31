from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .feature_graph_v1 import FeatureGraph, FeatureGraphValidationError, feature_graph_from_dict


SYSTEM_PROMPT = """You are the semantic CAD planning agent for Solid_Ai.
Your only job is to convert an engineering request into a backend-neutral FeatureGraph JSON.
Do not emit SolidWorks API calls, MCP tool calls, coordinates for backend selectors, or code.
Use only these feature kinds: profile, extrude_boss, revolve, revolve_cut, hole_pattern, rib, fillet, chamfer, pattern.
Represent dependencies explicitly in depends_on.
Use SI meters unless units=mm is necessary.
For ambiguous requirements, preserve the ambiguity in params and set design_intent accordingly; never invent unsafe engineering facts.
Return JSON only with keys: schema, part_id, design_intent, units, features.
Each feature must contain feature_id, kind, depends_on, params.
"""


class LLMTransport(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class LocalOpenAICompatibleTransport:
    base_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = "not-needed"
    timeout_s: float = 90.0
    model: str | None = None

    def _request(self, path: str) -> Any:
        request = urllib.request.Request(
            self.base_url.rstrip("/") + path,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))

    def _select_model(self) -> str:
        if self.model:
            return self.model
        payload = self._request("/models")
        data = payload.get("data") if isinstance(payload, Mapping) else None
        if not isinstance(data, list) or not data:
            raise RuntimeError("Local LLM endpoint returned no models")
        model_id = data[0].get("id")
        if not isinstance(model_id, str) or not model_id:
            raise RuntimeError("Local LLM endpoint returned invalid model metadata")
        return model_id

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        model = self._select_model()
        payload = json.dumps({
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"local LLM unavailable at {self.base_url}: {exc}") from exc
        choices = result.get("choices") if isinstance(result, Mapping) else None
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("local LLM returned no choices")
        message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("local LLM returned empty content")
        return content


def _extract_json(text: str) -> Mapping[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1])
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise FeatureGraphValidationError("LLM response did not contain a JSON object")
    try:
        value = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise FeatureGraphValidationError(f"LLM returned invalid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise FeatureGraphValidationError("LLM root value must be an object")
    return value


class SemanticLLMPlannerV1:
    def __init__(self, transport: LLMTransport):
        self.transport = transport

    def plan(self, engineering_prompt: str) -> FeatureGraph:
        if not isinstance(engineering_prompt, str) or not engineering_prompt.strip():
            raise ValueError("engineering_prompt must be non-empty")
        raw = self.transport.generate(SYSTEM_PROMPT, engineering_prompt)
        return feature_graph_from_dict(_extract_json(raw))
