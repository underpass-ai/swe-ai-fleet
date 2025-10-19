"""Mapper for deliberation status strings to protobuf enums."""

from __future__ import annotations

from services.orchestrator.infrastructure.dto import orchestrator_dto


class DeliberationStatusMapper:
    """Mapper for converting deliberation status between domain and protobuf.
    
    Encapsulates the mapping logic between string status values (domain)
    and protobuf enum values (infrastructure).
    """
    
    # Status mapping: domain string → proto enum
    _STATUS_MAP = {
        "DELIBERATION_STATUS_PENDING": orchestrator_dto.DELIBERATION_STATUS_PENDING,
        "DELIBERATION_STATUS_IN_PROGRESS": orchestrator_dto.DELIBERATION_STATUS_IN_PROGRESS,
        "DELIBERATION_STATUS_COMPLETED": orchestrator_dto.DELIBERATION_STATUS_COMPLETED,
        "DELIBERATION_STATUS_FAILED": orchestrator_dto.DELIBERATION_STATUS_FAILED,
        "DELIBERATION_STATUS_TIMEOUT": orchestrator_dto.DELIBERATION_STATUS_TIMEOUT,
        "DELIBERATION_STATUS_UNKNOWN": orchestrator_dto.DELIBERATION_STATUS_UNKNOWN,
    }
    
    @staticmethod
    def string_to_proto_enum(status: str) -> int:
        """Convert domain status string to protobuf enum.
        
        Args:
            status: Status string from domain
            
        Returns:
            Protobuf status enum value
        """
        return DeliberationStatusMapper._STATUS_MAP.get(
            status,
            orchestrator_dto.DELIBERATION_STATUS_UNKNOWN
        )
    
    @staticmethod
    def proto_enum_to_string(proto_status: int) -> str:
        """Convert protobuf enum to domain status string.
        
        Args:
            proto_status: Protobuf status enum value
            
        Returns:
            Domain status string
        """
        # Reverse lookup
        for status_str, proto_val in DeliberationStatusMapper._STATUS_MAP.items():
            if proto_val == proto_status:
                return status_str
        
        return "DELIBERATION_STATUS_UNKNOWN"

