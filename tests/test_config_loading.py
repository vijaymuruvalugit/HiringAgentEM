"""Tests for configuration loading functionality."""
import pytest
import yaml
from pathlib import Path
import tempfile

from tests.test_helpers import load_config


class TestConfigLoading:
    """Test configuration loading from YAML files."""

    def test_load_valid_config(self, sample_config, tmp_path):
        """Test loading a valid config file."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)
        
        result = load_config(config_file)
        assert result == sample_config
        assert "n8n" in result
        assert "agents" in result["n8n"]

    def test_load_nonexistent_file(self):
        """Test loading a non-existent config file."""
        fake_path = Path("/nonexistent/path/config.yaml")
        result = load_config(fake_path)
        assert result == {}

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading an invalid YAML file."""
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")
        
        result = load_config(config_file)
        assert result == {}

    def test_load_empty_file(self, tmp_path):
        """Test loading an empty config file."""
        config_file = tmp_path / "config.yaml"
        config_file.touch()
        
        result = load_config(config_file)
        assert result == {}

    def test_load_config_with_default_path(self, sample_config, tmp_path, monkeypatch):
        """Test loading config using default path."""
        # This test would require mocking the DEFAULT_CONFIG_PATH
        # For now, we test the function directly
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config, f)
        
        result = load_config(config_file)
        assert "n8n" in result

