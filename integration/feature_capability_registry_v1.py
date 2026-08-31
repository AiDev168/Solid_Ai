from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureCapabilityBinding:
    feature_kind: str
    capability_id: str


class FeatureCapabilityRegistryV1:
    """Explicit semantic feature -> capability bindings.

    Bindings are declarations, not proofs. A capability's proven/candidate
    lifecycle is owned by the capability catalog and backend evidence.
    """

    def __init__(self, bindings: tuple[FeatureCapabilityBinding, ...] = ()) -> None:
        self._bindings = {item.feature_kind: item.capability_id for item in bindings}

    def register(self, feature_kind: str, capability_id: str) -> None:
        if not feature_kind.strip() or not capability_id.strip():
            raise ValueError("feature_kind and capability_id must be non-empty")
        if feature_kind in self._bindings:
            raise ValueError(f"feature kind already registered: {feature_kind}")
        self._bindings[feature_kind] = capability_id

    def capability_for(self, feature_kind: str) -> str | None:
        return self._bindings.get(feature_kind)

    def require(self, feature_kind: str) -> str:
        capability_id = self.capability_for(feature_kind)
        if capability_id is None:
            raise KeyError(f"no explicit capability binding for feature kind: {feature_kind}")
        return capability_id


def build_default_feature_capability_registry() -> FeatureCapabilityRegistryV1:
    return FeatureCapabilityRegistryV1((
        FeatureCapabilityBinding("profile", "part.create_sketch"),
        FeatureCapabilityBinding("extrude_boss", "part.extrude_boss"),
        FeatureCapabilityBinding("hole_pattern", "part.hole"),
        FeatureCapabilityBinding("rib", "part.extrude_boss"),
        FeatureCapabilityBinding("fillet", "edge.fillet"),
    ))


__all__ = [
    "FeatureCapabilityBinding",
    "FeatureCapabilityRegistryV1",
    "build_default_feature_capability_registry",
]
