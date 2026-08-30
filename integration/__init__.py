"""Small, standalone integration layer for proven Ai_Designer CAD assets."""

from .aidesigner_assets import CAPABILITIES, CapabilitySpec, describe_capabilities, get_capability, lower_boss, lower_fillet, lower_hole, require_capability

__all__ = [
    "CAPABILITIES",
    "CapabilitySpec",
    "describe_capabilities",
    "get_capability",
    "lower_boss",
    "lower_fillet",
    "lower_hole",
    "require_capability",
]
