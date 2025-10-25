"""Agent status enumeration."""

from enum import Enum


class AgentStatus(Enum):
    """Enumeration of valid agent statuses.
    
    This enumeration centralizes all valid agent statuses in the system,
    ensuring consistency across all entities and preventing magic strings.
    """
    
    READY = "ready"
    IDLE = "idle"
    BUSY = "busy"
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
            raise ValueError(f"Invalid agent status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}")
    
    @classmethod
    def is_ready_status(cls, status: str) -> bool:
        """Check if status represents ready state.
        
        Args:
            status: Status to check
            
        Returns:
            True if status is ready, False otherwise
        """
        return status == cls.READY.value
    
    @classmethod
    def is_busy_status(cls, status: str) -> bool:
        """Check if status represents busy state.
        
        Args:
            status: Status to check
            
        Returns:
            True if status is busy, False otherwise
        """
        return status == cls.BUSY.value
    
    @classmethod
    def is_offline_status(cls, status: str) -> bool:
        """Check if status represents offline state.
        
        Args:
            status: Status to check
            
        Returns:
            True if status is offline, False otherwise
        """
        return status == cls.OFFLINE.value
    
    @classmethod
    def is_idle_status(cls, status: str) -> bool:
        """Check if status represents idle state.
        
        Args:
            status: Status to check
            
        Returns:
            True if status is idle, False otherwise
        """
        return status == cls.IDLE.value
    
    @classmethod
    def is_error_status(cls, status: str) -> bool:
        """Check if status represents error state.
        
        Args:
            status: Status to check
            
        Returns:
            True if status is error, False otherwise
        """
        return status == cls.ERROR.value
