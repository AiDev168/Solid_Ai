from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


SUPPORTED_NODE_TYPES = {
    "box",
    "sketch",
    "extrude",
    "revolve",
    "rib",
    "hole",
    "fillet",
    "chamfer",
    "loft",
    "circular_pattern",
    "sheet_metal",
    "sketched_bend",
    "mirror",
}

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class FeatureGraphPlanningError(ValueError):
    """Raised when an LLM response cannot be accepted as a Feature Graph."""


@dataclass(frozen=True)
class LocalLLMConfig:
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = "local-model"
    api_key: str = "not-needed"
    timeout_seconds: int = 120

    @classmethod
    def from_environment(cls) -> "LocalLLMConfig":
        return cls(
            base_url=os.getenv("SOLID_AI_LLM_BASE_URL", cls.base_url),
            model=os.getenv("SOLID_AI_LLM_MODEL", cls.model),
            api_key=os.getenv("SOLID_AI_LLM_API_KEY", cls.api_key),
            timeout_seconds=int(os.getenv("SOLID_AI_LLM_TIMEOUT", str(cls.timeout_seconds))),
        )

    def validate_local_only(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
            raise FeatureGraphPlanningError(
                "LLM endpoint must be local-only (localhost/127.0.0.1/::1)"
            )


class OpenAICompatibleLocalClient:
    def __init__(self, config: LocalLLMConfig | None = None) -> None:
        self.config = config or LocalLLMConfig.from_environment()
        self.config.validate_local_only()

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise FeatureGraphPlanningError(f"local LLM request failed: {exc}") from exc

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise FeatureGraphPlanningError("local LLM returned no chat content") from exc


SYSTEM_PROMPT = """You are the planning layer of Solid AI.

Your ONLY output is one CAD-neutral Feature Graph JSON object. Never emit MCP tool
calls, SolidWorks API calls, Python code, coordinates for tool invocation outside
node parameters, or execution steps.

Target IR contract:
{
  "schema_version": "feature-graph-v0.5.6-draft",
  "units": "meters",
  "nodes": [
    {"id": "n1", "type": "...", ...}
  ]
}

Use only these node types when needed:
box, sketch, extrude, revolve, rib, hole, fillet, chamfer, loft,
circular_pattern, sheet_metal, sketched_bend, mirror.

Rules:
- All lengths are meters.
- Angles inside the IR are radians unless the node contract explicitly requires degrees.
- Nodes reference earlier node ids, never SolidWorks names or backend indices.
- A semantic reference is represented in node.ref / reference fields, not a raw tool selector.
- Do not invent unsupported feature types.
- Do not silently drop requested engineering requirements. If the request cannot be
  represented by the vocabulary, return a JSON object with an "unresolved_requirements"
  array and still produce the best valid graph you can.
- Return JSON only. No markdown fences and no explanation.
"""


def _extract_json(text: str) -> Mapping[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise FeatureGraphPlanningError(f"LLM did not return valid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise FeatureGraphPlanningError("Feature Graph root must be a JSON object")
    return value


def validate_feature_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    schema_version = graph.get("schema_version")
    units = graph.get("units")
    nodes = graph.get("nodes")
    if not isinstance(schema_version, str) or not schema_version:
        raise FeatureGraphPlanningError("Feature Graph requires schema_version")
    if units != "meters":
        raise FeatureGraphPlanningError("Feature Graph units must be meters")
    if not isinstance(nodes, list) or not nodes:
        raise FeatureGraphPlanningError("Feature Graph requires a non-empty nodes array")

    seen: set[str] = set()
    for position, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            raise FeatureGraphPlanningError(f"node[{position}] must be an object")
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not node_id:
            raise FeatureGraphPlanningError(f"node[{position}] missing id")
        if node_id in seen:
            raise FeatureGraphPlanningError(f"duplicate node id: {node_id}")
        seen.add(node_id)
        if node_type not in SUPPORTED_NODE_TYPES:
            raise FeatureGraphPlanningError(f"unsupported node type: {node_type}")

        for key in ("sketch", "feature", "node"):
            value = node.get(key)
            if isinstance(value, str) and value not in seen:
                raise FeatureGraphPlanningError(
                    f"node {node_id} references future/unknown node {value}"
                )

    if any(key in graph for key in ("tool", "arguments", "call_tool", "mcp")):
        raise FeatureGraphPlanningError("raw tool-call fields are forbidden in Feature Graph IR")

    return dict(graph)


def plan_prompt(user_prompt: str, client: OpenAICompatibleLocalClient | None = None) -> dict[str, Any]:
    if not user_prompt.strip():
        raise FeatureGraphPlanningError("engineering prompt is empty")
    llm = client or OpenAICompatibleLocalClient()
    raw = llm.chat(SYSTEM_PROMPT, user_prompt)
    return validate_feature_graph(_extract_json(raw))
