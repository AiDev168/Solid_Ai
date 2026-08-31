import pytest

from integration.llm_fidelity_gate_v1 import (
    LLMSemanticFidelityError,
    assert_explicit_constraints_preserved,
    assert_no_implicit_m8_drill_conversion,
)


def test_explicit_dimension_is_preserved():
    requirements = {"explicit_constraints": [{"id": "c1", "target": "thickness", "value": 10, "unit": "mm"}]}
    graph = {"features": [{"feature_id": "base", "params": {"thickness": 10, "requirement_refs": ["c1"]}}]}
    assert_explicit_constraints_preserved(graph, requirements)


def test_missing_constraint_is_rejected():
    requirements = {"explicit_constraints": [{"id": "c1", "target": "thickness", "value": 10, "unit": "mm"}]}
    graph = {"features": [{"feature_id": "base", "params": {"depth_mm": 10}}]}
    with pytest.raises(LLMSemanticFidelityError):
        assert_explicit_constraints_preserved(graph, requirements)


def test_m8_must_not_become_8_5_mm():
    requirements = {"explicit_constraints": [{"id": "hole_size", "target": "bolt_hole_size", "value": "M8", "unit": "nominal"}]}
    graph = {"features": [{"feature_id": "holes", "params": {"diameter_mm": 8.5}}]}
    with pytest.raises(LLMSemanticFidelityError):
        assert_no_implicit_m8_drill_conversion(graph, requirements)


def test_m8_semantic_reference_is_allowed():
    requirements = {"explicit_constraints": [{"id": "hole_size", "target": "bolt_hole_size", "value": "M8", "unit": "nominal"}]}
    graph = {"features": [{"feature_id": "holes", "params": {"fastener": "M8", "requirement_refs": ["hole_size"]}}]}
    assert_explicit_constraints_preserved(graph, requirements)
    assert_no_implicit_m8_drill_conversion(graph, requirements)
