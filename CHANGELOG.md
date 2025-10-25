# Changelog

All notable changes to FlexiAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 2: Google Gemini & Vertex AI Integration (Complete)**
  - Added `google-genai>=0.8.0` dependency
  - Implemented `GeminiProvider` class for Google Gemini Developer API
  - Implemented `VertexAIProvider` class for Google Vertex AI (GCP)
  - Added `GeminiRequestNormalizer` for request format conversion
  - Added `GeminiResponseNormalizer` for response format conversion
  - Support for gemini-2.0-flash, gemini-1.5-pro, and other Gemini models
  - Support for Vertex AI models (text-bison, chat-bison, codechat-bison)
  - Multi-provider failover: OpenAI → Gemini → Vertex AI
  - Gemini API key validation (AIza pattern)
  - Vertex AI service account and ADC authentication
  - Safety ratings preservation in response metadata
  - 39 new tests (19 normalizer tests, 10 provider tests, 10 integration tests)
  - 18 Vertex AI unit tests, 10 integration tests
  
- **Phase 2.9: Comprehensive Documentation (Complete)**
  - Complete README.md with all 3 providers (OpenAI, Gemini, Vertex AI)
  - Installation guide, quick start, multi-provider failover examples
  - Authentication methods for each provider documented
  - Example files:
    - `examples/gemini_basic.py` - 6 Gemini Developer API examples
    - `examples/vertexai_basic.py` - 6 Vertex AI examples
    - `examples/multi_provider_failover.py` - 5 multi-provider examples
  - Updated `docs/api-reference.md` with GeminiProvider and VertexAIProvider
  - Updated `docs/configuration.md` with GCP authentication guide
  - Comprehensive troubleshooting section covering all providers
  - Security best practices for GCP service accounts
  - Supported models list for all providers
  - Roadmap and contribution guidelines

### Changed
- Updated `ModelValidator` to support Gemini models (gemini-2.5, gemini-2.0, gemini-1.5, gemini-pro)
- Updated `ModelValidator` to support Vertex AI models (same as Gemini + text-bison, chat-bison, codechat-bison)
- Updated `APIKeyValidator` to validate Gemini API keys
- Enhanced `FlexiAI` client to support multiple providers simultaneously (OpenAI, Gemini, Vertex AI)
- Updated provider registry to handle Gemini and Vertex AI providers
- Updated `ProviderConfig` validator to include "gemini" and "vertexai" as supported providers
- Enhanced multi-provider failover with independent circuit breakers per provider

### Fixed
- N/A

### Security
- Added comprehensive .gitignore patterns for credentials (*.json, *.key, service-account*.json)
- Documented security best practices for service account management
- Added warnings about never committing credentials to version control

---

## [0.1.0] - 2025-10-25

### Added
- **Phase 1: Core Foundation + OpenAI Support (Complete)**
  - Project setup with proper package structure
  - Configuration management system (FlexiAIConfig, ProviderConfig, CircuitBreakerConfig)
  - Core models (Message, UnifiedRequest, UnifiedResponse, TokenUsage)
  - Exception hierarchy (8 custom exceptions)
  - OpenAI provider implementation with full API support
  - Circuit breaker pattern implementation (CLOSED → OPEN → HALF_OPEN states)
  - Provider registry with priority-based selection
  - Request/response normalization for OpenAI
  - FlexiAI main client with automatic failover
  - Comprehensive logging and utilities
  - API key and model validators
  - 387 tests (377 unit + 10 integration)
  - 98% test coverage
  - Complete documentation (~3,500 lines)
    - README.md with features, examples, and roadmap
    - CONTRIBUTING.md with development guidelines
    - docs/architecture.md with design patterns
    - docs/api-reference.md with complete API documentation
    - docs/configuration.md with patterns and best practices
  - Package distribution ready
    - Built wheel: flexiai-0.1.0-py3-none-any.whl (41KB)
    - Built source distribution: flexiai-0.1.0.tar.gz (52KB)
    - MIT License
    - Ready for PyPI publication

### Dependencies
- openai>=1.0.0
- pydantic>=2.0.0
- tenacity>=8.0.0
- python-dotenv>=1.0.0
- google-genai>=0.8.0 (Phase 2)

---

## Release Notes Format

### Version Number Guidelines
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backwards compatible manner
- **PATCH**: Backwards compatible bug fixes

### Change Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
