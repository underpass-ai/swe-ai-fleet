"""AuthorizationResult Value Object - Result of authorization check."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationResult:
    """Result of an authorization check.
    
    Encapsulates whether access was granted and, if denied, why.
    
    This is a Value Object that represents the outcome of an authorization decision.
    Immutable by design (frozen=True).
    """
    
    is_authorized: bool
    denial_reason: str | None = None
    
    def __post_init__(self) -> None:
        """Validate authorization result.
        
        Raises:
            ValueError: If validation fails
        """
        # If denied, reason must be provided
        if not self.is_authorized and not self.denial_reason:
            raise ValueError(
                "denial_reason is required when is_authorized=False. "
                "Every denial must have an explicit reason for audit trails."
            )
        
        # If authorized, reason should be None
        if self.is_authorized and self.denial_reason:
            raise ValueError(
                "denial_reason must be None when is_authorized=True. "
                "Authorized access should not have a denial reason."
            )
    
    def was_granted(self) -> bool:
        """Check if authorization was granted.
        
        Returns:
            True if access was authorized
        """
        return self.is_authorized
    
    def was_denied(self) -> bool:
        """Check if authorization was denied.
        
        Returns:
            True if access was denied
        """
        return not self.is_authorized
    
    def get_denial_reason(self) -> str:
        """Get denial reason (fails if authorized).
        
        Returns:
            Denial reason string
            
        Raises:
            ValueError: If called on authorized result
        """
        if self.is_authorized:
            raise ValueError("Cannot get denial_reason when authorization was granted")
        
        return self.denial_reason or "Unknown reason"  # Should never be None due to validation
    
    @staticmethod
    def granted() -> "AuthorizationResult":
        """Create authorized result.
        
        Returns:
            AuthorizationResult with is_authorized=True
        """
        return AuthorizationResult(is_authorized=True, denial_reason=None)
    
    @staticmethod
    def denied(reason: str) -> "AuthorizationResult":
        """Create denied result with reason.
        
        Args:
            reason: Why access was denied (required)
            
        Returns:
            AuthorizationResult with is_authorized=False
            
        Raises:
            ValueError: If reason is empty
        """
        if not reason or not reason.strip():
            raise ValueError("Denial reason cannot be empty")
        
        return AuthorizationResult(is_authorized=False, denial_reason=reason)

