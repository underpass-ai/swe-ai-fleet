"""Council status enumeration."""

from enum import Enum


class CouncilStatus(Enum):
    """Enumeration of valid council statuses.
    
    This enumeration centralizes all valid council statuses in the system,
    ensuring consistency across all entities and preventing magic strings.
    """
    
    ACTIVE = "active"
    IDLE = "idle"
    INACTIVE = "inactive"
    ERROR = "error"
    OFFLINE = "offline"
    
    @classmethod
    def validate_status(cls, status: str) -> None:
        """Validate a status string and raise exception if invalid.
        
        Args:
            status: Status string to validate.
            
        Raises:
            ValueError: If status is not valid.
        """
        valid_statuses = {status.value for status in cls}
        if status not in valid_statuses:
            raise ValueError(f"Invalid council status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}")
