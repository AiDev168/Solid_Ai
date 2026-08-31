from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from .feature_graph_compiler_v1 import CompiledFeature, CompiledPlan, Operation, compile_feature_graph
from .feature_graph_v1 import FeatureGraph
from .runtime_reference_context_v1 import ReferenceBinding, ReferenceRequest
from .runtime_reference_resolver_v1 import RuntimeReferenceResolverV1
from .semantic_reference_lowering_v1 import materialize_plan
from .solidpilot_operation_executor_v1 import OperationResult, SolidPilotExecutionError, SolidPilotOperationExecutor, parse_solidpilot_result
from .support_reference_v1 import SketchFrame, frame_from_sketch_result


class GenericFeatureGraphRuntimeError(RuntimeError):
    pass


@dataclass
class GenericRuntimeReport:
    ok: bool = False
    executed_features: list[str] = field(default_factory=list)
    operations: list[OperationResult] = field(default_factory=list)
    bindings: dict[str, ReferenceBinding] = field(default_factory=dict)
    final_evidence: Any = None
    errors: list[str] = field(default_factory=list)


def _topological_features(graph: FeatureGraph) -> tuple[str, ...]:
    remaining = {node.feature_id: node for node in graph.features}
    ordered: list[str] = []
    while remaining:
        ready = sorted(
            node.feature_id
            for node in remaining.values()
            if all(dep not in remaining for dep in node.depends_on)
        )
        if not ready:
            raise GenericFeatureGraphRuntimeError("feature graph contains a dependency cycle")
        for feature_id in ready:
            ordered.append(feature_id)
            remaining.pop(feature_id)
    return tuple(ordered)


def _require_result_map(result: Any, tool: str) -> Mapping[str, Any]:
    if not isinstance(result, Mapping):
        raise GenericFeatureGraphRuntimeError(f"{tool}: expected structured mapping, got {type(result).__name__}")
    status = result.get("status")
    if result.get("ok") is False or status not in {"READY", "COMPLETED"}:
        raise GenericFeatureGraphRuntimeError(f"{tool}: backend rejected operation: {result}")
    return result


class GenericFeatureGraphRuntimeV1:
    """Execute a semantic FeatureGraph without feature-specific runtime classes.

    The runtime owns orchestration only. Semantic references are resolved from
    fresh SolidPilot evidence and materialized immediately before execution.
    """

    def __init__(self, session: Any):
        self.session = session
        self.executor = SolidPilotOperationExecutor(session)
        self.resolver = RuntimeReferenceResolverV1(session)
        self.report = GenericRuntimeReport()
        self._frames: dict[str, SketchFrame] = {}
        self._depths: dict[str, float] = {}

    async def _execute_operation(self, operation: Operation) -> OperationResult:
        return await self.executor.call(operation)

    async def _execute_feature(self, feature: CompiledFeature) -> None:
        for operation in feature.operations:
            result = await self._execute_operation(operation)
            self.report.operations.append(result)
            if operation.tool == "create_sketch":
                self._capture_sketch_frame(feature.feature_id, result.result)
            elif operation.tool == "extrude_feature":
                depth = operation.params.get("depth")
                if isinstance(depth, (int, float)) and not isinstance(depth, bool) and depth > 0:
                    self._depths[feature.feature_id] = float(depth)
        self.report.executed_features.append(feature.feature_id)

    def _capture_sketch_frame(self, feature_id: str, result: Any) -> None:
        if isinstance(result, Mapping):
            geometry = result.get("result_geometry")
            if isinstance(geometry, Mapping) and isinstance(geometry.get("frame"), Mapping):
                self._frames[feature_id] = frame_from_sketch_result(result)

    async def _bind_reference(self, reference: Mapping[str, Any]) -> ReferenceBinding:
        request = ReferenceRequest(
            reference_id=str(reference["reference_id"]),
            kind=str(reference["kind"]),
            role=str(reference["role"]),
            source_feature_id=str(reference["feature_id"]),
            criteria=dict(reference.get("criteria", {})),
        )
        producer = request.source_feature_id
        frame = self._frames.get(producer)
        if frame is None:
            raise GenericFeatureGraphRuntimeError(
                f"reference {request.reference_id}: no source sketch frame for {producer}"
            )
        if request.kind == "face" and request.role == "extrude_end_face":
            depth = self._depths.get(producer)
            if depth is None:
                raise GenericFeatureGraphRuntimeError(
                    f"reference {request.reference_id}: no source extrusion depth for {producer}"
                )
            return await self.resolver.bind_extrude_end_face(
                request,
                source_frame=frame,
                depth_m=depth,
            )
        if request.kind == "edge" and request.role == "outer_extrusion_boundary":
            raw = request.criteria.get("bounds_uv_m")
            if not isinstance(raw, (list, tuple)) or len(raw) != 4:
                raise GenericFeatureGraphRuntimeError(
                    f"reference {request.reference_id}: bounds_uv_m must be [umin,umax,vmin,vmax]"
                )
            bounds = tuple(float(value) for value in raw)
            return await self.resolver.bind_outer_extrusion_edges(
                request,
                source_frame=frame,
                bounds_uv=bounds,  # type: ignore[arg-type]
            )
        raise GenericFeatureGraphRuntimeError(
            f"unsupported semantic reference role: {request.kind}/{request.role}"
        )

    async def _resolve_feature_references(self, feature: CompiledFeature) -> dict[str, ReferenceBinding]:
        bindings: dict[str, ReferenceBinding] = {}
        operation_params = dict(feature.operations[0].params) if feature.operations else {}
        refs = []
        for key in ("support_reference", "selection_reference", "axis_reference"):
            value = operation_params.get(key)
            if isinstance(value, Mapping):
                refs.append(value)
            elif isinstance(value, str):
                refs.append({"reference_id": value})
        for reference in refs:
            if set(reference) == {"reference_id"}:
                raise GenericFeatureGraphRuntimeError(
                    f"reference {reference['reference_id']}: incomplete reference descriptor"
                )
            binding = await self._bind_reference(reference)
            bindings[binding.reference_id] = binding
        self.report.bindings.update(bindings)
        return bindings

    async def run(self, graph: FeatureGraph) -> GenericRuntimeReport:
        try:
            compiled = compile_feature_graph(graph)
            await self.executor.prepare()

            nodes = {node.feature_id: node for node in graph.features}
            compiled_by_id = {feature.feature_id: feature for feature in compiled.features}
            ordered = _topological_features(graph)

            for feature_id in ordered:
                feature = compiled_by_id[feature_id]
                if any(
                    isinstance(feature.operations[0].params.get(key), (Mapping, str))
                    for key in ("support_reference", "selection_reference", "axis_reference")
                ):
                    bindings = await self._resolve_feature_references(feature)
                    resolved_plan = materialize_plan(
                        CompiledPlan(graph=graph, features=(feature,)),
                        bindings,
                    )
                    feature = resolved_plan.features[0]
                await self._execute_feature(feature)

            evidence = parse_solidpilot_result(
                await self.session.call_tool("analyze_model", {"analysis_type": "geometry"})
            )
            self.report.final_evidence = _require_result_map(evidence, "analyze_model")
            self.report.ok = True
        except (GenericFeatureGraphRuntimeError, SolidPilotExecutionError, ValueError, TypeError) as exc:
            self.report.errors.append(str(exc))
        except Exception as exc:
            self.report.errors.append(f"unexpected runtime failure: {exc}")
        return self.report


__all__ = ["GenericFeatureGraphRuntimeError", "GenericFeatureGraphRuntimeV1", "GenericRuntimeReport"]
