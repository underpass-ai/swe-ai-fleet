"""Unit tests for ContextVersionHelper."""

import hashlib
import time
from unittest.mock import patch

import pytest
from services.context.infrastructure.helpers.context_version_helper import (
    ContextVersionHelper,
)


def test_generate_version_hash_with_simple_content() -> None:
    """Test generating version hash with simple content."""
    # Arrange
    content = "test content"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_version_hash(content)

    # Assert
    assert result == expected
    assert len(result) == 16


def test_generate_version_hash_with_empty_string() -> None:
    """Test generating version hash with empty string."""
    # Arrange
    content = ""
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_version_hash(content)

    # Assert
    assert result == expected
    assert len(result) == 16


def test_generate_version_hash_with_multiline_content() -> None:
    """Test generating version hash with multiline content."""
    # Arrange
    content = "line1\nline2\nline3"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_version_hash(content)

    # Assert
    assert result == expected


def test_generate_version_hash_is_deterministic() -> None:
    """Test that same content produces same hash."""
    # Arrange
    content = "deterministic test"

    # Act
    result1 = ContextVersionHelper.generate_version_hash(content)
    result2 = ContextVersionHelper.generate_version_hash(content)

    # Assert
    assert result1 == result2


def test_generate_version_hash_different_content_different_hash() -> None:
    """Test that different content produces different hashes."""
    # Arrange
    content1 = "content A"
    content2 = "content B"

    # Act
    result1 = ContextVersionHelper.generate_version_hash(content1)
    result2 = ContextVersionHelper.generate_version_hash(content2)

    # Assert
    assert result1 != result2


def test_generate_version_hash_with_unicode() -> None:
    """Test generating version hash with unicode content."""
    # Arrange
    content = "Hello 世界 🌍"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_version_hash(content)

    # Assert
    assert result == expected
    assert len(result) == 16


def test_generate_new_version_returns_timestamp() -> None:
    """Test that generate_new_version returns a timestamp."""
    # Arrange
    story_id = "story-123"
    before = int(time.time())

    # Act
    result = ContextVersionHelper.generate_new_version(story_id)
    after = int(time.time())

    # Assert
    assert isinstance(result, int)
    assert before <= result <= after + 1  # Allow 1 second tolerance


def test_generate_new_version_is_monotonically_increasing() -> None:
    """Test that successive calls return increasing versions."""
    # Arrange
    story_id = "story-123"

    # Act
    version1 = ContextVersionHelper.generate_new_version(story_id)
    time.sleep(0.01)  # Small delay to ensure different timestamps
    version2 = ContextVersionHelper.generate_new_version(story_id)

    # Assert
    assert version2 >= version1


@patch("services.context.infrastructure.helpers.context_version_helper.time.time")
def test_generate_new_version_uses_time_module(mock_time) -> None:
    """Test that generate_new_version uses time.time()."""
    # Arrange
    mock_time.return_value = 1234567890.5
    story_id = "story-123"

    # Act
    result = ContextVersionHelper.generate_new_version(story_id)

    # Assert
    mock_time.assert_called_once()
    assert result == 1234567890


def test_generate_context_hash_with_story_id_and_version() -> None:
    """Test generating context hash with story_id and version."""
    # Arrange
    story_id = "story-123"
    version = 12345
    content = f"{story_id}:{version}"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_context_hash(story_id, version)

    # Assert
    assert result == expected
    assert len(result) == 16


def test_generate_context_hash_is_deterministic() -> None:
    """Test that same inputs produce same hash."""
    # Arrange
    story_id = "story-456"
    version = 67890

    # Act
    result1 = ContextVersionHelper.generate_context_hash(story_id, version)
    result2 = ContextVersionHelper.generate_context_hash(story_id, version)

    # Assert
    assert result1 == result2


def test_generate_context_hash_different_story_ids() -> None:
    """Test that different story_ids produce different hashes."""
    # Arrange
    version = 100

    # Act
    result1 = ContextVersionHelper.generate_context_hash("story-1", version)
    result2 = ContextVersionHelper.generate_context_hash("story-2", version)

    # Assert
    assert result1 != result2


def test_generate_context_hash_different_versions() -> None:
    """Test that different versions produce different hashes."""
    # Arrange
    story_id = "story-123"

    # Act
    result1 = ContextVersionHelper.generate_context_hash(story_id, 100)
    result2 = ContextVersionHelper.generate_context_hash(story_id, 200)

    # Assert
    assert result1 != result2


def test_generate_context_hash_with_zero_version() -> None:
    """Test generating context hash with version 0."""
    # Arrange
    story_id = "story-123"
    version = 0
    content = f"{story_id}:{version}"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_context_hash(story_id, version)

    # Assert
    assert result == expected


def test_generate_context_hash_with_negative_version() -> None:
    """Test generating context hash with negative version (edge case)."""
    # Arrange
    story_id = "story-123"
    version = -1
    content = f"{story_id}:{version}"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Act
    result = ContextVersionHelper.generate_context_hash(story_id, version)

    # Assert
    assert result == expected


def test_all_hash_methods_return_16_characters() -> None:
    """Test that all hash methods return exactly 16 characters."""
    # Act
    hash1 = ContextVersionHelper.generate_version_hash("test")
    hash2 = ContextVersionHelper.generate_context_hash("story-1", 100)

    # Assert
    assert len(hash1) == 16
    assert len(hash2) == 16


def test_hash_methods_return_hexadecimal_strings() -> None:
    """Test that hash methods return valid hexadecimal strings."""
    # Act
    hash1 = ContextVersionHelper.generate_version_hash("test")
    hash2 = ContextVersionHelper.generate_context_hash("story-1", 100)

    # Assert: All characters should be valid hex
    assert all(c in "0123456789abcdef" for c in hash1)
    assert all(c in "0123456789abcdef" for c in hash2)
