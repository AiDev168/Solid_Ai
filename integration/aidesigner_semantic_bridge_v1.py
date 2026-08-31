from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Mapping


class AiDesignerBridgeError(RuntimeError):
    """Raised when the proven Ai_Designer semantic assets cannot be reused safely."""


@dataclass(frozen=True)
class AiDesignerSemanticAssetsV1:
    """Handles to the canonical Ai_Designer requirements/intent stack."""

    gateway_cls: Any
    requirements_extractor_cls: Any
    intent_extractor_cls: Any
    requirements_schema: Mapping[str, Any]
    intent_schema: Mapping[str, Any]


def load_aidesigner_assets() -> AiDesignerSemanticAssetsV1:
    """Import, rather than reimplement, the canonical Ai_Designer semantic stack."""
    try:
        gateway = importlib.import_module("ai_designer.llm.gateway")
        requirements = importlib.import_module(
            "ai_designer.engineering.requirements_v2_resilient_v1"
        )
        intent = importlib.import_module("ai_designer.engineering.intent_v2")
        schemas = importlib.import_module("ai_designer.engineering.llm_schemas_v1")
    except ImportError as exc:
        raise AiDesignerBridgeError(
            "Ai_Designer semantic assets are not importable in the current environment"
        ) from exc

    return AiDesignerSemanticAssetsV1(
        gateway_cls=gateway.LLMGateway,
        requirements_extractor_cls=requirements.ResilientEngineeringRequirementsExtractorV2,
        intent_extractor_cls=intent.EngineeringIntentExtractorV2,
        requirements_schema=schemas.ENGINEERING_REQUIREMENTS_JSON_SCHEMA,
        intent_schema=schemas.ENGINEERING_INTENT_JSON_SCHEMA,
    )


def build_gateway_from_environment() -> Any:
    """Construct the canonical Ai_Designer provider-neutral gateway."""
    return load_aidesigner_assets().gateway_cls.from_environment()


def extract_requirements(
    user_text: str,
    *,
    gateway: Any | None = None,
    request_id: str | None = None,
) -> Any:
    """Run Ai_Designer's evidence-backed RequirementsV2 extractor."""
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text must be non-empty")
    assets = load_aidesigner_assets()
    active_gateway = gateway or assets.gateway_cls.from_environment()
    extractor = assets.requirements_extractor_cls(
        active_gateway,
        request_id=request_id,
    )
    return extractor.extract(user_text, request_id=request_id)


def extract_intent(
    requirements_payload: Mapping[str, Any],
    *,
    source_text: str | None = None,
    gateway: Any | None = None,
) -> Any:
    """Run Ai_Designer's fidelity/constraint-checked EngineeringIntent extractor."""
    if not isinstance(requirements_payload, Mapping):
        raise TypeError("requirements_payload must be a mapping")
    assets = load_aidesigner_assets()
    active_gateway = gateway or assets.gateway_cls.from_environment()
    extractor = assets.intent_extractor_cls(active_gateway)
    return extractor.extract(requirements_payload, source_text=source_text)


__all__ = [
    "AiDesignerBridgeError",
    "AiDesignerSemanticAssetsV1",
    "build_gateway_from_environment",
    "extract_intent",
    "extract_requirements",
    "load_aidesigner_assets",
]
