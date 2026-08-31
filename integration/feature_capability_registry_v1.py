from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .aidesigner_assets import CapabilitySpec, get_capability


@dataclass(frozen=True)
class FeatureCapabilityBinding:
    feature_kind: str
    capability: CapabilitySpec

    @property
    def capability_id(self) -> str:
        return self.capability.capability_id


class FeatureCapabilityRegistryV1:
    """Explicit semantic feature -> capability declarations.

    A binding may point to a proven or candidate capability. The registry does
    not promote evidence status and never invents bindings for unknown feature
    kinds.
    """

    def __init__(self, bindings: tuple[FeatureCapabilityBinding, ...] = ()) -> None:
        self._bindings = {item.feature_kind: item for item in bindings}

    def register(self, feature_kind: str, capability: CapabilitySpec) -> None:
        if not feature_kind.strip() or not capability.capability_id.strip():
            raise ValueError("feature_kind and capability_id must be non-empty")
        if feature_kind in self._bindings:
            raise ValueError(f"feature kind already registered: {feature_kind}")
        self._bindings[feature_kind] = FeatureCapabilityBinding(feature_kind, capability)

    def binding_for(self, feature_kind: str) -> FeatureCapabilityBinding | None:
        return self._bindings.get(feature_kind)

    def capability_for(self, feature_kind: str) -> CapabilitySpec | None:
        binding = self.binding_for(feature_kind)
        return binding.capability if binding is not None else None

    def require(self, feature_kind: str) -> FeatureCapabilityBinding:
        binding = self.binding_for(feature_kind)
        if binding is None:
            raise KeyError(f"no explicit capability binding for feature kind: {feature_kind}")
        return binding


def build_default_feature_capability_registry() -> FeatureCapabilityRegistryV1:
    capability_ids = (
        ("profile", "part.create_sketch"),
        ("extrude_boss", "part.extrude_boss"),
        ("hole_pattern", "part.hole"),
        ("rib", "part.extrude_boss"),
        ("fillet", "edge.fillet"),
    )
    bindings: list[FeatureCapabilityBinding] = []
    for feature_kind, capability_id in capability_ids:
        capability = get_capability(capability_id)
        if capability is None:
            raise KeyError(f"capability registry missing: {capability_id}")
        bindings.append(FeatureCapabilityBinding(feature_kind, capability))
    return FeatureCapabilityRegistryV1(tuple(bindings))


__all__ = [
    "FeatureCapabilityBinding",
    "FeatureCapabilityRegistryV1",
    "build_default_feature_capability_registry",
]
