from __future__ import annotations

import sys
import types

import pytest

import integration.aidesigner_composition_v1 as bridge


@pytest.fixture
def fake_aidesigner_modules(monkeypatch):
    modules: dict[str, types.ModuleType] = {}

    def module(name: str) -> types.ModuleType:
        item = types.ModuleType(name)
        modules[name] = item
        monkeypatch.setitem(sys.modules, name, item)
        return item

    root = module("ai_designer")
    llm = module("ai_designer.llm")
    gateway_mod = module("ai_designer.llm.gateway")
    engineering = module("ai_designer.engineering")
    complex_mod = module("ai_designer.engineering.complex_engineering_pipeline_v1")
    front_mod = module("ai_designer.engineering.engineering_front_door_v1")
    intake_mod = module("ai_designer.engineering.engineering_intake_assessment_v1")
    planning_mod = module("ai_designer.engineering.requirements_planning_v2")
    req_sp_mod = module("ai_designer.engineering.requirements_solidpilot_v1")
    agentic = module("agentic")
    design_loop_mod = module("agentic.design_loop")
    legacy_mod = module("agentic.legacy_repair_bridge")
    recovery = module("ai_designer.recovery")
    recovery_controller_mod = module("ai_designer.recovery.controller")
    recovery_registry_mod = module("ai_designer.recovery.registry")

    solidpilot = module("ai_designer.solidpilot")
    client_mod = module("ai_designer.solidpilot.client")

    class LLMGateway:  # pragma: no cover - shape-only fake
        @classmethod
        def from_environment(cls):
            return object()

    class ComplexPipeline:
        def __init__(self, gateway, client):
            self.gateway = gateway
            self.client = client

    class FrontDoor: ...
    class IntakeAssessor: ...
    class Planning: ...
    class RequirementsSolidPilot: ...
    class DesignLoop: ...
    class RecoveryController: ...
    class RecoveryRegistry: ...
    class LegacyRepairBridge: ...
    class SolidPilotClient:
        def __init__(self, base_url):
            self.base_url = base_url

    gateway_mod.LLMGateway = LLMGateway
    complex_mod.ComplexEngineeringPipelineV1 = ComplexPipeline
    front_mod.EngineeringFrontDoorV1 = FrontDoor
    intake_mod.EngineeringIntakeAssessorV1 = IntakeAssessor
    planning_mod.RequirementsPlanningV2 = Planning
    req_sp_mod.RequirementsSolidPilotV1 = RequirementsSolidPilot
    design_loop_mod.DesignIntegrationLoop = DesignLoop
    recovery_controller_mod.RecoveryController = RecoveryController
    recovery_registry_mod.RecoverySolverRegistry = RecoveryRegistry
    legacy_mod.LegacyRepairBridge = LegacyRepairBridge
    client_mod.SolidPilotClient = SolidPilotClient

    for parent, child_name in [
        (root, "llm"),
        (root, "engineering"),
        (root, "recovery"),
        (root, "solidpilot"),
        (llm, "gateway"),
        (engineering, "complex_engineering_pipeline_v1"),
        (engineering, "engineering_front_door_v1"),
        (engineering, "engineering_intake_assessment_v1"),
        (engineering, "requirements_planning_v2"),
        (engineering, "requirements_solidpilot_v1"),
        (agentic, "design_loop"),
        (agentic, "legacy_repair_bridge"),
        (recovery, "controller"),
        (recovery, "registry"),
        (solidpilot, "client"),
    ]:
        setattr(parent, child_name.split(".")[-1], modules[
            f"{parent.__name__}.{child_name}"
        ])

    return modules


def test_benchmark_provider_maps_to_canonical_gateway_environment(monkeypatch):
    monkeypatch.setenv("BENCHMARK_PROVIDER", "api-provider")
    monkeypatch.setenv("BENCHMARK_BASE_URL", "https://api.gapgpt.app/v1")
    monkeypatch.setenv("BENCHMARK_MODEL", "gapgpt-qwen-3.5")
    monkeypatch.setenv("BENCHMARK_API_KEY", "secret")
    monkeypatch.delenv("AIDESIGNER_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("AIDESIGNER_LLM_MODEL", raising=False)
    monkeypatch.delenv("AIDESIGNER_LLM_API_KEY", raising=False)

    bridge._map_benchmark_provider_env()

    assert bridge.os.environ["AIDESIGNER_LLM_BASE_URL"] == "https://api.gapgpt.app/v1"
    assert bridge.os.environ["AIDESIGNER_LLM_MODEL"] == "gapgpt-qwen-3.5"
    assert bridge.os.environ["AIDESIGNER_LLM_API_KEY"] == "secret"


def test_load_stack_exposes_canonical_semantic_planning_and_recovery_assets(
    monkeypatch, fake_aidesigner_modules
):
    source = monkeypatch.chdir
    del source
    monkeypatch.setenv("AI_DESIGNER_ROOT", ".")
    monkeypatch.setattr(bridge, "_bootstrap_source_tree", lambda: __import__("pathlib").Path("."))
    stack = bridge.load_stack()

    assert stack.gateway_cls.__name__ == "LLMGateway"
    assert stack.complex_pipeline_cls.__name__ == "ComplexPipeline"
    assert stack.requirements_planning_cls.__name__ == "Planning"
    assert stack.requirements_solidpilot_cls.__name__ == "RequirementsSolidPilot"
    assert stack.design_loop_cls.__name__ == "DesignLoop"
    assert stack.recovery_controller_cls.__name__ == "RecoveryController"
    assert stack.recovery_registry_cls.__name__ == "RecoveryRegistry"
    assert stack.legacy_repair_bridge_cls.__name__ == "LegacyRepairBridge"


def test_canonical_pipeline_uses_ai_designer_client_at_existing_solidpilot_boundary(
    monkeypatch, fake_aidesigner_modules
):
    monkeypatch.setenv("AI_DESIGNER_ROOT", ".")
    monkeypatch.setattr(bridge, "_bootstrap_source_tree", lambda: __import__("pathlib").Path("."))
    pipeline = bridge.build_canonical_pipeline(solidpilot_base_url="http://localhost:5000")

    assert pipeline.__class__.__name__ == "ComplexPipeline"
    assert pipeline.client.base_url == "http://localhost:5000"
