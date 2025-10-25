# Example FlexiAI Configuration File

This directory contains example configuration files for FlexiAI.

## config.json

A complete example configuration file showing all available options.

### Configuration Structure

```json
{
  "providers": [
    {
      "name": "openai",          // Provider name: openai, gemini, anthropic, azure, bedrock
      "priority": 1,             // Priority for failover (1=highest)
      "api_key": "sk-...",       // API key for authentication
      "model": "gpt-4",          // Model name to use
      "timeout": 30,             // Request timeout in seconds (optional)
      "max_retries": 3,          // Maximum retry attempts (optional)
      "base_url": null,          // Custom API endpoint (optional)
      "config": {}               // Provider-specific config (optional)
    }
  ],
  "circuit_breaker": {           // Circuit breaker configuration (optional)
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "half_open_max_calls": 3
  },
  "retry": {                     // Retry configuration (optional)
    "max_attempts": 3,
    "backoff_factor": 2.0,
    "max_backoff": 60
  },
  "logging": {                   // Logging configuration (optional)
    "enabled": true,
    "level": "INFO"
  },
  "default_temperature": 0.7,    // Default temperature (optional)
  "default_max_tokens": 2000     // Default max tokens (optional)
}
```

## Loading Configuration

### From Dictionary

```python
from flexiai.config import ConfigLoader

config_loader = ConfigLoader()
config = config_loader.load_from_dict({
    "providers": [
        {
            "name": "openai",
            "priority": 1,
            "api_key": "sk-...",
            "model": "gpt-4"
        }
    ]
})
```

### From JSON File

```python
from flexiai.config import ConfigLoader

config_loader = ConfigLoader()
config = config_loader.load_from_file("docs/examples/config.json")
```

### From Environment Variables

Set environment variables with `FLEXIAI_` prefix:

```bash
export FLEXIAI_PROVIDER_0_NAME=openai
export FLEXIAI_PROVIDER_0_API_KEY=sk-...
export FLEXIAI_PROVIDER_0_MODEL=gpt-4
export FLEXIAI_PROVIDER_0_PRIORITY=1
export FLEXIAI_DEFAULT_TEMPERATURE=0.8
```

Then load:

```python
from flexiai.config import ConfigLoader

config_loader = ConfigLoader()
config = config_loader.load_from_env()
```

## Exporting Configuration

### To Dictionary

```python
config_dict = config_loader.export_to_dict()
```

### To JSON File

```python
config_loader.export_to_json("my_config.json")
```

## Configuration Merging

By default, environment variables override configuration from dictionaries or files:

```python
# This will merge environment variables with the dict
config = config_loader.load_from_dict(config_dict, merge_env=True)

# This will NOT merge environment variables
config = config_loader.load_from_dict(config_dict, merge_env=False)
```

## Provider Priority

Providers are automatically sorted by priority (1 = highest). During failover, FlexiAI will try providers in priority order.

## Notes

- At least one provider must be configured
- API keys are required for all providers
- Model names must be valid for the respective provider
- Timeout and retry settings have sensible defaults if not specified
