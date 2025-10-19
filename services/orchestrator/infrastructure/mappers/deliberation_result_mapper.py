"""Mapper for DeliberationResultVO."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.value_objects import DeliberationResultVO

from .check_suite_mapper import CheckSuiteMapper
from .proposal_mapper import ProposalMapper


class DeliberationResultMapper:
    """Maps DeliberationResultVO to/from Protobuf DTOs.
    
    Note: Uses CheckSuite entity internally for check results.
    """
    
    @staticmethod
    def to_proto(vo: DeliberationResultVO, orchestrator_pb2: Any) -> Any:
        """Convert DeliberationResultVO to protobuf DeliberationResult.
        
        Args:
            vo: DeliberationResultVO domain value object
            orchestrator_pb2: Protobuf module
            
        Returns:
            orchestrator_pb2.DeliberationResult instance
        """
        return orchestrator_pb2.DeliberationResult(
            proposal=ProposalMapper.to_proto(vo.proposal, orchestrator_pb2),
            checks=CheckSuiteMapper.to_proto(vo.checks, orchestrator_pb2),
            score=vo.score,
            rank=vo.rank,
        )
    
    @staticmethod
    def from_proto(proto: Any) -> DeliberationResultVO:
        """Convert protobuf DeliberationResult to DeliberationResultVO.
        
        Args:
            proto: orchestrator_pb2.DeliberationResult instance
            
        Returns:
            DeliberationResultVO domain value object
        """
        return DeliberationResultVO(
            proposal=ProposalMapper.from_proto(proto.proposal),
            checks=CheckSuiteMapper.from_proto(proto.checks),
            score=proto.score,
            rank=proto.rank,
        )

