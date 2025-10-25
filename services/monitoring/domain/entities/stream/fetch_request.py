"""Fetch request configuration for message retrieval."""
from dataclasses import dataclass


@dataclass
class FetchRequest:
    """
    Configuration for fetching messages from a consumer.
    
    Encapsulates the parameters needed for consumer.fetch() operations.
    """
    
    limit: int
    timeout: int
    
    def validate(self) -> None:
        """Validate fetch request parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        if self.limit < 1:
            raise ValueError("limit must be >= 1")
        if self.limit > 10000:
            raise ValueError("limit must be <= 10000")
        if self.timeout < 1:
            raise ValueError("timeout must be >= 1")
        if self.timeout > 300:
            raise ValueError("timeout must be <= 300 seconds")
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation.
        
        Returns:
            Dict with fetch configuration
        """
        return {
            "limit": self.limit,
            "timeout": self.timeout,
        }
    
    @classmethod
    def create(cls, limit: int, timeout: int) -> "FetchRequest":
        """Factory method to create validated FetchRequest.
        
        Args:
            limit: Maximum number of messages to fetch
            timeout: Timeout in seconds
            
        Returns:
            FetchRequest instance
            
        Raises:
            ValueError: If validation fails
        """
        instance = cls(limit=limit, timeout=timeout)
        instance.validate()
        return instance
    
    @classmethod
    def default_monitoring(cls) -> "FetchRequest":
        """Create default fetch request for monitoring.
        
        Returns:
            FetchRequest with 1 message, 5 second timeout
        """
        return cls(limit=1, timeout=5)
