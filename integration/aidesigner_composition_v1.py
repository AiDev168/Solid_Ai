from __future__ import annotations

import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
    agentic_engineering_loop_cls: Any
    agentic_recovery_coordinator_cls: Any
    execution_supervisor_cls: Any


def _bootstrap_source_tree() -> Path:
    """Make separately-owned Ai_Designer source importable without copying it."""
    configured = os.getenv("AI_DESIGNER_ROOT") or os.getenv("AI_DESIGNER_SRC")

    # Explicit configuration wins. For the common sibling-repository layout,
    # fall back to ../Ai_Designer so the composed runner works without a fragile
    # environment prerequisite while keeping the two repositories separate.
    if configured:
        configured_path = Path(configured).expanduser().resolve()
    else:
        sibling = Path(__file__).resolve().parents[2] / "Ai_Designer"
        if not sibling.exists():
            raise AiDesignerCompositionError(
                "Ai_Designer source not found. Set AI_DESIGNER_ROOT to the "
                "Ai_Designer repository root (or AI_DESIGNER_SRC to its src directory)."
            )
        configured_path = sibling.resolve()
    candidates = [configured_path / "src", configured_path]
    source = next((item for item in candidates if (item / "ai_designer").is_dir()), None)
    if source is None:
        raise AiDesignerCompositionError(
            f"Ai_Designer source tree not found under {configured_path}"
        )

    # Ai_Designer has two relevant import roots on the current main layout:
    # src/ contains the ai_designer package, while repo-root contains the
    # top-level agentic package used by the existing proven repair loop.
    roots = [str(configured_path), str(source)]
    for root in roots:
        if root not in sys.path:
            sys.path.insert(0, root)
    return source


def _map_benchmark_provider_env() -> None:
    """Reuse Ai_Designer canonical gateway while accepting BENCHMARK_* variables."""
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
    """Load existing Ai_Designer components; do not reimplement them."""
    _bootstrap_source_tree()
    _map_benchmark_provider_env()
    try:
        gateway = importlib.import_module("ai_designer.llm.gateway")
        complex_pipeline = importlib.import_module("ai_designer.engineering.complex_engineering_pipeline_v1")
        front_door = importlib.import_module("ai_designer.engineering.engineering_front_door_v1")
        intake = importlib.import_module("ai_designer.engineering.engineering_intake_assessment_v1")
        planning = importlib.import_module("ai_designer.engineering.requirements_planning_v2")
        req_sp = importlib.import_module("ai_designer.engineering.requirements_solidpilot_v1")
        agentic_loop = importlib.import_module("ai_designer.agents.agentic_engineering_loop_v1")
        recovery_coordinator = importlib.import_module("ai_designer.agentic.recovery_coordinator_v1")
        supervisor = importlib.import_module("ai_designer.agentic.supervisor")
        recovery_controller = importlib.import_module("ai_designer.recovery.controller")
        recovery_registry = importlib.import_module("ai_designer.recovery.registry")
        topology_solver = importlib.import_module("ai_designer.recovery.topology_solver")
        diagnosis = importlib.import_module("ai_designer.diagnostics.diagnosis")
        repair = importlib.import_module("ai_designer.planning.execution_repair")
    except ImportError as exc:
        missing = getattr(exc, "name", None) or str(exc)
        raise AiDesignerCompositionError(
            f"Could not import canonical Ai_Designer component: {missing}; {exc}"
        ) from exc

    return AiDesignerStackV1(
        gateway_cls=gateway.LLMGateway,
        complex_pipeline_cls=complex_pipeline.ComplexEngineeringPipelineV1,
        front_door_cls=front_door.EngineeringFrontDoorV1,
        intake_assessor_cls=intake.EngineeringIntakeAssessorV1,
        requirements_planning_cls=planning.RequirementsPlanningV2,
        requirements_solidpilot_cls=req_sp.RequirementsSolidPilotV1,
        design_loop_cls=supervisor.AgenticExecutionSupervisor,
        recovery_controller_cls=recovery_controller.RecoveryController,
        recovery_registry_cls=recovery_registry.RecoverySolverRegistry,
        topology_solver_cls=topology_solver.TopologyRebindingRecoverySolver,
        diagnosis_agent_cls=diagnosis.DiagnosisAgent,
        repair_agent_cls=repair.ExecutionRepairAgent,
        agentic_engineering_loop_cls=agentic_loop.AgenticEngineeringLoopV1,
        agentic_recovery_coordinator_cls=recovery_coordinator.AgenticRecoveryCoordinatorV1,
        execution_supervisor_cls=supervisor.AgenticExecutionSupervisor,
    )


def build_canonical_gateway() -> Any:
    return load_stack().gateway_cls.from_environment()


def build_canonical_pipeline(*, solidpilot_base_url: str = "http://localhost:5000") -> Any:
    stack = load_stack()
    client_module = importlib.import_module("ai_designer.solidpilot.client")
    client = client_module.SolidPilotClient(solidpilot_base_url)
    gateway = stack.gateway_cls.from_environment()
    return stack.complex_pipeline_cls(gateway, client)


def prepare_and_plan(user_text: str, *, solidpilot_base_url: str = "http://localhost:5000", request_id: str | None = None) -> tuple[Any, Any]:
    pipeline = build_canonical_pipeline(solidpilot_base_url=solidpilot_base_url)
    request = pipeline.prepare(user_text, request_id=request_id)
    planning = pipeline.planner.plan(request)
    return request, planning


def execute_canonical(user_text: str, *, solidpilot_base_url: str = "http://localhost:5000", operation_prefix: str = "AIDESIGNER-COMPOSED") -> Any:
    pipeline = build_canonical_pipeline(solidpilot_base_url=solidpilot_base_url)
    return pipeline.execute(user_text, operation_prefix=operation_prefix)


def build_deterministic_recovery_controller() -> Any:
    stack = load_stack()
    return stack.recovery_controller_cls(_build_recovery_registry(stack))


def build_llm_recovery_coordinator(*, gateway: Any | None = None) -> Any:
    stack = load_stack()
    active_gateway = gateway or stack.gateway_cls.from_environment()
    agent = stack.agentic_engineering_loop_cls(active_gateway)
    controller = stack.recovery_controller_cls(_build_recovery_registry(stack))
    return stack.agentic_recovery_coordinator_cls(agent, controller)


def _build_recovery_registry(stack: AiDesignerStackV1) -> Any:
    registry = stack.recovery_registry_cls()
    registry.register(stack.topology_solver_cls())
    return registry


def build_design_loop(*, compile_design: Any, execute_compiled: Any, verify_result: Any, diagnose: Any, repair: Any, validate_repair: Any) -> Any:
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
    "build_llm_recovery_coordinator",
    "execute_canonical",
    "load_stack",
    "prepare_and_plan",
]