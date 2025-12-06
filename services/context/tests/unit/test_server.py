"""
Unit tests for Context Service gRPC server helpers.

Tests only the pure functions (load_scopes_config).
Integration tests should cover the full servicer initialization and gRPC methods.
"""

from unittest.mock import mock_open, patch

import pytest

pytestmark = pytest.mark.unit


class TestLoadScopesConfig:
    """Test load_scopes_config function."""

    def test_load_scopes_config_success(self):
        """Test loading valid YAML config."""
        from services.context.server import load_scopes_config

        yaml_content = """
phases:
  DISCOVERY:
    sections: ["project", "epic", "story"]
  BUILD:
    sections: ["task", "code"]
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = load_scopes_config("/fake/path.yaml")

        assert "DISCOVERY" in result
        assert result["DISCOVERY"]["sections"] == ["project", "epic", "story"]

    def test_load_scopes_config_file_not_found(self):
        """Test handling of missing config file."""
        from services.context.server import load_scopes_config

        with patch("builtins.open", side_effect=FileNotFoundError()):
            result = load_scopes_config("/nonexistent.yaml")

        assert result == {}

    def test_load_scopes_config_invalid_yaml(self):
        """Test handling of invalid YAML."""
        from services.context.server import load_scopes_config

        with patch("builtins.open", mock_open(read_data="invalid: yaml: :")):
            with patch("yaml.safe_load", side_effect=Exception("Invalid YAML")):
                result = load_scopes_config("/bad.yaml")

        assert result == {}

    def test_load_scopes_config_empty_phases(self):
        """Test handling of YAML without phases key."""
        from services.context.server import load_scopes_config

        yaml_content = "other_key: value"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = load_scopes_config("/empty.yaml")

        assert result == {}

    def test_load_scopes_config_default_path(self):
        """Test load_scopes_config with default path (None)."""
        from services.context.server import load_scopes_config

        yaml_content = """
phases:
  DISCOVERY:
    sections: ["project"]
"""
        with patch("builtins.open", mock_open(read_data=yaml_content)) as mock_file:
            with patch("os.path.join") as mock_join:
                # Mock the path construction
                mock_join.return_value = "/fake/default/path.yaml"
                result = load_scopes_config(None)

        assert "DISCOVERY" in result
        mock_file.assert_called_once()
        mock_join.assert_called()
