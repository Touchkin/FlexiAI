"""
Unit tests for FlexiAI configuration management.

Tests the ConfigLoader class for loading configuration from
dictionaries, files, and environment variables.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from flexiai.config import ConfigLoader
from flexiai.exceptions import ConfigurationError
from flexiai.models import FlexiAIConfig


class TestConfigLoaderSingleton:
    """Tests for ConfigLoader singleton pattern."""

    def test_singleton_same_instance(self) -> None:
        """Test that ConfigLoader returns the same instance."""
        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        assert loader1 is loader2

    def test_singleton_reset(self) -> None:
        """Test that reset clears the current config."""
        loader = ConfigLoader()
        config_dict = {
            "providers": [{"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}]
        }
        loader.load_from_dict(config_dict, merge_env=False)
        assert loader.current_config is not None

        loader.reset()
        assert loader.current_config is None


class TestConfigLoaderFromDict:
    """Tests for loading configuration from dictionaries."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.loader.reset()

    def test_load_minimal_config(self) -> None:
        """Test loading minimal valid configuration."""
        config_dict = {
            "providers": [{"name": "openai", "priority": 1, "api_key": "sk-test", "model": "gpt-4"}]
        }
        config = self.loader.load_from_dict(config_dict, merge_env=False)

        assert isinstance(config, FlexiAIConfig)
        assert len(config.providers) == 1
        assert config.providers[0].name == "openai"
        assert config.providers[0].api_key == "sk-test"

    def test_load_full_config(self) -> None:
        """Test loading complete configuration."""
        config_dict = {
            "providers": [
                {
                    "name": "openai",
                    "api_key": "sk-test-1",
                    "model": "gpt-4",
                    "priority": 1,
                },
                {
                    "name": "anthropic",
                    "api_key": "sk-test-2",
                    "model": "claude-3-opus-20240229",
                    "priority": 2,
                },
            ],
            "default_temperature": 0.8,
            "default_max_tokens": 2000,
        }
        config = self.loader.load_from_dict(config_dict, merge_env=False)

        assert len(config.providers) == 2
        assert config.default_temperature == 0.8
        assert config.default_max_tokens == 2000

    def test_load_invalid_config_missing_providers(self) -> None:
        """Test that loading config without providers raises error."""
        config_dict: Dict[str, Any] = {}

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_dict(config_dict, merge_env=False)

        assert "Failed to load configuration from dict" in str(exc_info.value)

    def test_load_invalid_config_empty_providers(self) -> None:
        """Test that loading config with empty providers raises error."""
        config_dict = {"providers": []}

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_dict(config_dict, merge_env=False)

        assert "Failed to load configuration from dict" in str(exc_info.value)

    def test_load_invalid_provider_missing_name(self) -> None:
        """Test that provider without name raises error."""
        config_dict = {"providers": [{"api_key": "sk-test", "model": "gpt-4", "priority": 1}]}

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_dict(config_dict, merge_env=False)

        assert "Failed to load configuration from dict" in str(exc_info.value)

    def test_load_invalid_provider_missing_api_key(self) -> None:
        """Test that provider without API key raises error."""
        config_dict = {"providers": [{"name": "openai", "model": "gpt-4", "priority": 1}]}

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_dict(config_dict, merge_env=False)

        assert "Failed to load configuration from dict" in str(exc_info.value)

    def test_current_config_after_load(self) -> None:
        """Test that current_config is set after loading."""
        config_dict = {
            "providers": [{"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}]
        }
        config = self.loader.load_from_dict(config_dict, merge_env=False)

        assert self.loader.current_config is config


class TestConfigLoaderFromFile:
    """Tests for loading configuration from files."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.loader.reset()

    def test_load_from_json_file(self) -> None:
        """Test loading configuration from JSON file."""
        config_dict = {
            "providers": [
                {"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}
            ],
            "default_temperature": 0.7,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_dict, f)
            temp_path = f.name

        try:
            config = self.loader.load_from_file(temp_path, merge_env=False)
            assert isinstance(config, FlexiAIConfig)
            assert len(config.providers) == 1
            assert config.default_temperature == 0.7
        finally:
            Path(temp_path).unlink()

    def test_load_from_nonexistent_file(self) -> None:
        """Test that loading from nonexistent file raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_file("/nonexistent/config.json", merge_env=False)

        assert "Configuration file not found" in str(exc_info.value)

    def test_load_from_directory(self) -> None:
        """Test that loading from directory raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ConfigurationError) as exc_info:
                self.loader.load_from_file(temp_dir, merge_env=False)

            assert "Configuration path is not a file" in str(exc_info.value)

    def test_load_from_invalid_json(self) -> None:
        """Test that loading from invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                self.loader.load_from_file(temp_path, merge_env=False)

            assert "Invalid JSON in configuration file" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_load_from_non_object_json(self) -> None:
        """Test that loading from JSON array raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([1, 2, 3], f)
            temp_path = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                self.loader.load_from_file(temp_path, merge_env=False)

            assert "Configuration file must contain a JSON object" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()


class TestConfigLoaderFromEnv:
    """Tests for loading configuration from environment variables."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.loader.reset()
        # Clear any existing FLEXIAI_ environment variables
        for key in list(os.environ.keys()):
            if key.startswith("FLEXIAI_"):
                del os.environ[key]

    def teardown_method(self) -> None:
        """Clean up environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("FLEXIAI_"):
                del os.environ[key]

    def test_load_from_env_single_provider(self) -> None:
        """Test loading configuration from environment variables."""
        os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
        os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-test"
        os.environ["FLEXIAI_PROVIDER_0_MODEL"] = "gpt-4"
        os.environ["FLEXIAI_PROVIDER_0_PRIORITY"] = "1"
        os.environ["FLEXIAI_DEFAULT_TEMPERATURE"] = "0.8"

        config = self.loader.load_from_env()

        assert len(config.providers) == 1
        assert config.providers[0].name == "openai"
        assert config.providers[0].api_key == "sk-test"
        assert config.providers[0].model == "gpt-4"
        assert config.providers[0].priority == 1
        assert config.default_temperature == 0.8

    def test_load_from_env_multiple_providers(self) -> None:
        """Test loading multiple providers from environment."""
        os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
        os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-test-1"
        os.environ["FLEXIAI_PROVIDER_0_MODEL"] = "gpt-4"
        os.environ["FLEXIAI_PROVIDER_0_PRIORITY"] = "1"

        os.environ["FLEXIAI_PROVIDER_1_NAME"] = "anthropic"
        os.environ["FLEXIAI_PROVIDER_1_API_KEY"] = "sk-test-2"
        os.environ["FLEXIAI_PROVIDER_1_MODEL"] = "claude-3-opus-20240229"
        os.environ["FLEXIAI_PROVIDER_1_PRIORITY"] = "2"

        config = self.loader.load_from_env()

        assert len(config.providers) == 2
        assert config.providers[0].name == "openai"
        assert config.providers[0].priority == 1
        assert config.providers[1].name == "anthropic"
        assert config.providers[1].priority == 2

    def test_load_from_env_no_variables(self) -> None:
        """Test that loading with no env vars raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_env()

        assert "No FLEXIAI_ environment variables found" in str(exc_info.value)

    def test_load_from_env_invalid_temperature(self) -> None:
        """Test that invalid temperature value raises error."""
        os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
        os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-test"
        os.environ["FLEXIAI_PROVIDER_0_MODEL"] = "gpt-4"
        os.environ["FLEXIAI_PROVIDER_0_PRIORITY"] = "1"
        os.environ["FLEXIAI_DEFAULT_TEMPERATURE"] = "not-a-number"

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_env()

        assert "must be a float" in str(exc_info.value)

    def test_load_from_env_invalid_max_tokens(self) -> None:
        """Test that invalid max_tokens value raises error."""
        os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
        os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-test"
        os.environ["FLEXIAI_PROVIDER_0_MODEL"] = "gpt-4"
        os.environ["FLEXIAI_PROVIDER_0_PRIORITY"] = "1"
        os.environ["FLEXIAI_DEFAULT_MAX_TOKENS"] = "not-a-number"

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_env()

        assert "must be an integer" in str(exc_info.value)

    def test_load_from_env_invalid_priority(self) -> None:
        """Test that invalid priority value raises error."""
        os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
        os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-test"
        os.environ["FLEXIAI_PROVIDER_0_MODEL"] = "gpt-4"
        os.environ["FLEXIAI_PROVIDER_0_PRIORITY"] = "not-a-number"

        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.load_from_env()

        assert "must be an integer" in str(exc_info.value)


class TestConfigLoaderMerging:
    """Tests for configuration merging."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.loader.reset()
        # Clear any existing FLEXIAI_ environment variables
        for key in list(os.environ.keys()):
            if key.startswith("FLEXIAI_"):
                del os.environ[key]

    def teardown_method(self) -> None:
        """Clean up environment variables."""
        for key in list(os.environ.keys()):
            if key.startswith("FLEXIAI_"):
                del os.environ[key]

    def test_merge_dict_with_env(self) -> None:
        """Test merging dict config with environment variables."""
        config_dict = {
            "providers": [
                {"name": "openai", "priority": 1, "api_key": "sk-test", "model": "gpt-4"}
            ],
            "default_temperature": 0.7,
        }

        os.environ["FLEXIAI_DEFAULT_TEMPERATURE"] = "0.9"
        os.environ["FLEXIAI_DEFAULT_MAX_TOKENS"] = "1500"

        config = self.loader.load_from_dict(config_dict, merge_env=True)

        # Environment variables should override dict values
        assert config.default_temperature == 0.9
        assert config.default_max_tokens == 1500

    def test_merge_dict_without_env(self) -> None:
        """Test loading dict without merging environment."""
        config_dict = {
            "providers": [
                {"name": "openai", "priority": 1, "api_key": "sk-test", "model": "gpt-4"}
            ],
            "default_temperature": 0.7,
        }

        os.environ["FLEXIAI_DEFAULT_TEMPERATURE"] = "0.9"

        config = self.loader.load_from_dict(config_dict, merge_env=False)

        # Should use dict value, not env value
        assert config.default_temperature == 0.7


class TestConfigLoaderExport:
    """Tests for exporting configuration."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.loader = ConfigLoader()
        self.loader.reset()

    def test_export_to_dict(self) -> None:
        """Test exporting configuration to dictionary."""
        config_dict = {
            "providers": [
                {"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}
            ],
            "default_temperature": 0.8,
        }
        self.loader.load_from_dict(config_dict, merge_env=False)

        exported = self.loader.export_to_dict()

        assert isinstance(exported, dict)
        assert "providers" in exported
        assert exported["default_temperature"] == 0.8

    def test_export_to_dict_without_config(self) -> None:
        """Test that exporting without loaded config raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            self.loader.export_to_dict()

        assert "No configuration loaded" in str(exc_info.value)

    def test_export_to_json(self) -> None:
        """Test exporting configuration to JSON file."""
        config_dict = {
            "providers": [{"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}]
        }
        self.loader.load_from_dict(config_dict, merge_env=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"
            self.loader.export_to_json(output_path)

            assert output_path.exists()

            with open(output_path, "r") as f:
                loaded = json.load(f)

            assert "providers" in loaded

    def test_export_to_json_creates_directories(self) -> None:
        """Test that export creates parent directories."""
        config_dict = {
            "providers": [{"name": "openai", "api_key": "sk-test", "model": "gpt-4", "priority": 1}]
        }
        self.loader.load_from_dict(config_dict, merge_env=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "output.json"
            self.loader.export_to_json(output_path)

            assert output_path.exists()

    def test_export_to_json_without_config(self) -> None:
        """Test that exporting without loaded config raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"

            with pytest.raises(ConfigurationError) as exc_info:
                self.loader.export_to_json(output_path)

            assert "No configuration loaded" in str(exc_info.value)
