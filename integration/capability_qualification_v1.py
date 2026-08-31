from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class QualificationScenario:
    scenario_id: str
    capability_id: str
    family: str
    title: str
    purpose: str
    operations: tuple[Mapping[str, Any], ...]
    verification: tuple[str, ...]
    promotion_target: str = "proven"


@dataclass(frozen=True)
class QualificationResult:
    scenario_id: str
    capability_id: str
    status: str
    evidence: Mapping[str, Any] | None = None
    error: str | None = None


class QualificationExecutor(Protocol):
    async def execute(self, scenario: QualificationScenario) -> Mapping[str, Any]: ...


class QualificationHarnessV1:
    def __init__(self, scenarios: Sequence[QualificationScenario]) -> None:
        self._scenarios = tuple(scenarios)

    @property
    def scenarios(self) -> tuple[QualificationScenario, ...]:
        return self._scenarios

    def plan(self, *, capability_ids: set[str] | None = None) -> list[QualificationScenario]:
        if capability_ids is None:
            return list(self._scenarios)
        return [s for s in self._scenarios if s.capability_id in capability_ids or s.scenario_id in capability_ids]

    async def run(
        self,
        executor: QualificationExecutor,
        *,
        capability_ids: set[str] | None = None,
    ) -> list[QualificationResult]:
        results: list[QualificationResult] = []
        for scenario in self.plan(capability_ids=capability_ids):
            try:
                evidence = await executor.execute(scenario)
                results.append(
                    QualificationResult(
                        scenario_id=scenario.scenario_id,
                        capability_id=scenario.capability_id,
                        status="verified" if evidence.get("ok") else "failed",
                        evidence=evidence,
                    )
                )
            except Exception as exc:  # pragma: no cover - integration boundary
                results.append(
                    QualificationResult(
                        scenario_id=scenario.scenario_id,
                        capability_id=scenario.capability_id,
                        status="failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
        return results

    @staticmethod
    def promotion_eligible(result: QualificationResult) -> bool:
        return result.status == "verified" and isinstance(result.evidence, Mapping) and bool(result.evidence.get("verified"))

    @staticmethod
    def to_dict(scenario: QualificationScenario) -> dict[str, Any]:
        return asdict(scenario)



def build_core_modeling_scenarios() -> tuple[QualificationScenario, ...]:
    return (
        QualificationScenario(
            "Q-CUT-001", "part.cut_extrude", "prismatic", "Through pocket", "Verify closed sketch + cut extrusion against an existing solid body.",
            (
                {"tool": "create_sketch", "params": {"plane": "Top Plane"}},
                {"tool": "add_sketch_entity", "params": {"entity_type": "rectangle", "x1": -0.02, "y1": -0.015, "x2": 0.02, "y2": 0.015}},
                {"tool": "extrude_feature", "params": {"depth": 0.01, "feature_type": "boss"}},
                {"tool": "create_sketch", "params": {"on_face": True, "face_x": 0.0, "face_y": 0.005, "face_z": 0.0}},
                {"tool": "add_sketch_entity", "params": {"entity_type": "rectangle", "x1": -0.01, "y1": -0.007, "x2": 0.01, "y2": 0.007}},
                {"tool": "extrude_feature", "params": {"depth": 0.005, "feature_type": "cut"}},
            ),
            ("COMPLETED", "body_count_preserved", "volume_decreases"),
        ),
        QualificationScenario(
            "Q-PAT-001", "create_pattern.linear", "pattern", "Linear feature pattern", "Verify deterministic linear repetition.",
            (
                {"tool": "create_pattern", "params": {"pattern_type": "linear", "direction": "X", "count": 3, "spacing": 0.02}},
            ),
            ("COMPLETED", "feature_count_increases"),
        ),
        QualificationScenario(
            "Q-PAT-002", "create_pattern.circular", "pattern", "Circular feature pattern", "Verify circular repetition around explicit axis.",
            (
                {"tool": "create_pattern", "params": {"pattern_type": "circular", "axis": "Z", "count": 4, "angle": 360.0}},
            ),
            ("COMPLETED", "feature_count_increases"),
        ),
        QualificationScenario(
            "Q-SKETCH-001", "sketch.line", "sketch", "Connected line profile", "Verify multi-segment sketch geometry can be created.",
            (
                {"tool": "create_sketch", "params": {"plane": "Front Plane"}},
                {"tool": "add_sketch_entity", "params": {"entity_type": "line", "x1": -0.03, "y1": 0.0, "x2": 0.03, "y2": 0.0}},
                {"tool": "add_sketch_entity", "params": {"entity_type": "line", "x1": 0.03, "y1": 0.0, "x2": 0.03, "y2": 0.02}},
            ),
            ("COMPLETED", "geometry_present"),
        ),
        QualificationScenario(
            "Q-SKETCH-002", "sketch.arc", "sketch", "Arc profile", "Verify curved sketch entity support.",
            (
                {"tool": "create_sketch", "params": {"plane": "Front Plane"}},
                {"tool": "add_sketch_entity", "params": {"entity_type": "arc", "cx": 0.0, "cy": 0.0, "radius": 0.02}},
            ),
            ("COMPLETED", "geometry_present"),
        ),
        QualificationScenario(
            "Q-SKETCH-003", "add_sketch_constraint.coincident", "constraint", "Coincident constraint", "Verify topological sketch constraint application.",
            (
                {"tool": "add_sketch_constraint", "params": {"constraint_type": "coincident"}},
            ),
            ("COMPLETED", "constraint_applied"),
        ),
        QualificationScenario(
            "Q-REF-001", "add_reference_geometry.axis", "reference", "Reference axis", "Verify explicit reference axis creation.",
            (
                {"tool": "add_reference_geometry", "params": {"geometry_type": "axis"}},
            ),
            ("COMPLETED", "reference_created"),
        ),
        QualificationScenario(
            "Q-REF-002", "add_reference_geometry.plane", "reference", "Reference plane", "Verify explicit reference plane creation.",
            (
                {"tool": "add_reference_geometry", "params": {"geometry_type": "plane"}},
            ),
            ("COMPLETED", "reference_created"),
        ),
        QualificationScenario(
            "Q-EDGE-001", "edge.chamfer", "edge_modifier", "Outer chamfer", "Verify edge selection plus chamfer modification.",
            (
                {"tool": "add_edge_feature", "params": {"feature_type": "chamfer", "radius_or_distance": 0.003, "edge_indices": "[0]"}},
            ),
            ("COMPLETED", "topology_changes"),
        ),
        QualificationScenario(
            "Q-LOFT-001", "part.loft", "advanced_feature", "Two-profile loft", "Verify multiple-profile solid generation.",
            (
                {"tool": "extrude_feature", "params": {"feature_type": "loft"}},
            ),
            ("COMPLETED", "body_geometry_present"),
        ),
        QualificationScenario(
            "Q-SWEEP-001", "part.sweep", "advanced_feature", "Profile sweep", "Verify profile/path based solid generation.",
            (
                {"tool": "extrude_feature", "params": {"feature_type": "sweep"}},
            ),
            ("COMPLETED", "body_geometry_present"),
        ),
    )


__all__ = ["QualificationHarnessV1", "QualificationResult", "QualificationScenario", "build_core_modeling_scenarios"]
