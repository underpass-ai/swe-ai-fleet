"""Mapper for OrchestrateResponse."""

from __future__ import annotations

import time
from typing import Any

from services.orchestrator.domain.value_objects import (
    DeliberationResultVO,
    ProposalVO,
)

from .deliberation_result_mapper import DeliberationResultMapper
from .metadata_mapper import MetadataMapper


class OrchestrateResponseMapper:
    """Maps orchestration results to OrchestrateResponse protobuf."""
    
    @staticmethod
    def domain_to_proto(
        result: dict[str, Any],
        task_id: str,
        duration_ms: int,
        execution_id: str,
        orchestrator_pb2: Any,
        domain_checks_converter: Any,
    ) -> Any:
        """Convert domain orchestration result to protobuf OrchestrateResponse.
        
        Args:
            result: Dict with 'winner' and 'candidates' keys
            task_id: Task identifier
            duration_ms: Duration of orchestration in milliseconds
            execution_id: Unique execution identifier
            orchestrator_pb2: Protobuf module
            domain_checks_converter: Function to convert domain checks to CheckSuiteVO
            
        Returns:
            orchestrator_pb2.OrchestrateResponse instance
        """
        winner = result.get("winner")
        candidates = result.get("candidates", [])
        
        # Convert winner to VO and proto
        winner_proposal_vo = ProposalVO(
            author_id=winner.proposal.author.agent_id,
            author_role=winner.proposal.author.role,
            content=winner.proposal.content,
            created_at_ms=int(time.time() * 1000)
        )
        winner_checks_vo = domain_checks_converter(winner.checks)
        winner_vo = DeliberationResultVO(
            proposal=winner_proposal_vo,
            checks=winner_checks_vo,
            score=winner.score,
            rank=1
        )
        proto_winner = DeliberationResultMapper.to_proto(winner_vo, orchestrator_pb2)
        
        # Convert candidates to proto
        proto_candidates = []
        for idx, c in enumerate(candidates):
            candidate_proposal_vo = ProposalVO(
                author_id=c["proposal"]["author"].agent_id,
                author_role=c["proposal"]["author"].role,
                content=c["proposal"]["content"],
                created_at_ms=int(time.time() * 1000)
            )
            candidate_checks_vo = domain_checks_converter(c["checks"])
            candidate_vo = DeliberationResultVO(
                proposal=candidate_proposal_vo,
                checks=candidate_checks_vo,
                score=c["score"],
                rank=idx + 2
            )
            proto_candidates.append(
                DeliberationResultMapper.to_proto(candidate_vo, orchestrator_pb2)
            )
        
        # Create metadata VO and convert to proto
        metadata_vo = MetadataMapper.create(version="0.1.0", execution_id=execution_id)
        metadata_proto = MetadataMapper.to_proto(metadata_vo, orchestrator_pb2)
        
        return orchestrator_pb2.OrchestrateResponse(
            winner=proto_winner,
            candidates=proto_candidates,
            execution_id=execution_id,
            duration_ms=duration_ms,
            metadata=metadata_proto
        )

