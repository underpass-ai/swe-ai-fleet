"""Architect agent for selecting the best proposals."""

from typing import Any


class ArchitectAgent:
    """Domain agent responsible for selecting the best proposal from candidates.

    This agent encapsulates the business logic for evaluating and selecting
    proposals based on telemetry data and rubrics.
    """

    def select_best(
        self,
        proposals: list[str],
        telemetry: list[dict[str, Any]],
        rubric: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> str:
        """Select the best proposal from the given candidates.

        Args:
            proposals: List of proposal content strings
            telemetry: List of telemetry data for each proposal
            rubric: Optional rubric for evaluation (not currently used)

        Returns:
            The content of the selected proposal
        """
        # Simple deterministic selection by the highest tool score; can be replaced by an LLM call.
        idx = 0
        if telemetry:
            scores = [
                1.0 if (t.get("dryrun", {}).get("ok") and t.get("lint", {}).get("ok")) else 0.0
                for t in telemetry
            ]
            idx = max(range(len(scores)), key=lambda i: scores[i])
        return proposals[idx]
