"""TopologyState value object."""

from __future__ import annotations

from dataclasses import dataclass

from .execution_step import ExecutionStep
from .topology_node import TopologyNode


@dataclass(frozen=True)
class TopologyState:
    """Immutable snapshot of nodes for topological sorting."""

    nodes: tuple[TopologyNode, ...]

    def next_step(self, current_order: int) -> tuple[ExecutionStep, "TopologyState"]:
        """Produce next execution step and the updated state."""
        ready_nodes = tuple(node for node in self.nodes if node.is_ready())
        if not ready_nodes:
            raise ValueError("Internal error: topological sort failed")

        # Pick first ready node (deterministic order by task id)
        selected_node = sorted(ready_nodes, key=lambda n: n.task.task_id.value)[0]
        step = ExecutionStep(order=current_order, task=selected_node.task)

        updated_nodes: list[TopologyNode] = []
        for node in self.nodes:
            if node.task.task_id == selected_node.task.task_id:
                continue
            updated_nodes.append(
                node.remove_dependency(selected_node.task.task_id.value)
            )

        return step, TopologyState(tuple(updated_nodes))

    def is_empty(self) -> bool:
        return not self.nodes

