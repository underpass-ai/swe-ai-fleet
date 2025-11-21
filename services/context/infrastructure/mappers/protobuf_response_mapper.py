"""Mapper from protobuf responses to DTOs.

Infrastructure layer mapper for converting gRPC protobuf responses
to DTOs for NATS messaging.

Following Hexagonal Architecture:
- Infrastructure concern: serialization/deserialization
- Separates internal format (protobuf) from external format (DTO)
- No domain logic, pure data transformation
"""

from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
    RehydrationStatsDTO,
)
from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)
from services.context.gen import context_pb2


class ProtobufResponseMapper:
    """Mapper that converts protobuf responses to DTOs.

    Responsibility:
    - Protobuf response → DTO
    - Handle all field mappings and type conversions
    - Extract nested structures

    This is infrastructure-level serialization logic.
    Should NOT be in handlers or servicers.
    """

    @staticmethod
    def to_update_context_response_dto(
        response: context_pb2.UpdateContextResponse,
        story_id: str,
    ) -> UpdateContextResponseDTO:
        """Convert UpdateContextResponse to DTO.

        Args:
            response: Protobuf UpdateContextResponse
            story_id: Story ID from original request

        Returns:
            UpdateContextResponseDTO
        """
        return UpdateContextResponseDTO(
            story_id=story_id,
            status="success",
            version=response.version,
            hash=response.hash,
            warnings=list(response.warnings),
        )

    @staticmethod
    def to_rehydrate_session_response_dto(
        response: context_pb2.RehydrateSessionResponse,
    ) -> RehydrateSessionResponseDTO:
        """Convert RehydrateSessionResponse to DTO.

        Args:
            response: Protobuf RehydrateSessionResponse

        Returns:
            RehydrateSessionResponseDTO
        """
        stats_dto = RehydrationStatsDTO(
            decisions=response.stats.decisions,
            decision_edges=response.stats.decision_edges,
            impacts=response.stats.impacts,
            events=response.stats.events,
            roles=list(response.stats.roles),
        )

        return RehydrateSessionResponseDTO(
            case_id=response.case_id,
            status="success",
            generated_at_ms=response.generated_at_ms,
            packs_count=len(response.packs),
            stats=stats_dto,
        )

