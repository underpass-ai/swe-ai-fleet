"""Unit tests for AuthorizationResult Value Object."""

import pytest

from core.context.domain.value_objects.authorization_result import AuthorizationResult


class TestAuthorizationResult:
    """Test suite for AuthorizationResult VO."""
    
    def test_granted_factory_creates_authorized_result(self) -> None:
        """Test that granted() creates authorized result with no denial reason."""
        result = AuthorizationResult.granted()
        
        assert result.is_authorized is True
        assert result.denial_reason is None
        assert result.was_granted() is True
        assert result.was_denied() is False
    
    def test_denied_factory_creates_denied_result_with_reason(self) -> None:
        """Test that denied() creates denied result with reason."""
        reason = "User not assigned to story"
        result = AuthorizationResult.denied(reason)
        
        assert result.is_authorized is False
        assert result.denial_reason == reason
        assert result.was_denied() is True
        assert result.was_granted() is False
    
    def test_denied_factory_fails_fast_on_empty_reason(self) -> None:
        """Test that denied() raises ValueError if reason is empty."""
        with pytest.raises(ValueError, match="Denial reason cannot be empty"):
            AuthorizationResult.denied("")
        
        with pytest.raises(ValueError, match="Denial reason cannot be empty"):
            AuthorizationResult.denied("   ")  # Only whitespace
    
    def test_get_denial_reason_returns_reason_when_denied(self) -> None:
        """Test that get_denial_reason() returns reason for denied result."""
        reason = "Access forbidden"
        result = AuthorizationResult.denied(reason)
        
        assert result.get_denial_reason() == reason
    
    def test_get_denial_reason_fails_fast_when_granted(self) -> None:
        """Test that get_denial_reason() raises ValueError when authorized."""
        result = AuthorizationResult.granted()
        
        with pytest.raises(ValueError, match="Cannot get denial_reason when authorization was granted"):
            result.get_denial_reason()
    
    def test_direct_construction_with_denied_requires_reason(self) -> None:
        """Test that constructing denied result without reason fails fast."""
        with pytest.raises(ValueError, match="denial_reason is required when is_authorized=False"):
            AuthorizationResult(is_authorized=False, denial_reason=None)
    
    def test_direct_construction_with_granted_forbids_reason(self) -> None:
        """Test that constructing granted result with reason fails fast."""
        with pytest.raises(ValueError, match="denial_reason must be None when is_authorized=True"):
            AuthorizationResult(is_authorized=True, denial_reason="some reason")
    
    def test_authorization_result_is_immutable(self) -> None:
        """Test that AuthorizationResult is frozen (immutable)."""
        result = AuthorizationResult.granted()
        
        with pytest.raises(AttributeError):
            result.is_authorized = False  # type: ignore
        
        with pytest.raises(AttributeError):
            result.denial_reason = "try to change"  # type: ignore

