from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .support_reference_v1 import (
    SketchFrame,
    SupportReferenceError,
    resolve_extrude_end_face,
    resolve_extrusion_boundary_edges,
)


class RuntimeReferenceResolutionError(ValueError):
    """Raised when a semantic runtime reference cannot be bound safely."""


@dataclass(frozen=True)
class ReferenceRequest:
    reference_id: str
    kind: str
    role: str
    source_feature_id: str
    criteria: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferenceBinding:
    reference_id: str
    kind: str
    role: str
    source_feature_id: str
    state_version: int
    backend_indices: tuple[int, ...]
    evidence: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def backend_index(self) -> int:
        if len(self.backend_indices) != 1:
            raise RuntimeReferenceResolutionError(
                f"reference {self.reference_id} resolves to {len(self.backend_indices)} items; use backend_indices"
            )
        return self.backend_indices[0]


class RuntimeReferenceContextV1:
    """Resolve semantic references against fresh backend evidence.

    The context only produces bindings. It never generates SolidPilot tool calls
    and never invents backend selectors from coordinates that are absent from
    the evidence.
    """

    def bind_extrude_end_face(
        self,
        request: ReferenceRequest,
        *,
        faces: Sequence[Mapping[str, Any]],
        source_frame: SketchFrame,
        depth_m: float,
        state_version: int,
    ) -> ReferenceBinding:
        if request.kind != "face" or request.role != "extrude_end_face":
            raise RuntimeReferenceResolutionError(
                f"unsupported face request: {request.kind}/{request.role}"
            )
        try:
            resolved = resolve_extrude_end_face(
                faces,
                frame=source_frame,
                depth_m=depth_m,
                reference_id=request.reference_id,
                state_version=state_version,
            )
        except SupportReferenceError as exc:
            raise RuntimeReferenceResolutionError(str(exc)) from exc
        return ReferenceBinding(
            reference_id=request.reference_id,
            kind="face",
            role=request.role,
            source_feature_id=request.source_feature_id,
            state_version=state_version,
            backend_indices=(int(resolved["backend_index"]),),
            evidence=(dict(resolved["evidence"]),),
            metadata={
                "expected_point": resolved["expected_point"],
                "expected_normal": resolved["expected_normal"],
                "score": resolved["score"],
            },
        )

    def bind_outer_extrusion_edges(
        self,
        request: ReferenceRequest,
        *,
        edges: Sequence[Mapping[str, Any]],
        source_frame: SketchFrame,
        bounds_uv: tuple[float, float, float, float],
        state_version: int,
    ) -> ReferenceBinding:
        if request.kind != "edge" or request.role != "outer_extrusion_boundary":
            raise RuntimeReferenceResolutionError(
                f"unsupported edge request: {request.kind}/{request.role}"
            )
        try:
            resolved = resolve_extrusion_boundary_edges(
                edges,
                frame=source_frame,
                bounds_uv=bounds_uv,
                reference_id=request.reference_id,
                state_version=state_version,
            )
        except SupportReferenceError as exc:
            raise RuntimeReferenceResolutionError(str(exc)) from exc
        return ReferenceBinding(
            reference_id=request.reference_id,
            kind="edge",
            role=request.role,
            source_feature_id=request.source_feature_id,
            state_version=state_version,
            backend_indices=tuple(int(item["backend_index"]) for item in resolved),
            evidence=tuple(dict(item) for item in resolved),
            metadata={"count": len(resolved)},
        )


def binding_to_backend_params(binding: ReferenceBinding, *, parameter_name: str) -> dict[str, Any]:
    """Materialize a verified binding for a lowering boundary."""
    if parameter_name == "face_index":
        return {"face_index": binding.backend_index}
    if parameter_name == "edge_indices":
        return {"edge_indices": list(binding.backend_indices)}
    raise RuntimeReferenceResolutionError(f"unsupported backend parameter: {parameter_name}")


__all__ = [
    "ReferenceBinding",
    "ReferenceRequest",
    "RuntimeReferenceContextV1",
    "RuntimeReferenceResolutionError",
    "binding_to_backend_params",
]
