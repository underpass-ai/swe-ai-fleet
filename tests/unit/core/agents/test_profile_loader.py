"""Unit tests for core.agents.profile_loader

Tests AgentProfile dataclass and get_profile_for_role function with comprehensive coverage
of loading, defaults, error handling, and edge cases.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile
from core.agents_and_tools.agents.profile_loader import get_profile_for_role


# Helper to get default profiles directory
def get_default_profiles_dir():
    """Get the default profiles directory for testing."""
    # __file__ is at tests/unit/core/agents/test_profile_loader.py
    # Go up 4 levels: agents -> core -> unit -> tests -> project root
    # Then into core/agents_and_tools/resources/profiles/
    current_dir = Path(__file__)  # tests/unit/core/agents/test_profile_loader.py
    project_root = current_dir.parent.parent.parent.parent  # up to tests/
    # Now we need to go back to project root (one more level)
    # Actually, tests/unit/core/agents -> go up 4 to get to project root
    # tests -> unit -> core -> agents -> __file__
    # We want: project_root/core/agents_and_tools/resources/profiles
    profiles_path = project_root.parent / "core" / "agents_and_tools" / "resources" / "profiles"
    return str(profiles_path)  # Return as string (profiles_url)


class TestAgentProfile:
    """Test AgentProfile dataclass"""

    def test_agent_profile_creation(self):
        """Test creating AgentProfile with all fields."""
        profile = AgentProfile(
            name="architect",
            model="databricks/dbrx-instruct",
            context_window=128000,
            temperature=0.3,
            max_tokens=8192,
        )

        assert profile.name == "architect"
        assert profile.model == "databricks/dbrx-instruct"
        assert profile.context_window == 128000
        assert profile.temperature == 0.3
        assert profile.max_tokens == 8192




class TestGetProfileForRole:
    """Test get_profile_for_role function"""

    def test_get_profile_for_role_architect(self):
        """Test getting ARCHITECT profile returns AgentProfile."""
        profile = get_profile_for_role("ARCHITECT", get_default_profiles_dir())

        assert profile.model == "databricks/dbrx-instruct"
        assert profile.temperature == 0.3
        assert profile.max_tokens == 8192
        assert profile.context_window == 128000

    def test_get_profile_for_role_dev(self):
        """Test getting DEV profile."""
        profile = get_profile_for_role("DEV", get_default_profiles_dir())

        assert profile.model == "deepseek-coder:33b"
        assert profile.temperature == 0.7
        assert profile.max_tokens == 4096
        assert profile.context_window == 32768

    def test_get_profile_for_role_qa(self):
        """Test getting QA profile."""
        profile = get_profile_for_role("QA", get_default_profiles_dir())

        assert profile.model == "mistralai/Mistral-7B-Instruct-v0.3"
        assert profile.temperature == 0.5
        assert profile.max_tokens == 3072
        assert profile.context_window == 32768

    def test_get_profile_for_role_devops(self):
        """Test getting DEVOPS profile."""
        profile = get_profile_for_role("DEVOPS", get_default_profiles_dir())

        assert profile.model == "Qwen/Qwen2.5-Coder-14B-Instruct"
        assert profile.temperature == 0.6
        assert profile.max_tokens == 4096
        assert profile.context_window == 32768

    def test_get_profile_for_role_data(self):
        """Test getting DATA profile."""
        profile = get_profile_for_role("DATA", get_default_profiles_dir())

        assert profile.model == "deepseek-ai/deepseek-coder-6.7b-instruct"
        assert profile.temperature == 0.7
        assert profile.max_tokens == 4096
        assert profile.context_window == 32768

    def test_get_profile_for_role_lowercase_input(self):
        """Test role name is case-insensitive."""
        profiles_dir = get_default_profiles_dir()
        profile_upper = get_profile_for_role("ARCHITECT", profiles_dir)
        profile_lower = get_profile_for_role("architect", profiles_dir)
        profile_mixed = get_profile_for_role("ArChItEcT", profiles_dir)

        assert profile_upper == profile_lower == profile_mixed

    def test_get_profile_for_role_unknown_role(self):
        """Test unknown role raises FileNotFoundError (fail first)."""
        # Unknown role not in roles.yaml should fail
        with pytest.raises(FileNotFoundError, match="No profile found for role UNKNOWN_ROLE"):
            get_profile_for_role("UNKNOWN_ROLE", get_default_profiles_dir())

    def test_get_profile_for_role_custom_dir_yaml_exists(self):
        """Test loading from custom directory when YAML file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  ARCHITECT: architect.yaml
""")

            # Create architect.yaml in temp directory
            profile_file = Path(tmpdir) / "architect.yaml"
            profile_file.write_text("""
name: custom-architect
model: custom-model
context_window: 256000
temperature: 0.1
max_tokens: 16384
""")

            profile = get_profile_for_role("ARCHITECT", profiles_url=str(tmpdir))

            assert profile.model == "custom-model"
            assert profile.temperature == 0.1
            assert profile.max_tokens == 16384
            assert profile.context_window == 256000

    def test_get_profile_for_role_custom_dir_nonexistent(self):
        """Test with nonexistent custom directory raises FileNotFoundError (fail first)."""
        with pytest.raises(FileNotFoundError):
            get_profile_for_role("DEV", profiles_url="/nonexistent/dir")

    def test_get_profile_for_role_custom_dir_no_matching_file(self):
        """Test custom directory exists but no matching profile file raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping (required for fail-first approach)
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  DEV: developer.yaml
""")

            # Create directory but don't add profile file - should fail
            with pytest.raises(FileNotFoundError):
                get_profile_for_role("DEV", profiles_url=str(tmpdir))

    def test_get_profile_for_role_yaml_load_error(self):
        """Test YAML loading error raises exception (fail fast)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping (required for fail-first approach)
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  ARCHITECT: architect.yaml
""")

            # Create invalid YAML file
            profile_file = Path(tmpdir) / "architect.yaml"
            profile_file.write_text("invalid: yaml: content: [")

            # Should raise exception on invalid YAML (fail fast)
            with pytest.raises(Exception):  # ScannerError from yaml
                get_profile_for_role("ARCHITECT", profiles_url=str(tmpdir))


    def test_get_profile_for_role_maps_role_to_filename(self):
        """Test role names map to correct YAML filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  QA: qa.yaml
""")

            # Create qa.yaml (should map to QA role)
            profile_file = Path(tmpdir) / "qa.yaml"
            profile_file.write_text("""
name: custom-qa
model: custom-qa-model
context_window: 16000
temperature: 0.2
max_tokens: 2048
""")

            profile = get_profile_for_role("QA", profiles_url=str(tmpdir))

            assert profile.model == "custom-qa-model"
            assert profile.temperature == 0.2

    def test_get_profile_for_role_developer_alias(self):
        """Test DEV role maps to developer.yaml filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  DEV: developer.yaml
""")

            # Create developer.yaml (should map to DEV role)
            profile_file = Path(tmpdir) / "developer.yaml"
            profile_file.write_text("""
name: custom-dev
model: custom-dev-model
context_window: 64000
temperature: 0.4
max_tokens: 8192
""")

            profile = get_profile_for_role("DEV", profiles_url=str(tmpdir))

            assert profile.model == "custom-dev-model"

    def test_get_profile_returns_agent_profile_entity(self):
        """Test returned profile is AgentProfile entity with correct attributes."""
        profiles_dir = get_default_profiles_dir()

        for role in ["ARCHITECT", "DEV", "QA", "DEVOPS", "DATA"]:
            profile = get_profile_for_role(role, profiles_dir)

            # Check it's an AgentProfile entity
            assert hasattr(profile, "model")
            assert hasattr(profile, "temperature")
            assert hasattr(profile, "max_tokens")
            assert hasattr(profile, "context_window")
            assert hasattr(profile, "name")

    def test_profile_values_are_sane(self):
        """Test profile values are within reasonable ranges."""
        profiles_dir = get_default_profiles_dir()

        for role in ["ARCHITECT", "DEV", "QA", "DEVOPS", "DATA"]:
            profile = get_profile_for_role(role, profiles_dir)

            # Temperature should be between 0 and 2 (typically)
            assert 0 <= profile.temperature <= 2

            # Max tokens should be positive
            assert profile.max_tokens > 0

            # Context window should be larger than max_tokens
            assert profile.context_window >= profile.max_tokens

            # Model name should not be empty
            assert len(profile.model) > 0
