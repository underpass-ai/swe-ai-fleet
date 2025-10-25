"""Stream name value object."""
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamName:
    """
    Value object representing a NATS stream name.
    
    Immutable and validated at creation.
    """
    
    name: str
    
    def __post_init__(self):
        """Validate stream name on creation."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Stream name cannot be empty")
        if len(self.name) > 255:
            raise ValueError("Stream name cannot exceed 255 characters")
        if not self.name.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Stream name can only contain alphanumeric characters, hyphens, and underscores")
    
    def __str__(self) -> str:
        """Return the stream name as string."""
        return self.name
    
    def equals(self, other: "StreamName") -> bool:
        """Check if stream names are equal.
        
        Args:
            other: Another StreamName to compare
            
        Returns:
            True if names are equal
        """
        if not isinstance(other, StreamName):
            return False
        return self.name == other.name
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation.
        
        Returns:
            Dict with stream name
        """
        return {"name": self.name}
    
    @classmethod
    def create(cls, name: str) -> "StreamName":
        """Factory method to create validated StreamName.
        
        Args:
            name: Stream name
            
        Returns:
            StreamName instance
            
        Raises:
            ValueError: If validation fails
        """
        return cls(name=name)
