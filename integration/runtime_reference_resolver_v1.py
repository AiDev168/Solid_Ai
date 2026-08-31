from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .runtime_reference_context_v1 import (
    ReferenceBinding,
    ReferenceRequest,
    RuntimeReferenceContextV1,
    RuntimeReferenceResolutionError,
)
from .support_reference_v1 import SketchFrame


class ReferenceResolverExecutionError(RuntimeError):
    """Raised when fresh backend evidence cannot be collected or resolved."""


class AsyncReferenceSession(Protocol):
    async def call_tool(self, name: str, arguments: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True)
class EvidenceBundle:
    kind: str
    state_version: int
    items: tuple[Mapping[str, Any], ...]



def _parse_response(response: Any) -> Mapping[str, Any]:
    if getattr(response, "isError", False):
        raise ReferenceResolverExecutionError(str(response))
    structured = getattr(response, "structuredContent", None)
    if isinstance(structured, Mapping) and "result" in structured:
        value = structured["result"]
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ReferenceResolverExecutionError(
                    "SolidPilot returned non-JSON structured result"
                ) from exc
        if isinstance(value, Mapping):
            return value
    for item in getattr(response, "content", ()) or ():
        text = getattr(item, "text", None)
        if isinstance(text, str):
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(value, Mapping):
                return value
    raise ReferenceResolverExecutionError("SolidPilot response contained no structured mapping")


def _evidence_items(result: Mapping[str, Any], kind: str) -> EvidenceBundle:
    data = result.get("data")
    if not isinstance(data, Mapping):
        raise ReferenceResolverExecutionError(f"analyze_model returned no {kind} evidence data")
    raw = data.get(f"{kind}s")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ReferenceResolverExecutionError(f"analyze_model returned no indexed {kind}s")
    state_version = result.get("state_version")
    if not isinstance(state_version, int):
        raise ReferenceResolverExecutionError("analyze_model returned no integer state_version")
    items = tuple(item for item in raw if isinstance(item, Mapping))
    return EvidenceBundle(kind, state_version, items)


class RuntimeReferenceResolverV1:
    """Collect fresh SolidPilot evidence and bind semantic references.

    The resolver owns backend evidence acquisition only. Geometry semantics stay
    inside RuntimeReferenceContextV1 and its underlying reference solvers.
    """

    def __init__(self, session: AsyncReferenceSession, *, context: RuntimeReferenceContextV1 | None = None):
        self.session = session
        self.context = context or RuntimeReferenceContextV1()

    async def fresh_evidence(self, kind: str) -> EvidenceBundle:
        if kind not in {"face", "edge"}:
            raise ReferenceResolverExecutionError(f"unsupported evidence kind: {kind}")
        result = _parse_response(
            await self.session.call_tool("analyze_model", {"analysis_type": f"{kind}s"})
        )
        return _evidence_items(result, kind)

    async def bind_extrude_end_face(
        self,
        request: ReferenceRequest,
        *,
        source_frame: SketchFrame,
        depth_m: float,
    ) -> ReferenceBinding:
        evidence = await self.fresh_evidence("face")
        try:
            return self.context.bind_extrude_end_face(
                request,
                faces=evidence.items,
                source_frame=source_frame,
                depth_m=depth_m,
                state_version=evidence.state_version,
            )
        except RuntimeReferenceResolutionError as exc:
            raise ReferenceResolverExecutionError(str(exc)) from exc

    async def bind_outer_extrusion_edges(
        self,
        request: ReferenceRequest,
        *,
        source_frame: SketchFrame,
        bounds_uv: tuple[float, float, float, float],
    ) -> ReferenceBinding:
        evidence = await self.fresh_evidence("edge")
        try:
            return self.context.bind_outer_extrusion_edges(
                request,
                edges=evidence.items,
                source_frame=source_frame,
                bounds_uv=bounds_uv,
                state_version=evidence.state_version,
            )
        except RuntimeReferenceResolutionError as exc:
            raise ReferenceResolverExecutionError(str(exc)) from exc


__all__ = [
    "EvidenceBundle",
    "ReferenceResolverExecutionError",
    "RuntimeReferenceResolverV1",
]
