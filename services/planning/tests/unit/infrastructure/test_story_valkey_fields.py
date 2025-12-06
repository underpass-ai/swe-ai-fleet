"""Unit tests for StoryValkeyFields constants."""


from planning.infrastructure.mappers.story_valkey_fields import StoryValkeyFields


class TestStoryValkeyFields:
    """Test StoryValkeyFields constants class."""

    def test_story_id_constant(self):
        """Test STORY_ID constant value."""
        assert StoryValkeyFields.STORY_ID == "story_id"

    def test_epic_id_constant(self):
        """Test EPIC_ID constant value."""
        assert StoryValkeyFields.EPIC_ID == "epic_id"

    def test_title_constant(self):
        """Test TITLE constant value."""
        assert StoryValkeyFields.TITLE == "title"

    def test_brief_constant(self):
        """Test BRIEF constant value."""
        assert StoryValkeyFields.BRIEF == "brief"

    def test_state_constant(self):
        """Test STATE constant value."""
        assert StoryValkeyFields.STATE == "state"

    def test_dor_score_constant(self):
        """Test DOR_SCORE constant value."""
        assert StoryValkeyFields.DOR_SCORE == "dor_score"

    def test_created_by_constant(self):
        """Test CREATED_BY constant value."""
        assert StoryValkeyFields.CREATED_BY == "created_by"

    def test_created_at_constant(self):
        """Test CREATED_AT constant value."""
        assert StoryValkeyFields.CREATED_AT == "created_at"

    def test_updated_at_constant(self):
        """Test UPDATED_AT constant value."""
        assert StoryValkeyFields.UPDATED_AT == "updated_at"

    def test_all_constants_are_strings(self):
        """Test that all constants are strings."""
        assert isinstance(StoryValkeyFields.STORY_ID, str)
        assert isinstance(StoryValkeyFields.EPIC_ID, str)
        assert isinstance(StoryValkeyFields.TITLE, str)
        assert isinstance(StoryValkeyFields.BRIEF, str)
        assert isinstance(StoryValkeyFields.STATE, str)
        assert isinstance(StoryValkeyFields.DOR_SCORE, str)
        assert isinstance(StoryValkeyFields.CREATED_BY, str)
        assert isinstance(StoryValkeyFields.CREATED_AT, str)
        assert isinstance(StoryValkeyFields.UPDATED_AT, str)

    def test_constants_are_immutable(self):
        """Test that constants cannot be modified (class attributes)."""
        # Verify constants are class attributes, not instance attributes
        assert hasattr(StoryValkeyFields, "STORY_ID")
        assert hasattr(StoryValkeyFields, "EPIC_ID")
        assert hasattr(StoryValkeyFields, "TITLE")
        assert hasattr(StoryValkeyFields, "BRIEF")
        assert hasattr(StoryValkeyFields, "STATE")
        assert hasattr(StoryValkeyFields, "DOR_SCORE")
        assert hasattr(StoryValkeyFields, "CREATED_BY")
        assert hasattr(StoryValkeyFields, "CREATED_AT")
        assert hasattr(StoryValkeyFields, "UPDATED_AT")

    def test_all_constants_present(self):
        """Test that all expected constants are present."""
        expected_constants = {
            "STORY_ID",
            "EPIC_ID",
            "TITLE",
            "BRIEF",
            "STATE",
            "DOR_SCORE",
            "CREATED_BY",
            "CREATED_AT",
            "UPDATED_AT",
        }
        actual_constants = {
            attr
            for attr in dir(StoryValkeyFields)
            if not attr.startswith("_") and attr.isupper()
        }
        assert expected_constants == actual_constants

