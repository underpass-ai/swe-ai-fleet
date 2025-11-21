"""Unit tests for PhaseTransition domain entity."""

import pytest
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.phase_transition import PhaseTransition

pytestmark = pytest.mark.unit


def test_phase_transition_creation():
    """Test creating a valid PhaseTransition."""
    # Act
    transition = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:00:00Z",
    )

    # Assert
    assert transition.story_id.value == "STORY-123"
    assert transition.from_phase == "DISCOVERY"
    assert transition.to_phase == "PLANNING"
    assert transition.timestamp == "2025-11-10T19:00:00Z"


def test_phase_transition_immutable():
    """Test that PhaseTransition is immutable."""
    transition = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="PLANNING",
        to_phase="BUILD",
        timestamp="2025-11-10T19:00:00Z",
    )

    # Assert - should not be able to modify
    with pytest.raises(AttributeError):
        transition.from_phase = "DISCOVERY"


def test_phase_transition_validates_required_fields():
    """Test that empty phases raise validation error."""
    # Act & Assert
    with pytest.raises(ValueError, match="from_phase cannot be empty"):
        PhaseTransition(
            story_id=StoryId("STORY-123"),
            from_phase="",
            to_phase="PLANNING",
            timestamp="2025-11-10T19:00:00Z",
        )

    with pytest.raises(ValueError, match="to_phase cannot be empty"):
        PhaseTransition(
            story_id=StoryId("STORY-123"),
            from_phase="DISCOVERY",
            to_phase="",
            timestamp="2025-11-10T19:00:00Z",
        )

    with pytest.raises(ValueError, match="timestamp cannot be empty"):
        PhaseTransition(
            story_id=StoryId("STORY-123"),
            from_phase="DISCOVERY",
            to_phase="PLANNING",
            timestamp="",
        )


def test_phase_transition_to_string():
    """Test PhaseTransition string representation."""
    transition = PhaseTransition(
        story_id=StoryId("STORY-456"),
        from_phase="BUILD",
        to_phase="VALIDATE",
        timestamp="2025-11-10T19:00:00Z",
    )

    result = transition.get_log_context()

    assert "STORY-456" in str(result)
    assert "BUILD" in str(result)
    assert "VALIDATE" in str(result)


def test_phase_transition_equality():
    """Test PhaseTransition equality comparison."""
    transition1 = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:00:00Z",
    )

    transition2 = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:00:00Z",
    )

    transition3 = PhaseTransition(
        story_id=StoryId("STORY-456"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:01:00Z",
    )

    assert transition1 == transition2
    assert transition1 != transition3


def test_phase_transition_all_phases():
    """Test PhaseTransition with all valid phases."""
    phases = ["DISCOVERY", "PLANNING", "BUILD", "VALIDATE", "DEPLOY", "MAINTAIN"]

    for i in range(len(phases) - 1):
        transition = PhaseTransition(
            story_id=StoryId(f"STORY-{i}"),
            from_phase=phases[i],
            to_phase=phases[i + 1],
            timestamp=f"2025-11-10T19:{i:02d}:00Z",
        )

        assert transition.from_phase == phases[i]
        assert transition.to_phase == phases[i + 1]
        assert len(transition.timestamp) > 0


def test_phase_transition_get_entity_id():
    """Test get_entity_id method."""
    transition = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:00:00Z",
    )

    entity_id = transition.get_entity_id()

    assert entity_id == "STORY-123:2025-11-10T19:00:00Z"


def test_phase_transition_to_graph_properties():
    """Test to_graph_properties method."""
    transition = PhaseTransition(
        story_id=StoryId("STORY-456"),
        from_phase="PLANNING",
        to_phase="BUILD",
        timestamp="2025-11-10T20:00:00Z",
    )

    properties = transition.to_graph_properties()

    assert properties["story_id"] == "STORY-456"
    assert properties["from_phase"] == "PLANNING"
    assert properties["to_phase"] == "BUILD"
    assert properties["timestamp"] == "2025-11-10T20:00:00Z"


def test_phase_transition_get_graph_label():
    """Test get_graph_label method."""
    transition = PhaseTransition(
        story_id=StoryId("STORY-789"),
        from_phase="BUILD",
        to_phase="VALIDATE",
        timestamp="2025-11-10T21:00:00Z",
    )

    label = transition.get_graph_label()

    assert label == "PhaseTransition"

