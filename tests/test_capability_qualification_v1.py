import asyncio

from integration.capability_qualification_v1 import (
    QualificationHarnessV1,
    QualificationScenario,
    build_core_modeling_scenarios,
)


def test_core_modeling_matrix_is_not_empty_and_has_distinct_families():
    scenarios = build_core_modeling_scenarios()
    assert len(scenarios) >= 8
    assert len({s.scenario_id for s in scenarios}) == len(scenarios)
    assert len({s.family for s in scenarios}) >= 5


def test_harness_can_filter_by_capability_without_running_backend():
    harness = QualificationHarnessV1(build_core_modeling_scenarios())
    selected = harness.plan(capability_ids={"part.cut_extrude", "edge.chamfer"})
    assert [item.capability_id for item in selected] == ["part.cut_extrude", "edge.chamfer"]


def test_failed_execution_is_not_promotion_eligible():
    result = harness_result(status="failed", evidence={"ok": False, "verified": False})
    assert QualificationHarnessV1.promotion_eligible(result) is False


def test_verified_execution_with_explicit_verification_is_promotion_eligible():
    result = harness_result(status="verified", evidence={"ok": True, "verified": True})
    assert QualificationHarnessV1.promotion_eligible(result) is True


def test_harness_executes_each_selected_scenario_and_captures_evidence():
    harness = QualificationHarnessV1(build_core_modeling_scenarios())

    class FakeExecutor:
        async def execute(self, scenario):
            return {"ok": True, "verified": True, "scenario_id": scenario.scenario_id}

    results = asyncio.run(harness.run(FakeExecutor(), capability_ids={"part.cut_extrude", "sketch.arc"}))
    assert [r.scenario_id for r in results] == ["Q-CUT-001", "Q-SKETCH-002"]
    assert all(r.status == "verified" for r in results)


def harness_result(*, status, evidence):
    from integration.capability_qualification_v1 import QualificationResult

    return QualificationResult(
        scenario_id="T",
        capability_id="test",
        status=status,
        evidence=evidence,
    )
