from __future__ import annotations

from typing import Any, Mapping

from .aidesigner_composition_v1 import (
    AiDesignerCompositionError as AiDesignerBridgeError,
    build_canonical_gateway,
    load_stack,
)


# Compatibility facade. The canonical implementation now lives in
# aidesigner_composition_v1 so there is one Ai_Designer import/gateway seam.

def load_aidesigner_assets() -> Any:
    return load_stack()


def build_gateway_from_environment() -> Any:
    return build_canonical_gateway()


def extract_requirements(
    user_text: str,
    *,
    gateway: Any | None = None,
    request_id: str | None = None,
) -> Any:
    if not isinstance(user_text, str) or not user_text.strip():
        raise ValueError("user_text must be non-empty")
    stack = load_stack()
    active_gateway = gateway or stack.gateway_cls.from_environment()
    extractor = stack.requirements_extractor_cls(active_gateway, request_id=request_id)
    return extractor.extract(user_text, request_id=request_id)


def extract_intent(
    requirements_payload: Mapping[str, Any],
    *,
    source_text: str | None = None,
    gateway: Any | None = None,
) -> Any:
    if not isinstance(requirements_payload, Mapping):
        raise TypeError("requirements_payload must be a mapping")
    stack = load_stack()
    active_gateway = gateway or stack.gateway_cls.from_environment()
    extractor = stack.intent_extractor_cls(active_gateway)
    return extractor.extract(requirements_payload, source_text=source_text)


__all__ = [
    "AiDesignerBridgeError",
    "build_gateway_from_environment",
    "extract_intent",
    "extract_requirements",
    "load_aidesigner_assets",
]
