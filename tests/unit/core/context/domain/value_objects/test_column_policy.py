"""Unit tests for ColumnPolicy Value Object."""

import pytest

from core.context.domain.role import Role
from core.context.domain.entity_type import EntityType
from core.context.domain.value_objects.column_policy import ColumnPolicy


class TestColumnPolicy:
    """Test suite for ColumnPolicy VO."""
    
    def test_column_policy_creation_with_valid_columns(self) -> None:
        """Test creating ColumnPolicy with valid columns for entity type."""
        policy = ColumnPolicy(
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
            allowed_columns=("title", "description", "status"),
        )
        
        assert policy.entity_type == EntityType.STORY
        assert policy.role == Role.DEVELOPER
        assert policy.allowed_columns == ("title", "description", "status")
    
    def test_allows_column_returns_true_for_whitelisted_column(self) -> None:
        """Test that allows_column() returns True for whitelisted columns."""
        policy = ColumnPolicy(
            entity_type=EntityType.TASK,
            role=Role.QA,
            allowed_columns=("task_id", "title", "status"),
        )
        
        assert policy.allows_column("task_id") is True
        assert policy.allows_column("title") is True
        assert policy.allows_column("status") is True
    
    def test_allows_column_returns_false_for_non_whitelisted_column(self) -> None:
        """Test that allows_column() returns False for non-whitelisted columns."""
        policy = ColumnPolicy(
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
            allowed_columns=("title", "status"),
        )
        
        assert policy.allows_column("budget_allocated") is False
        assert policy.allows_column("estimated_hours") is False
        assert policy.allows_column("nonexistent_column") is False
    
    def test_column_policy_fails_fast_on_empty_allowed_columns(self) -> None:
        """Test that ColumnPolicy raises ValueError if allowed_columns is empty."""
        with pytest.raises(ValueError, match="allowed_columns cannot be empty"):
            ColumnPolicy(
                entity_type=EntityType.STORY,
                role=Role.DEVELOPER,
                allowed_columns=(),
            )
    
    def test_column_policy_fails_fast_on_invalid_column_name(self) -> None:
        """Test that ColumnPolicy raises ValueError for invalid column names."""
        with pytest.raises(ValueError, match="Invalid column 'invalid_col' for entity type story"):
            ColumnPolicy(
                entity_type=EntityType.STORY,
                role=Role.DEVELOPER,
                allowed_columns=("title", "invalid_col"),
            )
    
    def test_column_policy_fails_fast_on_empty_column_name(self) -> None:
        """Test that ColumnPolicy raises ValueError for empty column names."""
        with pytest.raises(ValueError, match="Column name cannot be empty"):
            ColumnPolicy(
                entity_type=EntityType.TASK,
                role=Role.DEVELOPER,
                allowed_columns=("task_id", ""),
            )
    
    def test_column_policy_validates_against_entity_type_schema(self) -> None:
        """Test that ColumnPolicy validates columns against EntityType schema."""
        # Valid: all columns exist in STORY schema
        policy = ColumnPolicy(
            entity_type=EntityType.STORY,
            role=Role.PRODUCT_OWNER,
            allowed_columns=("story_id", "title", "description", "status", "assigned_to"),
        )
        assert policy is not None
        
        # Invalid: "task_id" doesn't exist in STORY schema
        with pytest.raises(ValueError, match="Invalid column 'task_id' for entity type story"):
            ColumnPolicy(
                entity_type=EntityType.STORY,
                role=Role.DEVELOPER,
                allowed_columns=("story_id", "task_id"),  # task_id not in story schema
            )
    
    def test_column_policy_is_immutable(self) -> None:
        """Test that ColumnPolicy is frozen (immutable)."""
        policy = ColumnPolicy(
            entity_type=EntityType.DECISION,
            role=Role.ARCHITECT,
            allowed_columns=("id", "title", "rationale"),
        )
        
        with pytest.raises(AttributeError):
            policy.role = Role.DEVELOPER  # type: ignore
        
        with pytest.raises(AttributeError):
            policy.allowed_columns = ("title",)  # type: ignore
    
    def test_column_policy_for_different_entity_types(self) -> None:
        """Test ColumnPolicy works for all EntityType values."""
        # Test TASK
        task_policy = ColumnPolicy(
            entity_type=EntityType.TASK,
            role=Role.DEVELOPER,
            allowed_columns=("task_id", "title", "status"),
        )
        assert task_policy.allows_column("task_id") is True
        
        # Test DECISION
        decision_policy = ColumnPolicy(
            entity_type=EntityType.DECISION,
            role=Role.ARCHITECT,
            allowed_columns=("id", "title", "rationale"),
        )
        assert decision_policy.allows_column("rationale") is True
        
        # Test EPIC
        epic_policy = ColumnPolicy(
            entity_type=EntityType.EPIC,
            role=Role.PRODUCT_OWNER,
            allowed_columns=("epic_id", "title", "status"),
        )
        assert epic_policy.allows_column("epic_id") is True

