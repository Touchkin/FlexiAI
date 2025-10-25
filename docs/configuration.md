# Configuration Guide

Complete guide to configuring FlexiAI for different use cases.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [Provider Configuration](#provider-configuration)
- [Circuit Breaker Configuration](#circuit-breaker-configuration)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Common Patterns](#common-patterns)
- [Best Practices](#best-practices)

## Basic Configuration

### Minimal Configuration

```python
from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-...",
            model="gpt-4-turbo-preview"
        )
    ]
)

client = FlexiAI(config=config)
```

### Complete Configuration

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-...",
            model="gpt-4-turbo-preview",
            base_url=None,
            timeout=30,
            max_retries=3,
            config={}
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception_types=["ProviderException", "RateLimitError"]
    ),
    default_timeout=30,
    enable_logging=True,
    log_level="INFO"
)
```

## Provider Configuration

### Single Provider

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview"
        )
    ]
)
```

### Multiple Providers with Failover

```python
config = FlexiAIConfig(
    providers=[
        # Primary: OpenAI GPT-4
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview",
            timeout=30
        ),
        # Backup: OpenAI GPT-3.5
        ProviderConfig(
            name="openai",
            priority=2,
            api_key=os.getenv("OPENAI_BACKUP_KEY"),
            model="gpt-3.5-turbo",
            timeout=20
        )
    ]
)
```

### Provider-Specific Configuration

```python
# OpenAI with organization
ProviderConfig(
    name="openai",
    priority=1,
    api_key="sk-...",
    model="gpt-4-turbo",
    config={
        "organization": "org-123456"
    }
)

# Custom base URL (for proxies or Azure)
ProviderConfig(
    name="openai",
    priority=1,
    api_key="sk-...",
    model="gpt-4",
    base_url="https://custom-proxy.example.com/v1"
)
```

## Circuit Breaker Configuration

### Default Circuit Breaker

```python
config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig()  # Use defaults
)
```

### Custom Circuit Breaker

```python
config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,      # Open after 3 failures
        recovery_timeout=30,      # Try recovery after 30s
        expected_exception_types=[
            "ProviderException",
            "RateLimitError",
            "AuthenticationError"
        ]
    )
)
```

### Aggressive Circuit Breaker (Fail Fast)

```python
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=2,      # Very sensitive
    recovery_timeout=120      # Longer recovery period
)
```

### Lenient Circuit Breaker

```python
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=10,     # More tolerant
    recovery_timeout=30       # Quick recovery attempts
)
```

## Environment Variables

### Using Environment Variables

```python
import os
from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        )
    ]
)
```

### Environment Variable Naming Convention

```bash
# Provider configuration
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4-turbo-preview"
export OPENAI_TIMEOUT="30"
export OPENAI_MAX_RETRIES="3"

# Backup provider
export OPENAI_BACKUP_API_KEY="sk-backup..."
export OPENAI_BACKUP_MODEL="gpt-3.5-turbo"

# Circuit breaker
export CIRCUIT_BREAKER_THRESHOLD="5"
export CIRCUIT_BREAKER_RECOVERY_TIMEOUT="60"

# Logging
export FLEXIAI_LOG_LEVEL="INFO"
export FLEXIAI_ENABLE_LOGGING="true"
```

## Configuration Files

### JSON Configuration

**config.json**:
```json
{
  "providers": [
    {
      "name": "openai",
      "priority": 1,
      "api_key": "sk-...",
      "model": "gpt-4-turbo-preview",
      "timeout": 30,
      "max_retries": 3
    }
  ],
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60
  },
  "default_timeout": 30,
  "enable_logging": true,
  "log_level": "INFO"
}
```

**Loading**:
```python
import json
from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig

with open("config.json") as f:
    config_dict = json.load(f)

# Convert to FlexiAIConfig
config = FlexiAIConfig(
    providers=[ProviderConfig(**p) for p in config_dict["providers"]],
    circuit_breaker=CircuitBreakerConfig(**config_dict.get("circuit_breaker", {})),
    default_timeout=config_dict.get("default_timeout", 30),
    enable_logging=config_dict.get("enable_logging", True),
    log_level=config_dict.get("log_level", "INFO")
)

client = FlexiAI(config=config)
```

### YAML Configuration

**config.yaml**:
```yaml
providers:
  - name: openai
    priority: 1
    api_key: ${OPENAI_API_KEY}
    model: gpt-4-turbo-preview
    timeout: 30
    max_retries: 3

circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 60

default_timeout: 30
enable_logging: true
log_level: INFO
```

**Loading**:
```python
import yaml
import os
from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig, CircuitBreakerConfig

with open("config.yaml") as f:
    config_dict = yaml.safe_load(f)

# Substitute environment variables
def substitute_env_vars(d):
    if isinstance(d, dict):
        return {k: substitute_env_vars(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [substitute_env_vars(item) for item in d]
    elif isinstance(d, str) and d.startswith("${") and d.endswith("}"):
        return os.getenv(d[2:-1])
    return d

config_dict = substitute_env_vars(config_dict)

# Create config
config = FlexiAIConfig(
    providers=[ProviderConfig(**p) for p in config_dict["providers"]],
    circuit_breaker=CircuitBreakerConfig(**config_dict.get("circuit_breaker", {}))
)

client = FlexiAI(config=config)
```

## Common Patterns

### Development vs Production

**Development**:
```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-dev...",
            model="gpt-3.5-turbo",  # Cheaper for testing
            timeout=60,
            max_retries=5
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=10,  # More lenient
        recovery_timeout=30
    ),
    log_level="DEBUG"  # Verbose logging
)
```

**Production**:
```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo-preview",
            timeout=30,
            max_retries=3
        ),
        # Backup provider
        ProviderConfig(
            name="openai",
            priority=2,
            api_key=os.getenv("OPENAI_BACKUP_KEY"),
            model="gpt-3.5-turbo",
            timeout=20
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60
    ),
    log_level="INFO"  # Production logging
)
```

### Cost-Optimized Configuration

```python
config = FlexiAIConfig(
    providers=[
        # Try cheaper model first
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            timeout=20
        ),
        # Fallback to more expensive if needed
        ProviderConfig(
            name="openai",
            priority=2,
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4-turbo",
            timeout=30
        )
    ]
)
```

### High-Availability Configuration

```python
config = FlexiAIConfig(
    providers=[
        # Primary datacenter
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_PRIMARY_KEY"),
            model="gpt-4-turbo",
            base_url="https://primary.openai.com/v1",
            timeout=30
        ),
        # Secondary datacenter
        ProviderConfig(
            name="openai",
            priority=2,
            api_key=os.getenv("OPENAI_SECONDARY_KEY"),
            model="gpt-4-turbo",
            base_url="https://secondary.openai.com/v1",
            timeout=30
        ),
        # Tertiary backup
        ProviderConfig(
            name="openai",
            priority=3,
            api_key=os.getenv("OPENAI_BACKUP_KEY"),
            model="gpt-3.5-turbo",
            timeout=20
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,  # Quick failover
        recovery_timeout=120  # Longer recovery
    )
)
```

## Best Practices

### 1. Use Environment Variables for Secrets

**❌ Bad**:
```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key="sk-hardcoded123...",  # DON'T DO THIS
            model="gpt-4"
        )
    ]
)
```

**✅ Good**:
```python
import os

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key=os.getenv("OPENAI_API_KEY"),  # Use env vars
            model="gpt-4"
        )
    ]
)
```

### 2. Configure Backup Providers

**❌ Single Point of Failure**:
```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", priority=1, api_key="...", model="gpt-4")
    ]
)
```

**✅ High Availability**:
```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", priority=1, api_key=primary_key, model="gpt-4"),
        ProviderConfig(name="openai", priority=2, api_key=backup_key, model="gpt-3.5-turbo")
    ]
)
```

### 3. Set Appropriate Timeouts

**❌ Too Long**:
```python
ProviderConfig(name="openai", priority=1, api_key="...", model="gpt-4", timeout=300)
```

**✅ Reasonable**:
```python
ProviderConfig(name="openai", priority=1, api_key="...", model="gpt-4", timeout=30)
```

### 4. Configure Circuit Breaker

**❌ No Circuit Breaker**:
```python
config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=None  # Missing protection
)
```

**✅ With Circuit Breaker**:
```python
config = FlexiAIConfig(
    providers=[...],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60
    )
)
```

### 5. Enable Logging in Production

```python
config = FlexiAIConfig(
    providers=[...],
    enable_logging=True,
    log_level="INFO"  # Not DEBUG in production
)
```

### 6. Validate Configuration Early

```python
from pydantic import ValidationError

try:
    config = FlexiAIConfig(
        providers=[ProviderConfig(...)]
    )
    client = FlexiAI(config=config)
except ValidationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
```

### 7. Use Different Models for Different Tasks

```python
# For chat/general tasks
chat_config = FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", priority=1, api_key="...", model="gpt-4-turbo")
    ]
)

# For code generation
code_config = FlexiAIConfig(
    providers=[
        ProviderConfig(name="openai", priority=1, api_key="...", model="gpt-4")
    ]
)
```

---

**Last Updated**: October 25, 2025
**Version**: 1.0 (Phase 1 Complete)
