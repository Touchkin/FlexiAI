# FlexiAI

A unified interface for multiple GenAI providers (OpenAI, Google Gemini, Anthropic Claude) with automatic failover using circuit breaker pattern.

## 🚀 Features

- **Multi-Provider Support**: Seamlessly switch between OpenAI, Google Gemini, and Anthropic Claude
- **Automatic Failover**: Circuit breaker pattern ensures high availability
- **Unified API**: Single interface for all providers - write once, use anywhere
- **Type-Safe**: Built with Pydantic for robust data validation
- **Production-Ready**: Comprehensive error handling, logging, and retry logic
- **Easy Configuration**: Simple configuration via dict, JSON file, or environment variables

## 📦 Installation

```bash
pip install flexiai
```

## 🎯 Quick Start

```python
from flexiai import FlexiAI, FlexiAIConfig, ProviderConfig

# Configure providers with priority
config = FlexiAIConfig(
    providers=[
        ProviderConfig(
            name="openai",
            priority=1,
            api_key="your-openai-key",
            model="gpt-4-turbo-preview"
        ),
        ProviderConfig(
            name="gemini",
            priority=2,
            api_key="your-gemini-key",
            model="gemini-pro"
        ),
        ProviderConfig(
            name="anthropic",
            priority=3,
            api_key="your-claude-key",
            model="claude-3-sonnet"
        )
    ]
)

# Initialize client
client = FlexiAI(config)

# Make a request - FlexiAI handles failover automatically!
response = client.chat_completion(
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ],
    temperature=0.7,
    max_tokens=1000
)

print(response.content)
print(f"Provider used: {response.provider}")
print(f"Tokens used: {response.usage.total_tokens}")
```

## 📚 Documentation

**Status**: 🚧 In Development (Phase 1: Core Foundation + OpenAI Support)

Full documentation will be available soon. For now, please refer to the `Instructions.md` file for the comprehensive development plan.

## 🛠️ Development Status

FlexiAI is currently under active development. Here's the roadmap:

### Phase 1: Core Foundation + OpenAI Support ✅ (In Progress)
- [x] Project setup
- [ ] Core models and exceptions
- [ ] Configuration management
- [ ] OpenAI provider implementation
- [ ] Circuit breaker pattern
- [ ] Basic testing and documentation

### Phase 2: Google Gemini Integration 📋 (Planned)
- [ ] Gemini provider implementation
- [ ] Multi-provider failover testing

### Phase 3: Anthropic Claude Integration 📋 (Planned)
- [ ] Claude provider implementation
- [ ] Three-way provider failover

### Phase 4: Advanced Features 📋 (Planned)
- [ ] Streaming support
- [ ] Async operations
- [ ] Function calling
- [ ] Cost tracking
- [ ] Advanced monitoring

## 🤝 Contributing

Contributions are welcome! This project is in early development. Please see `Instructions.md` for the comprehensive development plan and guidelines.

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Links

- **GitHub**: https://github.com/yourusername/flexiai
- **Documentation**: Coming soon
- **Issue Tracker**: https://github.com/yourusername/flexiai/issues

## ⚠️ Development Notice

This is an alpha release. The API may change as we progress through development phases. Use in production at your own risk.

---

Built with ❤️ by the FlexiAI community
