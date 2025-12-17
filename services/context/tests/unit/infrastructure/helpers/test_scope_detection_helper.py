"""Unit tests for ScopeDetectionHelper."""

from unittest.mock import Mock, patch

import pytest
from services.context.infrastructure.helpers.scope_detection_helper import (
    ScopeDetectionHelper,
)


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_delegates_to_domain_service(mock_detect_scopes) -> None:
    """Test that detect_scopes delegates to domain service."""
    # Arrange
    prompt_blocks = Mock()
    expected_scopes = ["scope1", "scope2", "scope3"]
    mock_detect_scopes.return_value = expected_scopes

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    mock_detect_scopes.assert_called_once_with(prompt_blocks)
    assert result == expected_scopes


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_with_empty_result(mock_detect_scopes) -> None:
    """Test detect_scopes when domain service returns empty list."""
    # Arrange
    prompt_blocks = Mock()
    mock_detect_scopes.return_value = []

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    mock_detect_scopes.assert_called_once_with(prompt_blocks)
    assert result == []


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_with_single_scope(mock_detect_scopes) -> None:
    """Test detect_scopes with single scope."""
    # Arrange
    prompt_blocks = Mock()
    expected_scopes = ["admin"]
    mock_detect_scopes.return_value = expected_scopes

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    assert result == expected_scopes


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_passes_through_exceptions(mock_detect_scopes) -> None:
    """Test that detect_scopes passes through exceptions from domain service."""
    # Arrange
    prompt_blocks = Mock()
    mock_detect_scopes.side_effect = ValueError("Invalid prompt blocks")

    # Act & Assert
    with pytest.raises(ValueError, match="Invalid prompt blocks"):
        ScopeDetectionHelper.detect_scopes(prompt_blocks)


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_with_none_prompt_blocks(mock_detect_scopes) -> None:
    """Test detect_scopes with None prompt_blocks (edge case)."""
    # Arrange
    prompt_blocks = None
    mock_detect_scopes.return_value = []

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    mock_detect_scopes.assert_called_once_with(None)
    assert result == []


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_preserves_scope_order(mock_detect_scopes) -> None:
    """Test that detect_scopes preserves the order returned by domain service."""
    # Arrange
    prompt_blocks = Mock()
    expected_scopes = ["z-scope", "a-scope", "m-scope"]
    mock_detect_scopes.return_value = expected_scopes

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    assert result == expected_scopes
    assert result[0] == "z-scope"  # Order preserved


@patch("services.context.infrastructure.helpers.scope_detection_helper.detect_scopes")
def test_detect_scopes_with_duplicate_scopes(mock_detect_scopes) -> None:
    """Test detect_scopes when domain service returns duplicates."""
    # Arrange
    prompt_blocks = Mock()
    scopes_with_duplicates = ["scope1", "scope2", "scope1"]
    mock_detect_scopes.return_value = scopes_with_duplicates

    # Act
    result = ScopeDetectionHelper.detect_scopes(prompt_blocks)

    # Assert
    # Helper should return whatever domain service returns (including duplicates)
    assert result == scopes_with_duplicates
