"""Mapper for ProposalVO."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.value_objects import ProposalVO


class ProposalMapper:
    """Maps ProposalVO to/from Protobuf DTOs."""
    
    @staticmethod
    def to_proto(vo: ProposalVO, orchestrator_pb2: Any) -> Any:
        """Convert ProposalVO to protobuf Proposal.
        
        Args:
            vo: ProposalVO domain value object
            orchestrator_pb2: Protobuf module (injected to avoid import coupling)
            
        Returns:
            orchestrator_pb2.Proposal instance
        """
        return orchestrator_pb2.Proposal(
            author_id=vo.author_id,
            author_role=vo.author_role,
            content=vo.content,
            created_at_ms=vo.created_at_ms,
        )
    
    @staticmethod
    def from_proto(proto: Any) -> ProposalVO:
        """Convert protobuf Proposal to ProposalVO.
        
        Args:
            proto: orchestrator_pb2.Proposal instance
            
        Returns:
            ProposalVO domain value object
        """
        return ProposalVO(
            author_id=proto.author_id,
            author_role=proto.author_role,
            content=proto.content,
            created_at_ms=proto.created_at_ms,
        )

