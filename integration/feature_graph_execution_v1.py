from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .feature_graph_compiler_v1 import CompiledPlan, Operation


class FeatureExecutionError(RuntimeError):
    """Raised when a compiled operation cannot be executed."""


class OperationExecutor(Protocol):
    def execute(self, operation: Operation) -> Any:
        ...


@dataclass
class ExecutionReport:
    ok: bool = False
    executed_features: list[str] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CompiledPlanExecutor:
    """Execute an already compiled plan through an injected runtime boundary.

    This class deliberately knows nothing about SolidWorks, selectors, geometry
    recovery, or LLMs. Those concerns stay behind OperationExecutor.
    """

    def __init__(self, executor: OperationExecutor):
        self.executor = executor

    def execute(self, plan: CompiledPlan) -> ExecutionReport:
        report = ExecutionReport()
        try:
            for feature in plan.features:
                for operation in feature.operations:
                    result = self.executor.execute(operation)
                    report.results.append(result)
                report.executed_features.append(feature.feature_id)
            report.ok = True
        except Exception as exc:
            report.errors.append(str(exc))
        return report


__all__ = ["CompiledPlanExecutor", "ExecutionReport", "FeatureExecutionError", "OperationExecutor"]
