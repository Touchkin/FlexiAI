# Changelog

All notable changes to FlexiAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 7.2: Multi-Worker Synchronization Architecture (In Progress)**
  - Added `flexiai/sync/` module for distributed state synchronization
  - Implemented `BaseSyncBackend` abstract interface for sync backends
  - Implemented `MemorySyncBackend` for single-worker/development environments
  - Implemented `RedisSyncBackend` for multi-worker production deployments
    - Redis pub/sub for event broadcasting across workers
    - Distributed state storage with TTL (default 3600s)
    - Distributed locking using SETNX pattern
    - Connection pooling and auto-reconnection
  - Implemented `StateSyncManager` to coordinate state synchronization
    - Auto-generates unique worker IDs (hostname:pid:timestamp)
    - Registers circuit breakers for state sync
    - Handles local→remote and remote→local state changes
    - Graceful startup state loading from distributed storage
  - Added `CircuitBreakerEvent` and `StateUpdateEvent` for state changes
  - Added `StateSerializer` for JSON serialization with datetime/enum support
  - Integrated sync manager into `CircuitBreaker` class
    - Broadcasts state changes (OPENED, CLOSED, HALF_OPEN, FAILURE, SUCCESS)
    - Applies remote state changes from other workers
    - Thread-safe state serialization/deserialization
  - Integrated sync manager into `FlexiAI` client
    - Optional sync manager initialization based on configuration
    - Automatic fallback from Redis to Memory backend
    - Passes sync_manager to provider registry and circuit breakers
    - Graceful shutdown with `close()` method
  - Added `SyncConfig` model for multi-worker configuration
    - Redis connection settings (host, port, db, password, SSL)
    - Worker ID customization
    - Key prefix and pub/sub channel configuration
    - State TTL configuration
  - Tests:
    - 15/15 memory backend tests passing
    - Event, serializer, and manager tests added (need API alignment)
    - Total sync test coverage: 65 tests added

- **Phase 7.1: FlexiAI Decorator Implementation (Complete)**
- **Removed GeminiProvider (Google Gemini Developer API)**
  - Removed `flexiai/providers/gemini_provider.py`
  - Removed `tests/unit/test_gemini_provider.py`
  - Removed `tests/integration/test_gemini_integration.py`
  - Removed `examples/gemini_basic.py`
  - Removed GeminiProvider from provider registry
  - Updated all documentation to focus on VertexAIProvider for Google Gemini models
  - **Migration**: Use VertexAIProvider instead for accessing Gemini models on Google Cloud Platform

### Added
- **Phase 2: Google Vertex AI Integration (Complete)**
  - Added `google-genai>=0.8.0` dependency
  - Implemented `VertexAIProvider` class for Google Vertex AI (GCP)
  - Added `GeminiRequestNormalizer` for request format conversion (shared with Vertex AI)
  - Added `GeminiResponseNormalizer` for response format conversion (shared with Vertex AI)
  - Support for gemini-2.0-flash, gemini-1.5-pro, and other Gemini models on Vertex AI
  - Support for Vertex AI models (text-bison, chat-bison, codechat-bison)
  - Multi-provider failover: OpenAI → Vertex AI
  - Vertex AI service account and ADC authentication
  - Safety ratings preservation in response metadata
  - 18 Vertex AI unit tests, 10 integration tests

- **Phase 2.9: Comprehensive Documentation (Complete)**
  - Complete README.md with OpenAI and Vertex AI providers
  - Installation guide, quick start, multi-provider failover examples
  - Authentication methods for each provider documented
  - Example files:
    - `examples/vertexai_basic.py` - 6 Vertex AI examples
    - `examples/multi_provider_failover.py` - 5 multi-provider examples
  - Updated `docs/api-reference.md` with VertexAIProvider
  - Updated `docs/configuration.md` with GCP authentication guide
  - Comprehensive troubleshooting section covering OpenAI and Vertex AI
  - Security best practices for GCP service accounts
  - Supported models list for all providers
  - Roadmap and contribution guidelines

### Changed
- Updated `ModelValidator` to support Vertex AI models (gemini-2.5, gemini-2.0, gemini-1.5, gemini-pro, text-bison, chat-bison, codechat-bison)
- Updated `APIKeyValidator` to remove Gemini API key validation (no longer needed)
- Enhanced `FlexiAI` client to support multiple providers simultaneously (OpenAI, Vertex AI)
- Updated provider registry to handle Vertex AI provider
- Updated `ProviderConfig` validator to include "vertexai" as supported provider (removed "gemini")
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
