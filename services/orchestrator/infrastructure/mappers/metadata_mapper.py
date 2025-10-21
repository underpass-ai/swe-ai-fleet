"""Mapper for OrchestratorMetadataVO."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from services.orchestrator.domain.value_objects import OrchestratorMetadataVO


class MetadataMapper:
    """Maps OrchestratorMetadataVO to/from Protobuf DTOs."""
    
    @staticmethod
    def to_proto(vo: OrchestratorMetadataVO, orchestrator_pb2: Any) -> Any:
        """Convert OrchestratorMetadataVO to protobuf OrchestratorMetadata.
        
        Args:
            vo: OrchestratorMetadataVO domain value object
            orchestrator_pb2: Protobuf module
            
        Returns:
            orchestrator_pb2.OrchestratorMetadata instance
        """
        return orchestrator_pb2.OrchestratorMetadata(
            orchestrator_version=vo.orchestrator_version,
            timestamp_ms=vo.timestamp_ms,
            execution_id=vo.execution_id,
        )
    
    @staticmethod
    def from_proto(proto: Any) -> OrchestratorMetadataVO:
        """Convert protobuf OrchestratorMetadata to OrchestratorMetadataVO.
        
        Args:
            proto: orchestrator_pb2.OrchestratorMetadata instance
            
        Returns:
            OrchestratorMetadataVO domain value object
        """
        return OrchestratorMetadataVO(
            orchestrator_version=proto.orchestrator_version,
            timestamp_ms=proto.timestamp_ms,
            execution_id=proto.execution_id,
        )
    
    @staticmethod
    def create(
        version: str = "0.1.0",
        execution_id: str | None = None,
    ) -> OrchestratorMetadataVO:
        """Create metadata VO with current timestamp.
        
        Args:
            version: Orchestrator version
            execution_id: Execution ID (generated if not provided)
            
        Returns:
            OrchestratorMetadataVO instance
        """
        if execution_id is None:
            # Generate execution ID from timestamp + random component
            timestamp = str(time.time())
            execution_id = hashlib.sha256(timestamp.encode()).hexdigest()[:16]
        
        return OrchestratorMetadataVO(
            orchestrator_version=version,
            timestamp_ms=int(time.time() * 1000),
            execution_id=execution_id,
        )

