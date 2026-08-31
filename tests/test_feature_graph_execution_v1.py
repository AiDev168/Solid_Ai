from integration.feature_graph_compiler_v1 import compile_feature_graph
from integration.feature_graph_execution_v1 import CompiledPlanExecutor
from integration.feature_graph_v1 import feature_graph_from_dict


def graph():
    return feature_graph_from_dict({
        "schema": "solid-ai.feature-graph.v1",
        "part_id": "p",
        "design_intent": "simple bracket",
        "units": "mm",
        "features": [
            {"feature_id": "profile", "kind": "profile", "depends_on": [], "params": {"width": 10, "height": 20}},
            {"feature_id": "base", "kind": "extrude_boss", "depends_on": ["profile"], "params": {"depth_mm": 5}},
        ],
    })


class Recorder:
    def __init__(self):
        self.operations = []

    def execute(self, operation):
        self.operations.append(operation)
        return {"feature_id": operation.feature_id, "tool": operation.tool}


def test_executor_runs_compiled_operations_in_graph_order():
    recorder = Recorder()
    report = CompiledPlanExecutor(recorder).execute(compile_feature_graph(graph()))
    assert report.ok is True
    assert report.executed_features == ["profile", "base"]
    assert [op.feature_id for op in recorder.operations] == ["profile", "base"]


def test_executor_does_not_own_cad_or_llm_logic():
    recorder = Recorder()
    plan = compile_feature_graph(graph())
    report = CompiledPlanExecutor(recorder).execute(plan)
    assert report.errors == []
