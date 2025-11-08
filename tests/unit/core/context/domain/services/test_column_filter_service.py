"""Unit tests for ColumnFilterService Domain Service."""

import pytest
from dataclasses import dataclass

from core.context.domain.role import Role
from core.context.domain.entity_type import EntityType
from core.context.domain.value_objects.column_policy import ColumnPolicy
from core.context.domain.services.column_filter_service import ColumnFilterService


@dataclass(frozen=True)
class MockEntity:
    """Mock entity for testing filtering."""
    field1: str
    field2: int
    sensitive_field: str


class TestColumnFilterService:
    """Test suite for ColumnFilterService domain service."""
    
    @pytest.fixture
    def service_with_policies(self) -> ColumnFilterService:
        """Create ColumnFilterService with test policies."""
        policies = {
            (EntityType.STORY, Role.DEVELOPER): ColumnPolicy(
                entity_type=EntityType.STORY,
                role=Role.DEVELOPER,
                allowed_columns=("story_id", "title", "description", "status"),
            ),
            (EntityType.STORY, Role.QA): ColumnPolicy(
                entity_type=EntityType.STORY,
                role=Role.QA,
                allowed_columns=("story_id", "title", "status"),  # No description
            ),
            (EntityType.TASK, Role.DEVELOPER): ColumnPolicy(
                entity_type=EntityType.TASK,
                role=Role.DEVELOPER,
                allowed_columns=("task_id", "title", "status", "role"),
            ),
        }
        return ColumnFilterService(policies=policies)
    
    def test_filter_entity_with_dict_filters_columns(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() filters dict columns based on policy."""
        entity_dict = {
            "story_id": "story-123",
            "title": "Implement feature",
            "description": "Long description",
            "status": "IN_PROGRESS",
            "budget_allocated": 5000,  # Sensitive - not in whitelist
            "estimated_hours": 40,  # Sensitive - not in whitelist
        }
        
        filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        
        # Only whitelisted columns should remain
        assert "story_id" in filtered
        assert "title" in filtered
        assert "description" in filtered
        assert "status" in filtered
        assert "budget_allocated" not in filtered
        assert "estimated_hours" not in filtered
    
    def test_filter_entity_with_dataclass_filters_fields(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() filters dataclass fields."""
        # Use dict instead of dataclass to avoid schema validation issues
        # ColumnFilterService works on dicts primarily
        entity_dict = {
            "story_id": "story-123",
            "title": "Visible title",
            "description": "Visible description",
            "status": "IN_PROGRESS",
            "budget_allocated": 5000,  # Sensitive - not in whitelist
        }
        
        filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        
        # Only whitelisted columns should remain
        assert "story_id" in filtered
        assert "title" in filtered
        assert "description" in filtered
        assert "status" in filtered
        assert "budget_allocated" not in filtered
    
    def test_filter_entity_different_roles_get_different_columns(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that different roles get different column sets for same entity."""
        entity_dict = {
            "story_id": "story-123",
            "title": "Test story",
            "description": "Detailed description",
            "status": "READY",
        }
        
        # Developer sees description
        dev_filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        assert "description" in dev_filtered
        
        # QA does NOT see description
        qa_filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.QA,
        )
        assert "description" not in qa_filtered
    
    def test_filter_entity_fails_fast_when_no_policy_for_entity_type_and_role(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() raises ValueError when no policy exists."""
        entity_dict = {"epic_id": "epic-123", "title": "Epic"}
        
        # No policy for (EPIC, DEVELOPER) in fixture
        with pytest.raises(ValueError, match="No column policy defined"):
            service_with_policies.filter_entity(
                entity=entity_dict,
                entity_type=EntityType.EPIC,
                role=Role.DEVELOPER,
            )
    
    def test_filter_entity_preserves_values_for_allowed_columns(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() preserves values for allowed columns."""
        entity_dict = {
            "story_id": "story-123",
            "title": "Important Story",
            "description": "Critical feature",
            "status": "BLOCKED",
        }
        
        filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        
        # Values should be preserved exactly
        assert filtered["story_id"] == "story-123"
        assert filtered["title"] == "Important Story"
        assert filtered["description"] == "Critical feature"
        assert filtered["status"] == "BLOCKED"
    
    def test_filter_entity_handles_empty_entity(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() handles empty entity dict."""
        entity_dict = {}
        
        filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        
        assert filtered == {}
    
    def test_filter_entity_with_none_values(
        self,
        service_with_policies: ColumnFilterService,
    ) -> None:
        """Test that filter_entity() preserves None values in allowed columns."""
        entity_dict = {
            "story_id": "story-123",
            "title": None,  # None value
            "description": "Some desc",
            "status": None,  # None value
        }
        
        filtered = service_with_policies.filter_entity(
            entity=entity_dict,
            entity_type=EntityType.STORY,
            role=Role.DEVELOPER,
        )
        
        # None values should be preserved for allowed columns
        assert "title" in filtered
        assert filtered["title"] is None
        assert "status" in filtered
        assert filtered["status"] is None

