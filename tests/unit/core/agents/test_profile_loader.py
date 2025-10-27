"""Unit tests for core.agents.profile_loader

Tests AgentProfile dataclass and get_profile_for_role function with comprehensive coverage
of loading, defaults, error handling, and edge cases.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.agents_and_tools.agents.profile_loader import (
    AgentProfile,
    get_profile_for_role,
)


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

    def test_agent_profile_from_yaml_success(self):
        """Test loading AgentProfile from YAML file."""
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
name: test-architect
model: databricks/dbrx-instruct
context_window: 128000
temperature: 0.3
max_tokens: 8192
""")
            yaml_path = f.name

        try:
            profile = AgentProfile.from_yaml(yaml_path)
            assert profile.name == "test-architect"
            assert profile.model == "databricks/dbrx-instruct"
            assert profile.context_window == 128000
            assert profile.temperature == 0.3
            assert profile.max_tokens == 8192
        finally:
            Path(yaml_path).unlink()

    def test_agent_profile_from_yaml_with_defaults(self):
        """Test YAML loading with missing optional fields uses defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
name: minimal
model: test-model
""")
            yaml_path = f.name

        try:
            profile = AgentProfile.from_yaml(yaml_path)
            assert profile.name == "minimal"
            assert profile.model == "test-model"
            assert profile.context_window == 32768  # default
            assert profile.temperature == 0.7  # default
            assert profile.max_tokens == 4096  # default
        finally:
            Path(yaml_path).unlink()

    def test_agent_profile_from_yaml_file_not_found(self):
        """Test from_yaml raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Profile not found"):
            AgentProfile.from_yaml("/nonexistent/profile.yaml")

    def test_agent_profile_from_yaml_missing_pyyaml(self):
        """Test from_yaml raises ImportError when pyyaml not available."""
        with patch("core.agents_and_tools.agents.profile_loader.YAML_AVAILABLE", False):
            with pytest.raises(ImportError, match="pyyaml required"):
                AgentProfile.from_yaml("/some/path.yaml")


class TestGetProfileForRole:
    """Test get_profile_for_role function"""

    def test_get_profile_for_role_architect(self):
        """Test getting ARCHITECT profile returns correct defaults."""
        profile = get_profile_for_role("ARCHITECT")

        assert profile["model"] == "databricks/dbrx-instruct"
        assert profile["temperature"] == 0.3
        assert profile["max_tokens"] == 8192
        assert profile["context_window"] == 128000

    def test_get_profile_for_role_dev(self):
        """Test getting DEV profile."""
        profile = get_profile_for_role("DEV")

        assert profile["model"] == "deepseek-coder:33b"
        assert profile["temperature"] == 0.7
        assert profile["max_tokens"] == 4096
        assert profile["context_window"] == 32768

    def test_get_profile_for_role_qa(self):
        """Test getting QA profile."""
        profile = get_profile_for_role("QA")

        assert profile["model"] == "mistralai/Mistral-7B-Instruct-v0.3"
        assert profile["temperature"] == 0.5
        assert profile["max_tokens"] == 3072
        assert profile["context_window"] == 32768

    def test_get_profile_for_role_devops(self):
        """Test getting DEVOPS profile."""
        profile = get_profile_for_role("DEVOPS")

        assert profile["model"] == "Qwen/Qwen2.5-Coder-14B-Instruct"
        assert profile["temperature"] == 0.6
        assert profile["max_tokens"] == 4096
        assert profile["context_window"] == 32768

    def test_get_profile_for_role_data(self):
        """Test getting DATA profile."""
        profile = get_profile_for_role("DATA")

        assert profile["model"] == "deepseek-ai/deepseek-coder-6.7b-instruct"
        assert profile["temperature"] == 0.7
        assert profile["max_tokens"] == 4096
        assert profile["context_window"] == 32768

    def test_get_profile_for_role_lowercase_input(self):
        """Test role name is case-insensitive."""
        profile_upper = get_profile_for_role("ARCHITECT")
        profile_lower = get_profile_for_role("architect")
        profile_mixed = get_profile_for_role("ArChItEcT")

        assert profile_upper == profile_lower == profile_mixed

    def test_get_profile_for_role_unknown_role(self):
        """Test unknown role returns generic fallback."""
        profile = get_profile_for_role("UNKNOWN_ROLE")

        assert profile["model"] == "Qwen/Qwen3-0.6B"
        assert profile["temperature"] == 0.7
        assert profile["max_tokens"] == 2048
        assert profile["context_window"] == 8192

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

            profile = get_profile_for_role("ARCHITECT", profiles_dir=tmpdir)

            assert profile["model"] == "custom-model"
            assert profile["temperature"] == 0.1
            assert profile["max_tokens"] == 16384
            assert profile["context_window"] == 256000

    def test_get_profile_for_role_custom_dir_nonexistent(self):
        """Test with nonexistent custom directory falls back to generic defaults."""
        profile = get_profile_for_role("DEV", profiles_dir="/nonexistent/dir")

        # Should fall back to generic defaults
        assert profile["model"] == "Qwen/Qwen3-0.6B"

    def test_get_profile_for_role_custom_dir_no_matching_file(self):
        """Test custom directory exists but no matching profile file falls back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create roles.yaml mapping (required for fail-first approach)
            roles_file = Path(tmpdir) / "roles.yaml"
            roles_file.write_text("""
role_files:
  DEV: developer.yaml
""")
            
            # Create directory but don't add profile file
            profile = get_profile_for_role("DEV", profiles_dir=tmpdir)

            # Should fall back to generic defaults
            assert profile["model"] == "Qwen/Qwen3-0.6B"

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
                get_profile_for_role("ARCHITECT", profiles_dir=tmpdir)

    def test_get_profile_for_role_pyyaml_unavailable(self):
        """Test when YAML is unavailable falls back to generic defaults."""
        with patch("core.agents_and_tools.agents.profile_loader.YAML_AVAILABLE", False):
            profile = get_profile_for_role("DEV")

            # Should use generic defaults
            assert profile["model"] == "Qwen/Qwen3-0.6B"

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

            profile = get_profile_for_role("QA", profiles_dir=tmpdir)

            assert profile["model"] == "custom-qa-model"
            assert profile["temperature"] == 0.2

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

            profile = get_profile_for_role("DEV", profiles_dir=tmpdir)

            assert profile["model"] == "custom-dev-model"

    def test_get_profile_for_role_returns_dict_with_required_keys(self):
        """Test returned profile always has required keys."""
        required_keys = {"model", "temperature", "max_tokens", "context_window"}

        for role in ["ARCHITECT", "DEV", "QA", "DEVOPS", "DATA"]:
            profile = get_profile_for_role(role)
            assert set(profile.keys()) == required_keys

    def test_profile_values_are_sane(self):
        """Test profile values are within reasonable ranges."""
        for role in ["ARCHITECT", "DEV", "QA", "DEVOPS", "DATA"]:
            profile = get_profile_for_role(role)

            # Temperature should be between 0 and 2 (typically)
            assert 0 <= profile["temperature"] <= 2

            # Max tokens should be positive
            assert profile["max_tokens"] > 0

            # Context window should be larger than max_tokens
            assert profile["context_window"] >= profile["max_tokens"]

            # Model name should not be empty
            assert len(profile["model"]) > 0
