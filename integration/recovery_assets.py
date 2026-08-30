"""Deterministic recovery assets reused from Ai_Designer.

Source lineage:
- Ai_Designer recovery/controller.py
- Ai_Designer recovery/diagnosis.py
- Ai_Designer recovery/topology_solver.py
- Ai_Designer solidpilot/topology_rebinding_v1.py
"""
from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Protocol


@dataclass(frozen=True)
class FailureDiagnosis:
    category: str
    code: str
    retryable: bool
    solver_hints: tuple[str, ...] = ()
    reason: str = ""


def diagnose_failure(*, code: str, message: str = "") -> FailureDiagnosis:
    normalized = str(code).strip().upper()
    topology = {
        "STALE_REFERENCE", "STALE_FACE_SELECTOR", "STALE_EDGE_SELECTOR",
        "TOPOLOGY_REFERENCE_INVALID", "FACE_NOT_FOUND", "EDGE_NOT_FOUND", "AXIS_NOT_FOUND",
    }
    if normalized in topology:
        return FailureDiagnosis(
            "topology", normalized, True, ("topology-rebinding-v1",),
            "refresh topology evidence and rebind the requested reference",
        )
    return FailureDiagnosis(
        "unknown", normalized, False, (),
        message or "unsupported failure; recovery is fail-closed",
    )


@dataclass(frozen=True)
class RuntimeFailure:
    code: str
    message: str
    raw: str


def _try_decode_mapping(text: str) -> Mapping[str, Any] | None:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, Mapping):
            return parsed
    except (TypeError, ValueError):
        pass
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, Mapping):
            return parsed
    except (SyntaxError, ValueError):
        pass
    return None


def _extract_mapping(text: str) -> Mapping[str, Any] | None:
    direct = _try_decode_mapping(text.strip())
    if direct is not None and ("error" in direct or "code" in direct):
        return direct

    starts = [i for i, char in enumerate(text) if char == "{"]
    candidates: list[Mapping[str, Any]] = []
    for start in reversed(starts):
        depth = 0
        quote: str | None = None
        escape = False
        for pos in range(start, len(text)):
            char = text[pos]
            if quote is not None:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    parsed = _try_decode_mapping(text[start : pos + 1])
                    if parsed is not None:
                        candidates.append(parsed)
                    break

    for candidate in candidates:
        if "error" in candidate or "code" in candidate:
            return candidate
    return candidates[0] if candidates else None


def normalize_runtime_failure(error: Any) -> RuntimeFailure:
    raw = str(error)
    payload = _extract_mapping(raw) or {}
    nested = payload.get("error", payload)
    if not isinstance(nested, Mapping):
        nested = {}
    backend_code = str(nested.get("code", "")).strip().upper()
    backend_message = str(nested.get("message", ""))
    if backend_code == "FACE_NOT_FOUND":
        return RuntimeFailure("STALE_FACE_SELECTOR", backend_message or raw, raw)
    if backend_code == "EDGE_NOT_FOUND":
        return RuntimeFailure("STALE_EDGE_SELECTOR", backend_message or raw, raw)
    if backend_code == "AXIS_NOT_FOUND":
        return RuntimeFailure("STALE_REFERENCE", backend_message or raw, raw)
    return RuntimeFailure(backend_code or "TOOL_EXECUTION_FAILED", backend_message or raw, raw)


@dataclass(frozen=True)
class TopologyAnchor:
    kind: str
    backend_index: int
    geometry: Mapping[str, Any]
    source_state_version: int


@dataclass(frozen=True)
class TopologyBinding:
    kind: str
    backend_index: int
    source_backend_index: int
    source_state_version: int
    target_state_version: int
    distance: float


def _vec(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return None
    try:
        return float(value[0]), float(value[1]), float(value[2])
    except (TypeError, ValueError):
        return None


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def _unit(value: Sequence[float]) -> tuple[float, float, float] | None:
    norm = sqrt(sum(float(x) ** 2 for x in value))
    if norm <= 1e-12:
        return None
    return tuple(float(x) / norm for x in value)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _edge_score(anchor: Mapping[str, Any], candidate: Mapping[str, Any]) -> float | None:
    if anchor.get("kind") != "edge" or candidate.get("kind") != "edge":
        return None
    score = 0.0
    compared = 0
    amid = _vec(anchor.get("mid") or anchor.get("midpoint"))
    cmid = _vec(candidate.get("mid") or candidate.get("midpoint"))
    if amid is not None and cmid is not None:
        d = _distance(amid, cmid)
        if d > 1e-6:
            return None
        score += d / 1e-6
        compared += 1
    astart, aend = _vec(anchor.get("start")), _vec(anchor.get("end"))
    cstart, cend = _vec(candidate.get("start")), _vec(candidate.get("end"))
    if astart and aend and cstart and cend:
        d = min(
            _distance(astart, cstart) + _distance(aend, cend),
            _distance(astart, cend) + _distance(aend, cstart),
        )
        if d > 2e-6:
            return None
        score += d / 1e-6
        compared += 1
    if anchor.get("length") is not None and candidate.get("length") is not None:
        d = abs(float(anchor["length"]) - float(candidate["length"]))
        tol = 1e-6 * max(1.0, abs(float(anchor["length"])), abs(float(candidate["length"])))
        if d > tol:
            return None
        score += d / tol
        compared += 1
    return score if compared else None


def _face_score(anchor: Mapping[str, Any], candidate: Mapping[str, Any]) -> float | None:
    if anchor.get("kind") != "face" or candidate.get("kind") != "face":
        return None
    if anchor.get("surface_kind") and candidate.get("surface_kind") and anchor["surface_kind"] != candidate["surface_kind"]:
        return None
    score = 0.0
    compared = 0
    if "planar" in anchor and "planar" in candidate:
        if bool(anchor["planar"]) != bool(candidate["planar"]):
            return None
        compared += 1
    for key in ("origin", "point"):
        av, cv = _vec(anchor.get(key)), _vec(candidate.get(key))
        if av is not None and cv is not None:
            d = _distance(av, cv)
            if d > 1e-6:
                return None
            score += d / 1e-6
            compared += 1
            break
    an, cn = _unit(_vec(anchor.get("normal")) or ()), _unit(_vec(candidate.get("normal")) or ())
    if an is not None and cn is not None:
        angular = 1.0 - abs(_dot(an, cn))
        if angular > 1e-8:
            return None
        score += angular / 1e-8
        compared += 1
    aa, ca = _unit(_vec(anchor.get("axis")) or ()), _unit(_vec(candidate.get("axis")) or ())
    if anchor.get("axis") is not None and candidate.get("axis") is not None:
        if aa is None or ca is None or 1.0 - abs(_dot(aa, ca)) > 1e-8:
            return None
        compared += 1
    if anchor.get("radius") is not None and candidate.get("radius") is not None:
        av, cv = float(anchor["radius"]), float(candidate["radius"])
        tol = 1e-6 * max(1.0, abs(av), abs(cv))
        if abs(av - cv) > tol:
            return None
        score += abs(av - cv) / tol
        compared += 1
    if anchor.get("area") is not None and candidate.get("area") is not None:
        av, cv = float(anchor["area"]), float(candidate["area"])
        tol = 1e-4 * max(1.0, abs(av), abs(cv))
        score += min(abs(av - cv) / tol, 10.0)
        compared += 1
    return score if compared else None


def make_anchor(candidate: Mapping[str, Any], *, source_state_version: int) -> TopologyAnchor:
    kind = str(candidate.get("kind", ""))
    index = candidate.get("backend_index", candidate.get("i"))
    if kind not in {"face", "edge"} or not isinstance(index, int):
        raise ValueError("candidate requires kind=face|edge and integer backend index")
    return TopologyAnchor(kind, index, dict(candidate), source_state_version)


def rebind_anchor(
    anchor: TopologyAnchor,
    candidates: Sequence[Mapping[str, Any]],
    *,
    target_state_version: int,
) -> TopologyBinding:
    scored: list[tuple[float, Mapping[str, Any]]] = []
    for candidate in candidates:
        if candidate.get("kind") != anchor.kind:
            continue
        score = _edge_score(anchor.geometry, candidate) if anchor.kind == "edge" else _face_score(anchor.geometry, candidate)
        if score is not None:
            scored.append((score, candidate))
    if not scored:
        raise ValueError(f"no {anchor.kind} candidate matches the anchor")
    scored.sort(key=lambda item: item[0])
    best_score, best = scored[0]
    if len(scored) > 1 and abs(scored[1][0] - best_score) <= 1e-9:
        raise ValueError(f"ambiguous {anchor.kind} rebinding")
    index = best.get("backend_index", best.get("i"))
    if not isinstance(index, int):
        raise ValueError("matched candidate has no integer backend index")
    return TopologyBinding(anchor.kind, index, anchor.backend_index, anchor.source_state_version, target_state_version, best_score)


@dataclass(frozen=True)
class RecoveryRequest:
    category: str
    failure: str
    evidence: Any = None
    max_attempts: int = 1


@dataclass(frozen=True)
class RecoveryAttempt:
    solver: str
    success: bool
    result: Any


@dataclass(frozen=True)
class RecoveryResult:
    recovered: bool
    attempts: tuple[RecoveryAttempt, ...] = field(default_factory=tuple)


class RecoverySolver(Protocol):
    name: str
    categories: frozenset[str]
    def can_handle(self, category: str, evidence: Any) -> bool: ...
    def recover(self, request: RecoveryRequest) -> Any: ...


class RecoveryRegistry:
    def __init__(self) -> None:
        self._solvers: dict[str, RecoverySolver] = {}
    def register(self, solver: RecoverySolver) -> None:
        if not solver.name or not solver.categories or solver.name in self._solvers:
            raise ValueError(f"invalid or duplicate solver: {solver.name}")
        self._solvers[solver.name] = solver
    def select(self, category: str, evidence: Any) -> RecoverySolver:
        matches = [s for s in self._solvers.values() if category in s.categories and s.can_handle(category, evidence)]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one recovery solver for {category}, found {len(matches)}")
        return matches[0]


@dataclass(frozen=True)
class TopologyRecoveryEvidence:
    edge_anchor: TopologyAnchor | None = None
    edge_candidates: Sequence[Mapping[str, Any]] = ()
    face_anchor: TopologyAnchor | None = None
    face_candidates: Sequence[Mapping[str, Any]] = ()
    target_edge_state_version: int | None = None
    target_face_state_version: int | None = None


@dataclass(frozen=True)
class TopologyRecoveryResult:
    recovered: bool
    face_binding: TopologyBinding | None = None
    edge_binding: TopologyBinding | None = None
    error: str | None = None


class TopologyRecoverySolver:
    name = "topology-rebinding-v1"
    categories = frozenset({"topology"})
    def can_handle(self, category: str, evidence: Any) -> bool:
        return category == "topology" and isinstance(evidence, TopologyRecoveryEvidence) and bool((evidence.edge_anchor and evidence.edge_candidates) or (evidence.face_anchor and evidence.face_candidates))
    def recover(self, request: RecoveryRequest) -> TopologyRecoveryResult:
        ev = request.evidence
        if not isinstance(ev, TopologyRecoveryEvidence):
            return TopologyRecoveryResult(False, error="invalid topology evidence")
        try:
            edge_binding = None
            face_binding = None
            if ev.edge_anchor:
                if ev.target_edge_state_version is None:
                    return TopologyRecoveryResult(False, error="missing target edge state_version")
                edge_binding = rebind_anchor(ev.edge_anchor, ev.edge_candidates, target_state_version=ev.target_edge_state_version)
            if ev.face_anchor:
                if ev.target_face_state_version is None:
                    return TopologyRecoveryResult(False, error="missing target face state_version")
                face_binding = rebind_anchor(ev.face_anchor, ev.face_candidates, target_state_version=ev.target_face_state_version)
            return TopologyRecoveryResult(True, face_binding=face_binding, edge_binding=edge_binding)
        except ValueError as exc:
            return TopologyRecoveryResult(False, error=str(exc))


class RecoveryController:
    def __init__(self, registry: RecoveryRegistry):
        self.registry = registry
    def recover(self, request: RecoveryRequest) -> RecoveryResult:
        if request.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        solver = self.registry.select(request.category, request.evidence)
        attempts: list[RecoveryAttempt] = []
        for _ in range(request.max_attempts):
            result = solver.recover(request)
            success = bool(getattr(result, "recovered", False))
            attempts.append(RecoveryAttempt(solver.name, success, result))
            if success:
                return RecoveryResult(True, tuple(attempts))
        return RecoveryResult(False, tuple(attempts))
    def diagnose_and_recover(self, *, code: str, message: str = "", evidence: Any = None, max_attempts: int = 1) -> tuple[FailureDiagnosis, RecoveryResult | None]:
        diagnosis = diagnose_failure(code=code, message=message)
        if not diagnosis.retryable:
            return diagnosis, None
        return diagnosis, self.recover(RecoveryRequest(diagnosis.category, diagnosis.code, evidence, max_attempts))


class RecoveryAssets:
    def __init__(self) -> None:
        self.registry = RecoveryRegistry()
        self.registry.register(TopologyRecoverySolver())
        self.controller = RecoveryController(self.registry)


__all__ = [
    "FailureDiagnosis", "RuntimeFailure", "RecoveryAssets", "RecoveryAttempt", "RecoveryController", "RecoveryRegistry", "RecoveryRequest", "RecoveryResult", "TopologyAnchor", "TopologyBinding", "TopologyRecoveryEvidence", "TopologyRecoveryResult", "TopologyRecoverySolver", "diagnose_failure", "make_anchor", "normalize_runtime_failure", "rebind_anchor",
]
