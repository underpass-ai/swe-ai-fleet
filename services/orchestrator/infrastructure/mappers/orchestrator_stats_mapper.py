"""Mapper for OrchestratorStatistics to protobuf."""

from __future__ import annotations

from services.orchestrator.domain.entities import OrchestratorStatistics
from services.orchestrator.infrastructure.dto import orchestrator_dto


class OrchestratorStatsMapper:
    """Mapper for OrchestratorStatistics domain entity to protobuf.
    
    Handles conversion between OrchestratorStatistics domain entity
    and OrchestratorStats protobuf message.
    """
    
    @staticmethod
    def domain_to_proto(
        stats: OrchestratorStatistics,
        active_councils: int
    ) -> orchestrator_dto.OrchestratorStats:
        """Convert domain OrchestratorStatistics to protobuf OrchestratorStats.
        
        Args:
            stats: Domain statistics entity
            active_councils: Number of active councils (from registry)
            
        Returns:
            Protobuf OrchestratorStats message
        """
        stats_dict = stats.to_dict()
        
        return orchestrator_dto.OrchestratorStats(
            total_deliberations=stats_dict["total_deliberations"],
            total_orchestrations=stats_dict["total_orchestrations"],
            avg_deliberation_time_ms=stats_dict["average_duration_ms"],
            active_councils=active_councils,
            role_counts=stats_dict["role_counts"]
        )

