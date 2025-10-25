# Changelog

All notable changes to FlexiAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 2: Google Gemini Integration (In Progress)**
  - Added `google-genai>=0.8.0` dependency
  - Implemented `GeminiProvider` class for Google Gemini API integration
  - Added `GeminiRequestNormalizer` for request format conversion
  - Added `GeminiResponseNormalizer` for response format conversion
  - Support for gemini-2.0-flash-exp and other Gemini models
  - Multi-provider failover between OpenAI and Gemini
  - Gemini API key validation (AIza pattern)
  - Safety ratings preservation in response metadata
  - 39 new tests (19 normalizer tests, 10 provider tests, 10 integration tests)
  - Integration tests ready for real Gemini API (requires GEMINI_API_KEY)
- **Phase 2.8: Vertex AI Provider (Complete)**
  - Implemented `VertexAIProvider` class for Google Vertex AI integration
  - Uses Google Cloud Application Default Credentials (ADC) instead of API keys
  - Support for GCP project and location configuration
  - Reuses Gemini normalizers (same API format as Gemini)
  - Support for Vertex AI specific models (text-bison, chat-bison, codechat-bison)
  - 19 comprehensive unit tests for Vertex AI provider
  - 10 integration tests (requires GOOGLE_CLOUD_PROJECT env var)
  - Multi-provider support: OpenAI + Gemini + Vertex AI
  - Automatic failover across all three providers

### Changed
- Updated `ModelValidator` to support Gemini models (gemini-2.5, gemini-2.0, gemini-1.5, gemini-pro)
- Updated `ModelValidator` to support Vertex AI models (same as Gemini + text-bison, chat-bison, codechat-bison)
- Updated `APIKeyValidator` to validate Gemini API keys
- Enhanced `FlexiAI` client to support multiple providers simultaneously (OpenAI, Gemini, Vertex AI)
- Updated provider registry to handle Gemini and Vertex AI providers
- Updated `ProviderConfig` validator to include "vertexai" as supported provider

### Fixed
- N/A

### Security
- N/A

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
