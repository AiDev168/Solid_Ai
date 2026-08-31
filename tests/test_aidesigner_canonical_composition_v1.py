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
            "agentic",
        }:
            module.__path__ = []
        modules[name] = module
        monkeypatch.setitem(sys.modules, name, module)
        return module

    ai = add("ai_designer")
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
    design_loop = add("agentic.design_loop")
    recovery = add("ai_designer.recovery")
    recovery_controller = add("ai_designer.recovery.controller")
    recovery_registry = add("ai_designer.recovery.registry")
    topology = add("ai_designer.recovery.topology_solver")
    diagnosis = add("ai_designer.diagnostics.diagnosis")
    diagnostics = add("ai_designer.diagnostics")
    planning = add("ai_designer.planning")
    repair = add("ai_designer.planning.execution_repair")
    legacy = add("agentic.legacy_repair_bridge")

    class LLMGateway: pass
    class ComplexPipeline: pass
    class FrontDoor: pass
    class Intake: pass
    class Planning: pass
    class ReqSP: pass
    class DesignLoop: pass
    class RecoveryController: pass
    class RecoveryRegistry: pass
    class TopologySolver: pass
    class Diagnosis: pass
    class Repair: pass
    class Legacy: pass

    gateway.LLMGateway = LLMGateway
    engineering_modules["complex_engineering_pipeline_v1"].ComplexEngineeringPipelineV1 = ComplexPipeline
    engineering_modules["engineering_front_door_v1"].EngineeringFrontDoorV1 = FrontDoor
    engineering_modules["engineering_intake_assessment_v1"].EngineeringIntakeAssessorV1 = Intake
    engineering_modules["requirements_planning_v2"].RequirementsPlanningV2 = Planning
    engineering_modules["requirements_solidpilot_v1"].RequirementsSolidPilotV1 = ReqSP
    design_loop.DesignIntegrationLoop = DesignLoop
    recovery_controller.RecoveryController = RecoveryController
    recovery_registry.RecoverySolverRegistry = RecoveryRegistry
    topology.TopologyRebindingRecoverySolver = TopologySolver
    diagnosis.DiagnosisAgent = Diagnosis
    repair.ExecutionRepairAgent = Repair
    legacy.LegacyRepairBridge = Legacy

    for parent, child in (
        (ai, "llm"),
        (ai, "engineering"),
        (ai, "recovery"),
        (llm, "gateway"),
        (engineering, "complex_engineering_pipeline_v1"),
        (engineering, "engineering_front_door_v1"),
        (engineering, "engineering_intake_assessment_v1"),
        (engineering, "requirements_planning_v2"),
        (engineering, "requirements_solidpilot_v1"),
        (agentic, "design_loop"),
        (recovery, "controller"),
        (recovery, "registry"),
        (recovery, "topology_solver"),
        (ai, "diagnostics"),
        (ai, "planning"),
    ):
        setattr(parent, child.split(".")[-1], modules[f"{parent.__name__}.{child}"])

    monkeypatch.setattr(bridge, "_bootstrap_source_tree", lambda: Path("."))
    monkeypatch.delenv("BENCHMARK_PROVIDER", raising=False)

    stack = bridge.load_stack()

    assert stack.gateway_cls is LLMGateway
    assert stack.complex_pipeline_cls is ComplexPipeline
    assert stack.requirements_planning_cls is Planning
    assert stack.requirements_solidpilot_cls is ReqSP
    assert stack.design_loop_cls is DesignLoop
    assert stack.recovery_controller_cls is RecoveryController
    assert stack.recovery_registry_cls is RecoveryRegistry
    assert stack.topology_solver_cls is TopologySolver
    assert stack.diagnosis_agent_cls is Diagnosis
    assert stack.repair_agent_cls is Repair
    assert stack.legacy_repair_bridge_cls is Legacy
