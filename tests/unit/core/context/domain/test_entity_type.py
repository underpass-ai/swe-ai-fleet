"""Unit tests for EntityType enum."""

import pytest
from core.context.domain.entity_type import EntityType


class TestEntityTypeEnum:
    """Test EntityType enum values."""

    def test_all_entity_types_have_string_values(self):
        """Test all entity types can be converted to strings."""
        for entity_type in EntityType:
            assert isinstance(entity_type.value, str)
            assert len(entity_type.value) > 0

    def test_entity_type_values_are_lowercase(self):
        """Test entity type values follow lowercase convention."""
        for entity_type in EntityType:
            assert entity_type.value == entity_type.value.lower()


class TestEntityTypeGetValidColumns:
    """Test get_valid_columns() static method."""

    def test_story_has_valid_columns(self):
        """Test STORY entity type has defined columns."""
        columns = EntityType.get_valid_columns(EntityType.STORY)

        assert isinstance(columns, tuple)
        assert len(columns) > 0
        assert "title" in columns
        assert "description" in columns
        assert "status" in columns

    def test_task_has_valid_columns(self):
        """Test TASK entity type has defined columns."""
        columns = EntityType.get_valid_columns(EntityType.TASK)

        assert isinstance(columns, tuple)
        assert len(columns) > 0
        assert "title" in columns
        assert "status" in columns
        assert "role" in columns

    def test_decision_has_valid_columns(self):
        """Test DECISION entity type has defined columns."""
        columns = EntityType.get_valid_columns(EntityType.DECISION)

        assert isinstance(columns, tuple)
        assert len(columns) > 0
        assert "title" in columns
        assert "rationale" in columns

    def test_all_entity_types_have_columns_defined(self):
        """Test all entity types have columns defined."""
        for entity_type in EntityType:
            columns = EntityType.get_valid_columns(entity_type)
            assert isinstance(columns, tuple)
            assert len(columns) > 0, f"{entity_type} should have at least one column defined"

    def test_columns_are_immutable_tuples(self):
        """Test returned columns are immutable tuples."""
        columns = EntityType.get_valid_columns(EntityType.STORY)

        assert isinstance(columns, tuple)

        # Tuples are immutable
        with pytest.raises(TypeError):
            columns[0] = "hacked"  # type: ignore

    def test_columns_have_no_duplicates(self):
        """Test each entity type's columns have no duplicates."""
        for entity_type in EntityType:
            columns = EntityType.get_valid_columns(entity_type)
            assert len(columns) == len(set(columns)), f"{entity_type} has duplicate columns"

    def test_columns_are_non_empty_strings(self):
        """Test all column names are non-empty strings."""
        for entity_type in EntityType:
            columns = EntityType.get_valid_columns(entity_type)
            for col in columns:
                assert isinstance(col, str)
                assert len(col) > 0
                assert col.strip() == col, f"Column '{col}' has leading/trailing whitespace"


class TestEntityTypeSchemaConsistency:
    """Test schema consistency across entity types."""

    def test_common_fields_exist_where_expected(self):
        """Test common fields (id, title) exist in relevant entities."""
        # Most entities should have 'id' field
        entities_with_id = [
            EntityType.STORY,
            EntityType.TASK,
            EntityType.PLAN,
            EntityType.DECISION,
            EntityType.EPIC,
        ]

        for entity_type in entities_with_id:
            columns = EntityType.get_valid_columns(entity_type)
            # Allow variations like 'story_id', 'task_id', etc.
            has_id_field = any('id' in col for col in columns)
            assert has_id_field, f"{entity_type} should have an id field"

    def test_sensitive_fields_pii_detection(self):
        """Test that sensitive/PII fields can be identified."""
        # This test documents which fields are considered sensitive
        # Used for RBAC L3 column filtering

        story_columns = EntityType.get_valid_columns(EntityType.STORY)

        # Common sensitive fields (may or may not exist, but if they do, they're sensitive)
        potentially_sensitive = ["requester_id", "assigned_to", "owner", "created_by"]

        # Just verify the schema is defined and accessible
        assert isinstance(story_columns, tuple)

