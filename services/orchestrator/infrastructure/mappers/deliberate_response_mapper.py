"""Mapper for DeliberateResponse."""

from __future__ import annotations

import time
from typing import Any

from services.orchestrator.domain.value_objects import (
    DeliberationResultVO,
    ProposalVO,
)

from .deliberation_result_mapper import DeliberationResultMapper
from .metadata_mapper import MetadataMapper


class DeliberateResponseMapper:
    """Maps deliberation results to DeliberateResponse protobuf."""
    
    @staticmethod
    def domain_to_proto(
        results: list[Any],
        duration_ms: int,
        execution_id: str,
        orchestrator_pb2: Any,
        domain_checks_converter: Any,
        task_id: str | None = None,  # REQUIRED for backlog review ceremonies
    ) -> Any:
        """Convert domain deliberation results to protobuf DeliberateResponse.
        
        Args:
            results: List of domain DeliberationResult objects
            duration_ms: Duration of deliberation in milliseconds
            execution_id: Unique execution identifier
            orchestrator_pb2: Protobuf module
            domain_checks_converter: Function to convert domain checks to CheckSuiteVO
            task_id: Original task_id from request (REQUIRED for backlog review ceremonies)
            
        Returns:
            orchestrator_pb2.DeliberateResponse instance
        """
        proto_results = []
        
        for rank, result in enumerate(results, 1):
            # Convert domain result to VO
            proposal_vo = ProposalVO(
                author_id=result.proposal.author.agent_id,
                author_role=result.proposal.author.role,
                content=result.proposal.content,
                created_at_ms=int(time.time() * 1000)
            )
            
            checks_vo = domain_checks_converter(result.checks)
            
            result_vo = DeliberationResultVO(
                proposal=proposal_vo,
                checks=checks_vo,
                score=result.score,
                rank=rank
            )
            
            # Use mapper to convert VO to proto
            proto_result = DeliberationResultMapper.to_proto(result_vo, orchestrator_pb2)
            proto_results.append(proto_result)
        
        winner_id = proto_results[0].proposal.author_id if proto_results else ""
        
        # Create metadata VO and convert to proto
        metadata_vo = MetadataMapper.create(version="0.1.0", execution_id=execution_id)
        metadata_proto = MetadataMapper.to_proto(metadata_vo, orchestrator_pb2)
        
        import logging
        logger = logging.getLogger(__name__)
        final_task_id = task_id or ""
        logger.info(
            f"🔍 [TASK_ID_TRACE] DeliberateResponseMapper.domain_to_proto: "
            f"ASSIGNING task_id='{final_task_id}' to DeliberateResponse "
            f"(input task_id='{task_id}')"
        )
        return orchestrator_pb2.DeliberateResponse(
            task_id=final_task_id,  # REQUIRED for backlog review ceremonies
            results=proto_results,
            winner_id=winner_id,
            duration_ms=duration_ms,
            metadata=metadata_proto
        )

