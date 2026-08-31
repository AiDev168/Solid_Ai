from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

import integration.aidesigner_composition_v1 as bridge


def test_provider_environment_mapping(monkeypatch):
    monkeypatch.setenv("BENCHMARK_PROVIDER", "api-provider")
    monkeypatch.setenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
    monkeypatch.setenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
    monkeypatch.setenv("BENCHMARK_API_KEY", "secret")
    for key in ("AIDESIGNER_LLM_BASE_URL", "AIDESIGNER_LLM_MODEL", "AIDESIGNER_LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    bridge._map_benchmark_provider_env()

    assert os.environ["AIDESIGNER_LLM_BASE_URL"] == "https://api.gapgpt.app/v1"
    assert os.environ["AIDESIGNER_LLM_MODEL"] == "gapgpt-qwen-3.5"
    assert os.environ["AIDESIGNER_LLM_API_KEY"] == "secret"


def test_bootstrap_finds_ai_designer_source(monkeypatch, tmp_path: Path):
    source_root = tmp_path / "Ai_Designer" / "src"
    (source_root / "ai_designer").mkdir(parents=True)
    monkeypatch.setenv("AI_DESIGNER_ROOT", str(source_root.parent))

    resolved = bridge._bootstrap_source_tree()

    assert resolved == source_root
    assert str(source_root) in sys.path


def test_load_stack_requires_canonical_assets(monkeypatch):
    modules: dict[str, types.ModuleType] = {}

    def add(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        if name in {
            "ai_designer",
            "ai_designer.llm",
            "ai_designer.engineering",
            "ai_designer.recovery",
            "ai_designer.diagnostics",
            "ai_designer.planning",
            "ai_designer.agentic",
            "ai_designer.agents",
            "agentic",
        }:
            module.__path__ = []
        modules[name] = module
        monkeypatch.setitem(sys.modules, name, module)
        return module

    ai = add("ai_designer")
    agentic_pkg = add("ai_designer.agentic")
    agents = add("ai_designer.agents")
    llm = add("ai_designer.llm")
    gateway = add("ai_designer.llm.gateway")
    engineering = add("ai_designer.engineering")
    names = (
        "complex_engineering_pipeline_v1",
        "engineering_front_door_v1",
        "engineering_intake_assessment_v1",
        "requirements_planning_v2",
        "requirements_solidpilot_v1",
    )
    engineering_modules = {name: add(f"ai_designer.engineering.{name}") for name in names}
    agentic = add("agentic")
    agentic_loop = add("ai_designer.agents.agentic_engineering_loop_v1")
    recovery_coordinator = add("ai_designer.agentic.recovery_coordinator_v1")
    supervisor = add("ai_designer.agentic.supervisor")
    recovery = add("ai_designer.recovery")
    recovery_controller = add("ai_designer.recovery.controller")
    recovery_registry = add("ai_designer.recovery.registry")
    topology = add("ai_designer.recovery.topology_solver")
    diagnosis = add("ai_designer.diagnostics.diagnosis")
    diagnostics = add("ai_designer.diagnostics")
    planning = add("ai_designer.planning")
    repair = add("ai_designer.planning.execution_repair")

    class LLMGateway: pass
    class ComplexPipeline: pass
    class FrontDoor: pass
    class Intake: pass
    class Planning: pass
    class ReqSP: pass
    class AgenticLoop: pass
    class RecoveryCoordinator: pass
    class Supervisor: pass
    class RecoveryController: pass
    class RecoveryRegistry: pass
    class TopologySolver: pass
    class Diagnosis: pass
    class Repair: pass

    gateway.LLMGateway = LLMGateway
    engineering_modules["complex_engineering_pipeline_v1"].ComplexEngineeringPipelineV1 = ComplexPipeline
    engineering_modules["engineering_front_door_v1"].EngineeringFrontDoorV1 = FrontDoor
    engineering_modules["engineering_intake_assessment_v1"].EngineeringIntakeAssessorV1 = Intake
    engineering_modules["requirements_planning_v2"].RequirementsPlanningV2 = Planning
    engineering_modules["requirements_solidpilot_v1"].RequirementsSolidPilotV1 = ReqSP
    agentic_loop.AgenticEngineeringLoopV1 = AgenticLoop
    recovery_coordinator.AgenticRecoveryCoordinatorV1 = RecoveryCoordinator
    supervisor.AgenticExecutionSupervisor = Supervisor
    recovery_controller.RecoveryController = RecoveryController
    recovery_registry.RecoverySolverRegistry = RecoveryRegistry
    topology.TopologyRebindingRecoverySolver = TopologySolver
    diagnosis.DiagnosisAgent = Diagnosis
    repair.ExecutionRepairAgent = Repair

    for parent, child in (
        (ai, "llm"),
        (ai, "engineering"),
        (ai, "recovery"),
        (ai, "agentic"),
        (llm, "gateway"),
        (engineering, "complex_engineering_pipeline_v1"),
        (engineering, "engineering_front_door_v1"),
        (engineering, "engineering_intake_assessment_v1"),
        (engineering, "requirements_planning_v2"),
        (engineering, "requirements_solidpilot_v1"),
        (agentic_pkg, "recovery_coordinator_v1"),
        (agentic_pkg, "supervisor"),
        (ai, "agents"),
        (recovery, "controller"),
        (recovery, "registry"),
        (recovery, "topology_solver"),
        (ai, "diagnostics"),
        (ai, "planning"),
        (agents, "agentic_engineering_loop_v1"),
    ):
        setattr(parent, child.split(".")[-1], modules[f"{parent.__name__}.{child}"])

    # This test isolates stack loading from provider qualification. The real
    # runtime must still require an explicitly configured provider.
    monkeypatch.setattr(bridge, "_bootstrap_source_tree", lambda: Path("."))
    monkeypatch.delenv("BENCHMARK_PROVIDER", raising=False)
    monkeypatch.setenv("AIDESIGNER_LLM_BASE_URL", "http://test-provider/v1")
    monkeypatch.setenv("AIDESIGNER_LLM_MODEL", "test-model")
    monkeypatch.setenv("AIDESIGNER_LLM_API_KEY", "test-key")

    stack = bridge.load_stack()

    assert stack.gateway_cls is LLMGateway
    assert stack.complex_pipeline_cls is ComplexPipeline
    assert stack.requirements_planning_cls is Planning
    assert stack.requirements_solidpilot_cls is ReqSP
    assert stack.design_loop_cls is Supervisor
    assert stack.recovery_controller_cls is RecoveryController
    assert stack.recovery_registry_cls is RecoveryRegistry
    assert stack.topology_solver_cls is TopologySolver
    assert stack.diagnosis_agent_cls is Diagnosis
    assert stack.repair_agent_cls is Repair
    assert stack.agentic_engineering_loop_cls is AgenticLoop
    assert stack.agentic_recovery_coordinator_cls is RecoveryCoordinator
    assert stack.execution_supervisor_cls is Supervisor


def test_llm_configuration_requires_explicit_provider(monkeypatch):
    for key in (
        "AIDESIGNER_LLM_BASE_URL",
        "AIDESIGNER_LLM_MODEL",
        "AIDESIGNER_LLM_API_KEY",
        "BENCHMARK_PROVIDER",
        "BENCHMARK_BASE_URL",
        "BENCHMARK_MODEL",
        "BENCHMARK_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("SOLID_AI_ALLOW_LMSTUDIO", raising=False)

    with pytest.raises(
        bridge.AiDesignerCompositionError,
        match="No canonical external LLM is configured",
    ):
        bridge._validate_llm_configuration()


def test_llm_configuration_allows_explicit_lmstudio_fallback(monkeypatch):
    for key in (
        "AIDESIGNER_LLM_BASE_URL",
        "AIDESIGNER_LLM_MODEL",
        "AIDESIGNER_LLM_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SOLID_AI_ALLOW_LMSTUDIO", "1")

    bridge._validate_llm_configuration()


def test_benchmark_provider_overwrites_stale_aidesigner_provider(monkeypatch):
    monkeypatch.setenv("BENCHMARK_PROVIDER", "api-provider")
    monkeypatch.setenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
    monkeypatch.setenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
    monkeypatch.setenv("BENCHMARK_API_KEY", "secret")
    monkeypatch.setenv("AIDESIGNER_LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("AIDESIGNER_LLM_MODEL", "stale-local-model")
    monkeypatch.setenv("AIDESIGNER_LLM_API_KEY", "stale")

    bridge._map_benchmark_provider_env()

    assert os.environ["AIDESIGNER_LLM_BASE_URL"] == "https://api.gapgpt.app/v1"
    assert os.environ["AIDESIGNER_LLM_MODEL"] == "gapgpt-qwen-3.5"
    assert os.environ["AIDESIGNER_LLM_API_KEY"] == "secret"
