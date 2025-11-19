"""Unit tests for AgentProfile domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.agent_profile import AgentProfile


class TestAgentProfileCreation:
    """Test AgentProfile entity creation."""

    def test_create_profile_with_all_fields(self):
        """Test creating profile with all fields."""
        profile = AgentProfile(
            name="Qwen-7B-Chat",
            model="Qwen/Qwen2.5-7B-Instruct",
            context_window=32768,
            temperature=0.7,
            max_tokens=2048,
        )

        assert profile.name == "Qwen-7B-Chat"
        assert profile.model == "Qwen/Qwen2.5-7B-Instruct"
        assert profile.context_window == 32768
        assert profile.temperature == 0.7
        assert profile.max_tokens == 2048

    def test_create_profile_with_minimum_values(self):
        """Test creating profile with minimum valid values."""
        profile = AgentProfile(
            name="Minimal",
            model="test-model",
            context_window=100,
            temperature=0.0,
            max_tokens=50,
        )

        assert profile.temperature == 0.0
        assert profile.max_tokens == 50
        assert profile.context_window >= profile.max_tokens

    def test_create_profile_with_maximum_values(self):
        """Test creating profile with maximum valid values."""
        profile = AgentProfile(
            name="Maximal",
            model="test-model",
            context_window=32768,
            temperature=2.0,
            max_tokens=16384,
        )

        assert profile.temperature == 2.0
        assert profile.context_window >= profile.max_tokens


class TestAgentProfileValidation:
    """Test AgentProfile validation."""

    def test_profile_raises_error_on_empty_name(self):
        """Test profile raises error on empty name."""
        with pytest.raises(ValueError, match="Profile name cannot be empty"):
            AgentProfile(
                name="",
                model="test-model",
                context_window=1000,
                temperature=0.7,
                max_tokens=500,
            )

    def test_profile_raises_error_on_empty_model(self):
        """Test profile raises error on empty model."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            AgentProfile(
                name="Test",
                model="",
                context_window=1000,
                temperature=0.7,
                max_tokens=500,
            )

    def test_profile_raises_error_on_temperature_below_zero(self):
        """Test profile raises error on temperature below zero."""
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            AgentProfile(
                name="Test",
                model="test-model",
                context_window=1000,
                temperature=-0.1,
                max_tokens=500,
            )

    def test_profile_raises_error_on_temperature_above_two(self):
        """Test profile raises error on temperature above two."""
        with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
            AgentProfile(
                name="Test",
                model="test-model",
                context_window=1000,
                temperature=2.1,
                max_tokens=500,
            )

    def test_profile_raises_error_on_max_tokens_zero(self):
        """Test profile raises error on max_tokens zero."""
        with pytest.raises(ValueError, match="Max tokens must be positive"):
            AgentProfile(
                name="Test",
                model="test-model",
                context_window=1000,
                temperature=0.7,
                max_tokens=0,
            )

    def test_profile_raises_error_on_max_tokens_negative(self):
        """Test profile raises error on max_tokens negative."""
        with pytest.raises(ValueError, match="Max tokens must be positive"):
            AgentProfile(
                name="Test",
                model="test-model",
                context_window=1000,
                temperature=0.7,
                max_tokens=-1,
            )

    def test_profile_raises_error_when_context_window_smaller_than_max_tokens(self):
        """Test profile raises error when context_window < max_tokens."""
        with pytest.raises(
            ValueError,
            match="Context window.*must be >= max_tokens",
        ):
            AgentProfile(
                name="Test",
                model="test-model",
                context_window=500,
                temperature=0.7,
                max_tokens=1000,
            )

    def test_profile_accepts_context_window_equal_to_max_tokens(self):
        """Test profile accepts context_window equal to max_tokens."""
        profile = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.7,
            max_tokens=1000,
        )

        assert profile.context_window == profile.max_tokens


class TestAgentProfileImmutability:
    """Test AgentProfile immutability."""

    def test_profile_is_immutable(self):
        """Test profile is frozen (immutable)."""
        profile = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.7,
            max_tokens=500,
        )

        with pytest.raises(AttributeError):
            profile.name = "NewName"  # type: ignore

        with pytest.raises(AttributeError):
            profile.temperature = 0.8  # type: ignore


class TestAgentProfileEquality:
    """Test AgentProfile equality and comparison."""

    def test_profiles_with_same_values_are_equal(self):
        """Test profiles with identical values are equal."""
        profile1 = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.7,
            max_tokens=500,
        )
        profile2 = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.7,
            max_tokens=500,
        )

        assert profile1 == profile2

    def test_profiles_with_different_temperature_are_not_equal(self):
        """Test profiles with different temperature are not equal."""
        profile1 = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.7,
            max_tokens=500,
        )
        profile2 = AgentProfile(
            name="Test",
            model="test-model",
            context_window=1000,
            temperature=0.8,
            max_tokens=500,
        )

        assert profile1 != profile2

