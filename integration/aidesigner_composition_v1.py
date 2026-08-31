from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class AiDesignerCompositionError(RuntimeError):
    """Raised when the canonical Ai_Designer stack cannot be reused safely."""


@dataclass(frozen=True)
class AiDesignerStackV1:
    """Canonical Ai_Designer components exposed through one integration seam."""

    gateway_cls: Any
    complex_pipeline_cls: Any
    front_door_cls: Any
    intake_assessor_cls: Any
    requirements_planning_cls: Any
    requirements_solidpilot_cls: Any
    design_loop_cls: Any
    recovery_controller_cls: Any
    recovery_registry_cls: Any
    topology_solver_cls: Any
    diagnosis_agent_cls: Any
    repair_agent_cls: Any
    legacy_repair_bridge_cls: Any


def _bootstrap_source_tree() -> Path:
    """Make the separately-owned Ai_Designer source importable without copying it."""
    configured = os.getenv("AI_DESIGNER_ROOT") or os.getenv("AI_DESIGNER_SRC")
    if not configured:
        raise AiDesignerCompositionError(
            "AI_DESIGNER_ROOT (repository root) or AI_DESIGNER_SRC must be configured"
        )

    configured_path = Path(configured).expanduser().resolve()
    candidates = [configured_path / "src", configured_path]
    source = next((item for item in candidates if (item / "ai_designer").is_dir()), None)
    if source is None:
        raise AiDesignerCompositionError(
            f"Ai_Designer source tree not found under {configured_path}"
        )
    source_text = str(source)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    return source


def _map_benchmark_provider_env() -> None:
    """Reuse Ai_Designer's canonical gateway while accepting BENCHMARK_* variables."""
    provider = os.getenv("BENCHMARK_PROVIDER", "").strip().lower()
    if provider not in {"api-provider", "external"}:
        return

    base_url = os.getenv("BENCHMARK_BASE_URL")
    model = os.getenv("BENCHMARK_MODEL")
    api_key = os.getenv("BENCHMARK_API_KEY")
    if not (base_url and model and api_key):
        raise AiDesignerCompositionError(
            "BENCHMARK_PROVIDER requires BENCHMARK_BASE_URL, BENCHMARK_MODEL and BENCHMARK_API_KEY"
        )

    os.environ.setdefault("AIDESIGNER_LLM_BASE_URL", base_url)
    os.environ.setdefault("AIDESIGNER_LLM_MODEL", model)
    os.environ.setdefault("AIDESIGNER_LLM_API_KEY", api_key)


def load_stack() -> AiDesignerStackV1:
    """Load the existing Ai_Designer brain; do not reimplement these layers."""
    _bootstrap_source_tree()
    _map_benchmark_provider_env()
    try:
        gateway = importlib.import_module("ai_designer.llm.gateway")
        complex_pipeline = importlib.import_module(
            "ai_designer.engineering.complex_engineering_pipeline_v1"
        )
        front_door = importlib.import_module(
            "ai_designer.engineering.engineering_front_door_v1"
        )
        intake = importlib.import_module(
            "ai_designer.engineering.engineering_intake_assessment_v1"
        )
        planning = importlib.import_module(
            "ai_designer.engineering.requirements_planning_v2"
        )
        req_sp = importlib.import_module(
            "ai_designer.engineering.requirements_solidpilot_v1"
        )
        design_loop = importlib.import_module("agentic.design_loop")
        recovery_controller = importlib.import_module("ai_designer.recovery.controller")
        recovery_registry = importlib.import_module("ai_designer.recovery.registry")
        topology_solver = importlib.import_module("ai_designer.recovery.topology_solver")
        diagnosis = importlib.import_module("ai_designer.diagnostics.diagnosis")
        repair = importlib.import_module("ai_designer.planning.execution_repair")
        legacy_bridge = importlib.import_module("agentic.legacy_repair_bridge")
    except ImportError as exc:
        raise AiDesignerCompositionError(
            "A canonical Ai_Designer component could not be imported"
        ) from exc

    return AiDesignerStackV1(
        gateway_cls=gateway.LLMGateway,
        complex_pipeline_cls=complex_pipeline.ComplexEngineeringPipelineV1,
        front_door_cls=front_door.EngineeringFrontDoorV1,
        intake_assessor_cls=intake.EngineeringIntakeAssessorV1,
        requirements_planning_cls=planning.RequirementsPlanningV2,
        requirements_solidpilot_cls=req_sp.RequirementsSolidPilotV1,
        design_loop_cls=design_loop.DesignIntegrationLoop,
        recovery_controller_cls=recovery_controller.RecoveryController,
        recovery_registry_cls=recovery_registry.RecoverySolverRegistry,
        topology_solver_cls=topology_solver.TopologyRebindingRecoverySolver,
        diagnosis_agent_cls=diagnosis.DiagnosisAgent,
        repair_agent_cls=repair.ExecutionRepairAgent,
        legacy_repair_bridge_cls=legacy_bridge.LegacyRepairBridge,
    )


def build_canonical_gateway() -> Any:
    return load_stack().gateway_cls.from_environment()


def build_canonical_pipeline(*, solidpilot_base_url: str = "http://localhost:5000") -> Any:
    """Build Ai_Designer's canonical NL -> Requirements -> Intent -> Planning pipeline.

    Execution stays behind the existing SolidPilot HTTP contract. No second LLM
    transport, requirements authority, or CAD execution stack is introduced here.
    """
    stack = load_stack()
    client_module = importlib.import_module("ai_designer.solidpilot.client")
    client = client_module.SolidPilotClient(solidpilot_base_url)
    gateway = stack.gateway_cls.from_environment()
    return stack.complex_pipeline_cls(gateway, client)


def prepare_and_plan(
    user_text: str,
    *,
    solidpilot_base_url: str = "http://localhost:5000",
    request_id: str | None = None,
) -> tuple[Any, Any]:
    """Return canonical validated requirements plus canonical RequirementsPlanningV2 result."""
    pipeline = build_canonical_pipeline(solidpilot_base_url=solidpilot_base_url)
    request = pipeline.prepare(user_text, request_id=request_id)
    planning = pipeline.planner.plan(request)
    return request, planning


def execute_canonical(
    user_text: str,
    *,
    solidpilot_base_url: str = "http://localhost:5000",
    operation_prefix: str = "AIDESIGNER-CANONICAL",
) -> Any:
    """Use Ai_Designer's existing RequirementsSolidPilotV1 execution seam."""
    pipeline = build_canonical_pipeline(solidpilot_base_url=solidpilot_base_url)
    return pipeline.execute(user_text, operation_prefix=operation_prefix)


def build_deterministic_recovery_controller() -> Any:
    """Reuse Ai_Designer's bounded topology recovery solver/controller."""
    stack = load_stack()
    registry = stack.recovery_registry_cls()
    registry.register(stack.topology_solver_cls())
    return stack.recovery_controller_cls(registry)


def build_llm_repair_bridge(*, gateway: Any | None = None) -> Any:
    """Reuse Ai_Designer's existing LLM diagnosis + intent-repair bridge."""
    stack = load_stack()
    active_gateway = gateway or stack.gateway_cls.from_environment()
    diagnosis_agent = stack.diagnosis_agent_cls(active_gateway)
    repair_agent = stack.repair_agent_cls(active_gateway)
    return stack.legacy_repair_bridge_cls(diagnosis_agent, repair_agent)


def build_design_loop(
    *,
    compile_design: Callable[[Any], Any],
    execute_compiled: Callable[[Any], Any],
    verify_result: Callable[[Any, Any], Any],
    diagnose: Callable[[Any, Any, Any, Any], Any],
    repair: Callable[[Any, Any], Any],
    validate_repair: Callable[[Any], bool],
) -> Any:
    """Instantiate the proven Ai_Designer PLAN -> EXECUTE -> VERIFY -> REPAIR loop.

    Callers supply the existing Solid_Ai compile/execute/verify ports; orchestration
    and retry semantics stay owned by Ai_Designer.
    """
    stack = load_stack()
    return stack.design_loop_cls(
        compile_design=compile_design,
        execute_compiled=execute_compiled,
        verify_result=verify_result,
        diagnose=diagnose,
        repair=repair,
        validate_repair=validate_repair,
    )


__all__ = [
    "AiDesignerCompositionError",
    "AiDesignerStackV1",
    "build_canonical_gateway",
    "build_canonical_pipeline",
    "build_design_loop",
    "build_deterministic_recovery_controller",
    "build_llm_repair_bridge",
    "execute_canonical",
    "load_stack",
    "prepare_and_plan",
]
