"""
Configuration management for FlexiAI.

This module provides the ConfigLoader class for loading and managing
configuration from multiple sources: dictionaries, JSON files, and
environment variables.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from flexiai.exceptions import ConfigurationError
from flexiai.models import FlexiAIConfig


class ConfigLoader:
    """
    Singleton configuration loader for FlexiAI.

    Supports loading configuration from:
    - Python dictionaries
    - JSON files
    - Environment variables (with FLEXIAI_ prefix)

    Configuration sources are merged with the following priority (highest to lowest):
    1. Environment variables
    2. User-provided config (dict or file)
    3. Default values

    Example:
        >>> loader = ConfigLoader()
        >>> config = loader.load_from_dict({
        ...     "providers": [
        ...         {"name": "openai", "api_key": "sk-..."}
        ...     ]
        ... })
        >>> # Load from file
        >>> config = loader.load_from_file("config.json")
        >>> # Load from environment
        >>> config = loader.load_from_env()
    """

    _instance: Optional["ConfigLoader"] = None

    def __new__(cls) -> "ConfigLoader":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ConfigLoader."""
        # Only initialize once
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._current_config: Optional[FlexiAIConfig] = None

    @property
    def current_config(self) -> Optional[FlexiAIConfig]:
        """Get the current loaded configuration."""
        return self._current_config

    def load_from_dict(self, config_dict: Dict[str, Any], merge_env: bool = True) -> FlexiAIConfig:
        """
        Load configuration from a Python dictionary.

        Args:
            config_dict: Configuration dictionary
            merge_env: Whether to merge environment variables (default: True)

        Returns:
            Validated FlexiAIConfig instance

        Raises:
            ConfigurationError: If configuration is invalid

        Example:
            >>> loader = ConfigLoader()
            >>> config = loader.load_from_dict({
            ...     "providers": [
            ...         {
            ...             "name": "openai",
            ...             "api_key": "sk-...",
            ...             "models": ["gpt-4", "gpt-3.5-turbo"]
            ...         }
            ...     ],
            ...     "default_temperature": 0.8
            ... })
        """
        try:
            # Merge with environment variables if requested
            if merge_env:
                env_dict = self._load_env_vars()
                config_dict = self._merge_configs(config_dict, env_dict)

            # Validate and create config using Pydantic
            self._current_config = FlexiAIConfig(**config_dict)
            return self._current_config

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from dict: {str(e)}",
                details={"config_dict": config_dict, "error": str(e)},
            ) from e

    def load_from_file(self, file_path: Union[str, Path], merge_env: bool = True) -> FlexiAIConfig:
        """
        Load configuration from a JSON file.

        Args:
            file_path: Path to JSON configuration file
            merge_env: Whether to merge environment variables (default: True)

        Returns:
            Validated FlexiAIConfig instance

        Raises:
            ConfigurationError: If file doesn't exist or is invalid

        Example:
            >>> loader = ConfigLoader()
            >>> config = loader.load_from_file("config.json")
        """
        path = Path(file_path)

        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {file_path}",
                details={"file_path": str(file_path)},
            )

        if not path.is_file():
            raise ConfigurationError(
                f"Configuration path is not a file: {file_path}",
                details={"file_path": str(file_path)},
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)

            if not isinstance(config_dict, dict):
                raise ConfigurationError(
                    "Configuration file must contain a JSON object",
                    details={"file_path": str(file_path), "type": type(config_dict).__name__},
                )

            return self.load_from_dict(config_dict, merge_env=merge_env)

        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file: {str(e)}",
                details={"file_path": str(file_path), "error": str(e)},
            ) from e
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from file: {str(e)}",
                details={"file_path": str(file_path), "error": str(e)},
            ) from e

    def load_from_env(self) -> FlexiAIConfig:
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with FLEXIAI_.
        Nested keys use double underscores (__).

        Supported environment variables:
            - FLEXIAI_DEFAULT_TEMPERATURE: Default temperature (float)
            - FLEXIAI_DEFAULT_MAX_TOKENS: Default max tokens (int)
            - FLEXIAI_PROVIDER_{N}_NAME: Provider name (str)
            - FLEXIAI_PROVIDER_{N}_API_KEY: Provider API key (str)
            - FLEXIAI_PROVIDER_{N}_MODEL: Model name (str)
            - FLEXIAI_PROVIDER_{N}_PRIORITY: Provider priority (int)

        Returns:
            Validated FlexiAIConfig instance

        Raises:
            ConfigurationError: If environment configuration is invalid

        Example:
            >>> # Set environment variables
            >>> os.environ["FLEXIAI_PROVIDER_0_NAME"] = "openai"
            >>> os.environ["FLEXIAI_PROVIDER_0_API_KEY"] = "sk-..."
            >>> # Load config
            >>> loader = ConfigLoader()
            >>> config = loader.load_from_env()
        """
        env_dict = self._load_env_vars()

        if not env_dict:
            raise ConfigurationError(
                "No FLEXIAI_ environment variables found",
                details={"prefix": "FLEXIAI_"},
            )

        return self.load_from_dict(env_dict, merge_env=False)

    def export_to_dict(self) -> Dict[str, Any]:
        """
        Export current configuration to a dictionary.

        Returns:
            Dictionary representation of current configuration

        Raises:
            ConfigurationError: If no configuration is loaded

        Example:
            >>> loader = ConfigLoader()
            >>> config = loader.load_from_dict({...})
            >>> config_dict = loader.export_to_dict()
        """
        if self._current_config is None:
            raise ConfigurationError(
                "No configuration loaded. Call load_from_dict(), "
                "load_from_file(), or load_from_env() first."
            )

        return self._current_config.model_dump(mode="python", exclude_none=True)

    def export_to_json(self, file_path: Union[str, Path], indent: int = 2) -> None:
        """
        Export current configuration to a JSON file.

        Args:
            file_path: Path where JSON file should be written
            indent: JSON indentation level (default: 2)

        Raises:
            ConfigurationError: If no configuration is loaded or file cannot be written

        Example:
            >>> loader = ConfigLoader()
            >>> config = loader.load_from_dict({...})
            >>> loader.export_to_json("my_config.json")
        """
        config_dict = self.export_to_dict()

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=indent)

        except Exception as e:
            raise ConfigurationError(
                f"Failed to export configuration to JSON: {str(e)}",
                details={"file_path": str(file_path), "error": str(e)},
            ) from e

    def _load_env_vars(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Dictionary with configuration from environment variables
        """
        config: Dict[str, Any] = {}
        prefix = "FLEXIAI_"

        # Load simple config values
        if temp := os.getenv(f"{prefix}DEFAULT_TEMPERATURE"):
            try:
                config["default_temperature"] = float(temp)
            except ValueError:
                raise ConfigurationError(
                    f"Invalid value for {prefix}DEFAULT_TEMPERATURE: must be a float",
                    details={"value": temp},
                )

        if tokens := os.getenv(f"{prefix}DEFAULT_MAX_TOKENS"):
            try:
                config["default_max_tokens"] = int(tokens)
            except ValueError:
                raise ConfigurationError(
                    f"Invalid value for {prefix}DEFAULT_MAX_TOKENS: must be an integer",
                    details={"value": tokens},
                )

        # Load provider configurations
        providers = self._load_providers_from_env(prefix)
        if providers:
            config["providers"] = providers

        return config

    def _load_providers_from_env(self, prefix: str) -> list[Dict[str, Any]]:
        """
        Load provider configurations from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., "FLEXIAI_")

        Returns:
            List of provider configuration dictionaries
        """
        providers: Dict[int, Dict[str, Any]] = {}

        # Find all FLEXIAI_PROVIDER_* environment variables
        for key, value in os.environ.items():
            if not key.startswith(f"{prefix}PROVIDER_"):
                continue

            # Parse key: FLEXIAI_PROVIDER_{INDEX}_{FIELD}
            parts = key[len(prefix) :].split("_", 2)  # ['PROVIDER', 'INDEX', 'FIELD']
            if len(parts) < 3 or parts[0] != "PROVIDER":
                continue

            try:
                index = int(parts[1])
                field = parts[2].lower()
            except (ValueError, IndexError):
                continue

            # Initialize provider dict if needed
            if index not in providers:
                providers[index] = {}

            # Set field value
            if field == "priority":
                try:
                    providers[index]["priority"] = int(value)
                except ValueError:
                    raise ConfigurationError(
                        f"Invalid value for {key}: must be an integer",
                        details={"key": key, "value": value},
                    )
            else:
                providers[index][field] = value

        # Convert to sorted list
        return [providers[i] for i in sorted(providers.keys())]

    def _merge_configs(
        self, base_config: Dict[str, Any], override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.

        Override values take precedence over base values.

        Args:
            base_config: Base configuration dictionary
            override_config: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                merged[key] = self._merge_configs(merged[key], value)
            else:
                # Override value
                merged[key] = value

        return merged

    def reset(self) -> None:
        """
        Reset the configuration loader.

        Clears the current configuration.

        Example:
            >>> loader = ConfigLoader()
            >>> loader.load_from_dict({...})
            >>> loader.reset()
            >>> loader.current_config  # None
        """
        self._current_config = None
