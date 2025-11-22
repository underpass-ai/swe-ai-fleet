"""Unit tests for FileExecutionResult domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.results.file_execution_result import FileExecutionResult


class TestFileExecutionResultCreation:
    """Test FileExecutionResult entity creation."""

    def test_create_successful_result(self):
        """Test creating successful result."""
        result = FileExecutionResult(success=True, content="file content")

        assert result.success is True
        assert result.content == "file content"
        assert result.error is None

    def test_create_failed_result(self):
        """Test creating failed result."""
        result = FileExecutionResult(
            success=False,
            content=None,
            error="File not found",
        )

        assert result.success is False
        assert result.content is None
        assert result.error == "File not found"

    def test_create_result_with_none_content(self):
        """Test creating result with None content."""
        result = FileExecutionResult(success=True, content=None)

        assert result.success is True
        assert result.content is None


class TestFileExecutionResultImmutability:
    """Test FileExecutionResult immutability."""

    def test_result_is_immutable(self):
        """Test result is frozen (immutable)."""
        result = FileExecutionResult(success=True, content="test")

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

        with pytest.raises(AttributeError):
            result.content = "new content"  # type: ignore


class TestFileExecutionResultEquality:
    """Test FileExecutionResult equality and comparison."""

    def test_results_with_same_values_are_equal(self):
        """Test results with identical values are equal."""
        result1 = FileExecutionResult(success=True, content="content")
        result2 = FileExecutionResult(success=True, content="content")

        assert result1 == result2

    def test_results_with_different_success_are_not_equal(self):
        """Test results with different success values are not equal."""
        result1 = FileExecutionResult(success=True, content="content")
        result2 = FileExecutionResult(success=False, content="content")

        assert result1 != result2

