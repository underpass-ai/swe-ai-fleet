"""Adapter for council query operations."""

from __future__ import annotations

import logging

from services.orchestrator.domain.entities import CouncilRegistry
from services.orchestrator.domain.ports.council_query_port import (
    AgentInfo,
    CouncilInfo,
    CouncilQueryPort,
)

logger = logging.getLogger(__name__)


class CouncilQueryAdapter(CouncilQueryPort):
    """Adapter implementing council query operations.

    This adapter extracts information from councils and agents,
    providing structured data for queries.

    Attributes:
        _default_model: Default model to use when agent model cannot be determined
    """

    def __init__(self, default_model: str):
        """Initialize the adapter.

        Args:
            default_model: Default model name to use for agents without explicit model
        """
        self._default_model = default_model

    def has_council(self, role: str, council_registry: CouncilRegistry) -> bool:
        """Check if a council exists for the given role.

        Args:
            role: Role to check for
            council_registry: Registry to query

        Returns:
            True if council exists, False otherwise
        """
        try:
            return council_registry.has_council(role)
        except Exception:
            return False

    def list_councils(
        self,
        council_registry: CouncilRegistry,
        include_agents: bool = False
    ) -> list[CouncilInfo]:
        """List all active councils.

        Implements CouncilQueryPort.list_councils by extracting
        information from the council registry.

        Raises:
            RuntimeError: If include_agents is False (agents must be included)
        """
        # Fail-fast: Agents must be included for meaningful council information
        if not include_agents:
            raise RuntimeError(
                "include_agents must be True. "
                "Listing councils without agent information is not supported."
            )

        councils = []

        # Tell registry to provide councils with agents (Tell, Don't Ask)
        for role, _council, agents in council_registry.get_councils_with_agents():
            council_info = self._build_council_info(
                role=role,
                agents=agents,
                include_agents=include_agents
            )
            councils.append(council_info)

        return councils

    def get_council_info(
        self,
        council_registry: CouncilRegistry,
        role: str,
        include_agents: bool = False
    ) -> CouncilInfo:
        """Get information about a specific council.

        Raises:
            RuntimeError: If include_agents is False (agents must be included)
            ValueError: If council not found
        """
        # Fail-fast: Agents must be included
        if not include_agents:
            raise RuntimeError(
                "include_agents must be True. "
                "Getting council info without agent information is not supported."
            )

        if not council_registry.has_council(role):
            raise ValueError(f"Council for role {role} not found")

        agents = council_registry.get_agents(role)
        return self._build_council_info(
            role=role,
            agents=agents,
            include_agents=include_agents
        )

    def _build_council_info(
        self,
        role: str,
        agents: list,
        include_agents: bool
    ) -> CouncilInfo:
        """Build CouncilInfo from role and agents.

        Raises:
            RuntimeError: If council has no agents or agent model cannot be determined
        """
        num_agents = len(agents)

        # Fail-fast: Council must have at least one agent
        if num_agents == 0:
            raise RuntimeError(
                f"Council {role} has no agents. "
                f"Cannot build council info for an empty council."
            )

        # Get model from first agent (all agents in council use same model)
        # Fail-fast if model cannot be determined
        model = None
        if hasattr(agents[0], 'model'):
            model = agents[0].model
        elif hasattr(agents[0], 'vllm_url'):
            # For VLLM agents, use the injected default model
            model = self._default_model

        if not model or model == "unknown":
            raise RuntimeError(
                f"Cannot determine model for council {role}. "
                f"Agents must have 'model' attribute or default_model must be provided."
            )

        # Create AgentInfo for each agent if requested
        agent_infos = []
        if include_agents:
            for agent in agents:
                agent_info = AgentInfo(
                    agent_id=agent.agent_id,
                    role=role,
                    status="ready",  # FUTURE: Implement agent health checks and status tracking
                )
                agent_infos.append(agent_info)

        council_info = CouncilInfo(
            council_id=f"council-{role.lower()}",
            role=role,
            num_agents=num_agents,
            status="active" if num_agents > 0 else "idle",
            model=model
        )

        # Attach agent_infos as attribute for use case layer
        if include_agents:
            council_info.agent_infos = agent_infos

        return council_info

