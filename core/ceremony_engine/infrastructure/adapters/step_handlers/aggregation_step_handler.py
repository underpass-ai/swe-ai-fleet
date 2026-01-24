"""AggregationStepHandler: Aggregates results/decisions.

Following Hexagonal Architecture:
- This is an infrastructure adapter
- Executes aggregation steps
- Returns domain value objects (StepResult)
"""

from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.infrastructure.adapters.step_handlers.base_step_handler import (
    BaseStepHandler,
)


class AggregationStepHandler(BaseStepHandler):
    """Handler for aggregation_step steps.

    Aggregates results from multiple steps or sources.

    Config requirements:
    - sources: List of source step IDs or artifact IDs
    - aggregation_type: Type of aggregation (sum, average, merge, etc.)

    Following Hexagonal Architecture:
    - This is infrastructure (adapter)
    - Aggregates data from context inputs
    """

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute aggregation step.

        Args:
            step: Step to execute
            context: Execution context (step outputs, etc.)

        Returns:
            StepResult with aggregated output

        Raises:
            ValueError: If config is invalid
        """
        # Validate config
        self._validate_config(step, required_keys=["sources", "aggregation_type"])

        # Extract config
        sources = step.config["sources"]
        aggregation_type = step.config["aggregation_type"]
        if not isinstance(sources, list) or not sources:
            raise ValueError("aggregation_step sources must be a non-empty list")

        step_outputs = context.get_mapping(ContextKey.STEP_OUTPUTS) or {}
        inputs = context.get_mapping(ContextKey.INPUTS) or {}
        values = []
        for source in sources:
            if not isinstance(source, str) or not source.strip():
                raise ValueError("aggregation_step sources must be non-empty strings")
            if source in step_outputs:
                values.append(step_outputs[source])
                continue
            if source in inputs:
                values.append(inputs[source])
                continue
            raise ValueError(
                f"aggregation_step source '{source}' not found in inputs or step outputs"
            )

        aggregated_result = self._aggregate(values, aggregation_type)

        output = {
            "sources": sources,
            "aggregation_type": aggregation_type,
            "aggregated_result": aggregated_result,
        }

        return self._create_success_result(output)

    @staticmethod
    def _aggregate(values: list[object], aggregation_type: str) -> object:
        """Aggregate values based on aggregation_type."""
        if aggregation_type == "merge":
            if len(values) == 1:
                return values[0]
            if not all(isinstance(value, dict) for value in values):
                raise ValueError("merge aggregation requires all sources to be dicts")
            merged: dict[str, object] = {}
            for value in values:
                merged.update(value)  # later sources override earlier keys
            return merged
        if aggregation_type == "list":
            return list(values)
        if aggregation_type == "concat":
            if not all(isinstance(value, str) for value in values):
                raise ValueError("concat aggregation requires all sources to be strings")
            return "".join(values)
        raise ValueError(f"Unsupported aggregation_type: {aggregation_type}")
