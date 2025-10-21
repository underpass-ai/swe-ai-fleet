"""Mapper for DeliberationResultData to protobuf."""

from __future__ import annotations

from services.orchestrator.domain.entities.deliberation_result_data import (
    DeliberationResultData,
)
from services.orchestrator.infrastructure.dto import orchestrator_dto
from services.orchestrator.infrastructure.mappers.deliberation_status_mapper import (
    DeliberationStatusMapper,
)


class DeliberationResultDataMapper:
    """Mapper for DeliberationResultData to/from protobuf.
    
    Handles conversion between DeliberationResultData domain entity
    and GetDeliberationResultResponse protobuf message.
    """
    
    @staticmethod
    def domain_to_proto(
        result_data: DeliberationResultData
    ) -> orchestrator_dto.GetDeliberationResultResponse:
        """Convert domain DeliberationResultData to protobuf response.
        
        Args:
            result_data: Domain deliberation result data
            
        Returns:
            Protobuf GetDeliberationResultResponse message
        """
        # Map status to proto enum
        status = DeliberationStatusMapper.string_to_proto_enum(result_data.status)
        
        # Build response
        response = orchestrator_dto.GetDeliberationResultResponse(
            task_id=result_data.task_id,
            status=status,
            duration_ms=result_data.duration_ms,
            error_message=result_data.error_message,
        )
        
        # Add results if completed
        if result_data.is_completed:
            for agent_result in result_data.results:
                delib_result = orchestrator_dto.DeliberationResult(
                    proposal=orchestrator_dto.Proposal(
                        author_id=agent_result.proposal.author_id,
                        author_role=agent_result.proposal.author_role,
                        content=agent_result.proposal.content,
                    ),
                    score=1.0,  # Default score (can be enhanced later)
                )
                response.results.append(delib_result)
            
            # Set winner (first result)
            if result_data.winner_agent_id:
                response.winner_id = result_data.winner_agent_id
        
        # Add metadata
        response.metadata.CopyFrom(orchestrator_dto.OrchestratorMetadata(
            execution_id=result_data.task_id,
            total_agents=result_data.total_agents,
            successful_agents=result_data.received_count,
            failed_agents=result_data.failed_count,
        ))
        
        return response

