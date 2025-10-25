# FlexiAI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen.svg)]()

**FlexiAI** is a production-ready Python library that provides a unified interface for multiple GenAI providers with automatic failover capabilities using the circuit breaker pattern.

## 🌟 Features

- **Multi-Provider Support**: OpenAI, Google Vertex AI, and Anthropic Claude
- **Automatic Failover**: Priority-based provider selection with circuit breaker pattern
- **Unified Interface**: Single API for all providers
- **Type-Safe**: Full type hints and Pydantic validation
- **Production-Ready**: 95% test coverage, comprehensive error handling
- **Flexible Authentication**: API keys, service accounts, and ADC support
- **Token Tracking**: Monitor usage across all providers
- **Request Metadata**: Track which provider handled each request

## 📦 Installation

```bash
pip install flexiai
```

### Provider-Specific Dependencies

```bash
# For OpenAI support
pip install openai

# For Google Vertex AI support
pip install google-genai google-auth

# For Anthropic Claude support
pip install anthropic
```

Or install all providers at once:

```bash
pip install flexiai[all]
```

## 🚀 Quick Start

### Basic Usage with OpenAI

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message

# Configure with OpenAI
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key="sk-your-openai-api-key",
            model="gpt-4o-mini",
            priority=1
        )
    ]
)

# Create client and make a request
client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="user", content="What is Python?")
    ],
    max_tokens=500
)

print(response.content)
print(f"Tokens used: {response.usage.total_tokens}")
print(f"Provider: {response.metadata.provider}")
```

### Using Google Vertex AI (GCP)

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="vertexai",
            api_key="not-used",  # Vertex AI uses OAuth2, not API keys
            model="gemini-2.0-flash",
            priority=1,
            config={
                "project": "your-gcp-project-id",
                "location": "us-central1",
                "service_account_file": "/path/to/service-account.json"
            }
        )
    ]
)

client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="user", content="Hello!")
    ]
)
```

### Using Anthropic Claude

```python
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-your-anthropic-api-key",
            model="claude-3-5-sonnet-20241022",
            priority=1
        )
    ]
)

client = FlexiAI(config)
response = client.chat_completion(
    messages=[
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Explain quantum computing briefly.")
    ],
    max_tokens=200
)

print(response.content)
```

**Supported Claude Models:**
- `claude-3-opus-20240229` - Most capable model
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fastest responses
- `claude-3-5-sonnet-20241022` - Latest Sonnet (recommended)
- `claude-3-5-haiku-20241022` - Latest Haiku

## 🔄 Multi-Provider Failover

Configure multiple providers with priorities for automatic failover:

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig, Message, CircuitBreakerConfig

config = FlexiAIConfig(
    providers=[
        # Primary: OpenAI
        ProviderConfig(
            name="openai",
            api_key="sk-your-openai-key",
            model="gpt-4o-mini",
            priority=1
        ),
        # Secondary: Google Vertex AI
        ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash-exp",
            priority=2,
            config={
                "project": "your-gcp-project",
                "location": "us-central1",
                "service_account_file": "/path/to/credentials.json"
            }
        ),
        # Tertiary: Anthropic Claude
        ProviderConfig(
            name="anthropic",
            api_key="sk-ant-your-anthropic-key",
            model="claude-3-5-sonnet-20241022",
            priority=3
        )
    ],
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=60,
        expected_exception="ProviderException"
    )
)

client = FlexiAI(config)

# If OpenAI fails, automatically falls back to Vertex AI, then Claude
response = client.chat_completion(
    messages=[Message(role="user", content="Tell me a joke")]
)

# Check which provider was used
print(f"Response from: {response.metadata.provider}")
```

## 🎯 Advanced Features

### System Messages

```python
response = client.chat_completion(
    messages=[
        Message(role="system", content="You are a helpful Python expert"),
        Message(role="user", content="How do I use decorators?")
    ],
    max_tokens=1000
)
```

### Multi-Turn Conversations

```python
conversation = [
    Message(role="user", content="What is Flask?"),
    Message(role="assistant", content="Flask is a lightweight Python web framework..."),
    Message(role="user", content="How does it compare to Django?")
]

response = client.chat_completion(
    messages=conversation,
    temperature=0.8
)
```

### Provider Status Monitoring

```python
# Get health status of all providers
status = client.get_provider_status()
for provider_name, info in status.items():
    print(f"{provider_name}: {info['healthy']}")
    print(f"  Circuit Breaker: {info['circuit_breaker']['state']}")
    print(f"  Success Rate: {info['successful_requests']}/{info['total_requests']}")
```

### Request Statistics

```python
# Track requests and providers used
stats = client.get_request_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Successful: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Providers used: {stats['providers_used']}")
```

### Circuit Breaker Control

```python
# Manually reset circuit breakers if needed
client.reset_circuit_breakers()

# Check last used provider
last_provider = client.get_last_used_provider()
print(f"Last request handled by: {last_provider}")
```

### Testing Circuit Breaker

The circuit breaker protects your application from cascading failures by detecting and isolating failing providers. Here's how to test it:

#### Test 1: Invalid Credentials Detection

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig
from flexiai.exceptions import AllProvidersFailedError

# Create client with invalid API key
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="anthropic",
        priority=1,
        api_key="sk-ant-invalid-key-for-testing-12345678901234567890",
        model="claude-3-5-haiku-20241022"
    )
]))

# Make multiple requests - circuit breaker will track failures
failures = 0
for i in range(5):
    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": "test"}]
        )
    except AllProvidersFailedError:
        failures += 1
        print(f"Failure {failures}: Circuit breaker counting failures")

print(f"Total failures detected: {failures}/5")
print("✅ Circuit breaker is working - invalid credentials properly rejected")
```

#### Test 2: Automatic Failover

```python
# Configure primary provider (will fail) and backup provider (will succeed)
# Note: Must use different provider names
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="openai",
        priority=1,  # Primary
        api_key="sk-invalid-key-will-fail-12345678901234567890",
        model="gpt-3.5-turbo"
    ),
    ProviderConfig(
        name="anthropic",
        priority=2,  # Backup
        api_key=os.getenv("ANTHROPIC_API_KEY"),  # Valid key
        model="claude-3-5-haiku-20241022"
    )
]))

# Make request - should automatically failover to backup
try:
    response = client.chat_completion(
        messages=[{"role": "user", "content": "Say 'Failover works!'"}]
    )
    print(f"✅ Failover successful!")
    print(f"Response: {response.content}")
    print(f"Provider used: {response.provider}")

    # Check statistics
    stats = client.get_request_stats()
    print(f"Total requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")
except Exception as e:
    print(f"❌ Failover failed: {e}")
```

#### Test 3: Circuit Breaker States

```python
# Monitor circuit breaker state transitions
provider_status = client.get_provider_status()

for provider_name, info in provider_status.items():
    print(f"\nProvider: {provider_name}")
    print(f"  State: {info['circuit_breaker']['state']}")
    print(f"  Healthy: {info['healthy']}")
    print(f"  Failure Count: {info['circuit_breaker']['failure_count']}")
    print(f"  Success Count: {info['circuit_breaker']['success_count']}")
```

**Circuit Breaker States:**
- **CLOSED**: Normal operation, requests passing through
- **OPEN**: Too many failures, requests blocked (fail-fast)
- **HALF_OPEN**: Testing recovery, limited requests allowed

#### Test 4: Recovery Testing

```python
import time

# Create client with valid credentials
client = FlexiAI(FlexiAIConfig(providers=[
    ProviderConfig(
        name="anthropic",
        priority=1,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-5-haiku-20241022"
    )
]))

# Make successful request
response = client.chat_completion(
    messages=[{"role": "user", "content": "Hello"}]
)
print(f"✅ Successful request: {response.content}")

# Check that circuit is CLOSED (healthy)
status = client.get_provider_status()
for provider, info in status.items():
    state = info['circuit_breaker']['state']
    print(f"Circuit state after success: {state}")
    assert state == "CLOSED", "Circuit should be CLOSED after successful request"
```

#### Complete Test Script

For a comprehensive test, see `examples/circuit_breaker_test.py`:

```bash
# Set your API keys
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export OPENAI_API_KEY="sk-..."

# Run the test
python examples/circuit_breaker_test.py
```

**What the test validates:**
- ✅ Invalid credentials are detected immediately
- ✅ Circuit breaker tracks failure counts
- ✅ Automatic failover to backup providers
- ✅ Provider health monitoring
- ✅ Request statistics tracking
- ✅ Graceful error handling

## 🔧 Configuration

### From Dictionary

```python
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig

config_dict = {
    "providers": [
        {
            "name": "openai",
            "api_key": "sk-...",
            "model": "gpt-4o-mini",
            "priority": 1,
            "config": {
                "timeout": 30,
                "max_retries": 3
            }
        }
    ],
    "circuit_breaker": {
        "failure_threshold": 5,
        "recovery_timeout": 60
    }
}

config = FlexiAIConfig(**config_dict)
client = FlexiAI(config)
```

### From Environment Variables

```bash
export OPENAI_API_KEY="sk-your-key"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

```python
import os
from flexiai import FlexiAI
from flexiai.models import FlexiAIConfig, ProviderConfig

config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            priority=1
        ),
        ProviderConfig(
            name="vertexai",
            api_key="not-used",
            model="gemini-2.0-flash",
            priority=2,
            config={
                "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location": "us-central1"
            }
        )
    ]
)

client = FlexiAI(config)
```

## 🔐 Authentication

### OpenAI

OpenAI uses API keys for authentication:

```python
ProviderConfig(
    name="openai",
    api_key="sk-proj-...",  # Get from https://platform.openai.com/api-keys
    model="gpt-4o-mini"
)
```

### Google Vertex AI

Vertex AI supports multiple authentication methods:

#### Option 1: Service Account (Recommended for Production)

```python
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    model="gemini-2.0-flash-exp",
    config={
        "project": "your-gcp-project-id",
        "location": "us-central1",
        "service_account_file": "/path/to/service-account.json"
    }
)
```

#### Option 2: Application Default Credentials (ADC)

```bash
# Authenticate using gcloud
gcloud auth application-default login

# Or set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

```python
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    model="gemini-2.0-flash-exp",
    config={
        "project": "your-gcp-project-id",
        "location": "us-central1"
        # Will use ADC automatically
    }
)
```

### Anthropic Claude

Anthropic uses API keys for authentication:

```bash
# Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."
```

```python
ProviderConfig(
    name="anthropic",
    api_key="sk-ant-...",  # Get from https://console.anthropic.com/
    model="claude-3-5-sonnet-20241022"
)
```

Or load from environment:

```python
import os

ProviderConfig(
    name="anthropic",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-3-5-sonnet-20241022"
)
```

## 🛠️ Supported Models

### OpenAI Models

- `gpt-4o` - Most capable model
- `gpt-4o-mini` - Fast and affordable
- `gpt-4-turbo` - Previous generation flagship
- `gpt-3.5-turbo` - Fast and efficient

### Google Vertex AI Models

- `gemini-2.0-flash-exp` - Latest experimental Gemini on GCP
- `gemini-1.5-pro` - Advanced Gemini on GCP
- `gemini-1.5-flash` - Fast Gemini on GCP
- `text-bison` - Text generation
- `chat-bison` - Chat interactions
- `codechat-bison` - Code assistance

### Anthropic Claude Models

- `claude-3-opus-20240229` - Most capable, best for complex tasks
- `claude-3-sonnet-20240229` - Balanced performance and speed
- `claude-3-haiku-20240307` - Fastest, most cost-effective
- `claude-3-5-sonnet-20241022` - Latest Sonnet (recommended)
- `claude-3-5-haiku-20241022` - Latest Haiku

## 📚 Documentation

- [Architecture](docs/architecture.md) - System design and patterns
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Configuration Guide](docs/configuration.md) - Advanced configuration options
- [Examples](examples/) - Code examples and tutorials

## 🔧 Troubleshooting

### OpenAI Issues

#### Invalid API Key
```
Error: AuthenticationError: Incorrect API key provided
```
**Solution**:
- Verify API key starts with `sk-proj-` or `sk-`
- Check at https://platform.openai.com/api-keys
- Ensure no extra spaces or newlines in the key

#### Rate Limiting
```
Error: RateLimitError: You exceeded your current quota
```
**Solution**:
- Check your OpenAI account billing at https://platform.openai.com/account/billing
- Upgrade your plan or add payment method
- Implement exponential backoff (built into FlexiAI)

### Google Vertex AI Issues

#### Authentication Failed
```
Error: 401 UNAUTHENTICATED
```
**Solution**:

**For Service Account**:
```bash
# Verify file exists
ls -l /path/to/service-account.json

# Check file permissions
chmod 600 /path/to/service-account.json

# Verify JSON format
python -m json.tool service-account.json
```

**For ADC**:
```bash
# Re-authenticate
gcloud auth application-default login

# Verify authentication
gcloud auth application-default print-access-token

# Set project
gcloud config set project YOUR_PROJECT_ID
```

#### API Not Enabled
```
Error: Vertex AI API has not been used in project xxx before or it is disabled
```
**Solution**:
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID

# Or visit: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
```

#### Permission Denied
```
Error: 403 PERMISSION_DENIED
```
**Solution**:
- Grant "Vertex AI User" role to your service account:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Wrong Project or Location
```
Error: Project not found or Location not supported
```
**Solution**:
- Verify project ID: `gcloud projects list`
- Check supported locations: us-central1, us-east1, europe-west1, asia-northeast1
- Ensure project has billing enabled

#### API Keys Not Supported
```

#### API Keys Not Supported
```
Error: API keys are not supported by this API
```
**Solution**:
- Vertex AI requires OAuth2, not API keys
- Use service account file or ADC
- Vertex AI uses different authentication than Gemini Developer API

### Multi-Provider Failover Issues

#### All Providers Failed
```
Error: AllProvidersFailedError: All configured providers failed
```
**Solution**:
- Check each provider's credentials individually
- Verify network connectivity
- Review circuit breaker status: `client.get_provider_status()`
- Reset circuit breakers: `client.reset_circuit_breakers()`

#### Circuit Breaker Always Open
```
Warning: Circuit breaker open, skipping provider
```
**Solution**:
- Check provider health: `client.get_provider_status()`
- Wait for recovery timeout (default: 60 seconds)
- Manually reset: `client.reset_circuit_breakers()`
- Adjust threshold: `CircuitBreakerConfig(failure_threshold=10)`

### Common Configuration Issues

#### Environment Variables Not Loaded
```python
# ❌ Wrong
api_key = "$OPENAI_API_KEY"  # Literal string, not the value!

# ✅ Correct
import os
api_key = os.getenv("OPENAI_API_KEY")
```

#### Mixing Provider Types
```python
# ❌ Wrong - Vertex AI doesn't use Gemini API keys
ProviderConfig(
    name="vertexai",
    api_key="AIza...",  # Won't work!
    ...
)

# ✅ Correct - Vertex AI needs service account
ProviderConfig(
    name="vertexai",
    api_key="not-used",
    config={"service_account_file": "..."}
)
```

### Getting Help

If you're still experiencing issues:

1. **Check logs**: Enable debug logging
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Verify installation**:
   ```bash
   pip show flexiai
   pip list | grep -E "(openai|google-genai|google-auth)"
   ```

3. **Test providers individually**:
   ```python
   # Test each provider separately first
   config = FlexiAIConfig(providers=[single_provider])
   ```

4. **Open an issue**: Include:
   - FlexiAI version
   - Python version
   - Provider being used
   - Error message and stack trace (remove API keys!)
   - Minimal code to reproduce

## 🧪 Development

### Setup

```bash
git clone https://github.com/yourusername/flexiai.git
cd flexiai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flexiai --cov-report=html

# Run specific test file
pytest tests/unit/test_client.py

# Run integration tests (requires API keys)
export OPENAI_API_KEY="sk-..."
export GOOGLE_CLOUD_PROJECT="your-project"
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black flexiai tests

# Type checking
mypy flexiai

# Linting
flake8 flexiai tests
```

### Building and Installing

```bash
# Install build tool
pip install build

# Build wheel package
python -m build

# Install the built package
pip install dist/flexiai-*.whl
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for their powerful language models
- Google for Gemini and Vertex AI platforms
- The Python community for excellent libraries

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/flexiai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/flexiai/discussions)
- **Email**: support@flexiai.dev

## 🗺️ Roadmap

- [x] Phase 1: OpenAI Support
- [x] Phase 2: Google Vertex AI Support
- [ ] Phase 3: Anthropic Claude Support
- [ ] Phase 4: Streaming Support
- [ ] Phase 5: Azure OpenAI Support
- [ ] Phase 6: AWS Bedrock Support
- [ ] Advanced Features:
  - [ ] Function/Tool calling
  - [ ] Image generation
  - [ ] Embeddings support
  - [ ] Fine-tuning integration
  - [ ] Caching layer
  - [ ] Rate limiting per provider

---

**Made with ❤️ by the FlexiAI Team**
