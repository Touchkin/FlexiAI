# Changelog

All notable changes to FlexiAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-10-26

### Added - Phase 7 Complete: Decorator Support + Multi-Worker Synchronization

**🎨 Phase 7.1: Decorator API**
- Added `@flexiai_chat_completion` decorator for simplified LLM integration
  - Clean, Pythonic interface for chat completions
  - Automatic provider selection and failover
  - Full parameter support (temperature, max_tokens, system_message, etc.)
  - Works with both sync and async functions
  - Type-safe with proper type hints
- Added 3 comprehensive decorator examples:
  - `examples/decorator_basic.py` - Basic usage patterns
  - `examples/decorator_advanced.py` - Multi-provider with explicit selection
  - `examples/decorator_async.py` - Async/concurrent usage
- 36 decorator unit tests (91% coverage on decorators.py)
- All examples tested with real API calls

**🔄 Phase 7.2: Multi-Worker Synchronization**
- Added `flexiai/sync/` module (8 files, 957 lines) for distributed state synchronization:
  - `BaseSyncBackend` - Abstract interface for sync backends
  - `MemorySyncBackend` - Single-worker/development mode (in-memory state)
  - `RedisSyncBackend` - Production multi-worker mode with Redis pub/sub
  - `StateSyncManager` - Coordinates state sync across workers
  - `CircuitBreakerEvent` & `StateUpdateEvent` - State change events
  - `StateSerializer` - JSON serialization with datetime/enum support
- Circuit breaker state synchronization across workers:
  - Real-time event broadcasting via Redis pub/sub
  - Distributed state storage with configurable TTL
  - Automatic state recovery on worker startup
  - Thread-safe state serialization
- 64 sync unit tests (89% coverage on sync module)
- 14 Redis integration tests + 2 circuit breaker sync tests
- Verified with real Redis pub/sub in multi-worker environment

**🚀 Phase 7.3: Production Multi-Worker Deployment**
- Production-ready FastAPI application (`examples/fastapi_multiworker/`):
  - Complete multi-worker example (610 lines)
  - Comprehensive health check endpoints:
    - `/health` - Full health status with provider details
    - `/health/ready` - Kubernetes readiness probe
    - `/health/live` - Kubernetes liveness probe
  - Chat completion endpoints:
    - `/chat/direct` - Direct FlexiAI client usage
    - `/chat/decorator` - Decorator-based usage
  - Provider management endpoints:
    - `/providers` - Get provider status
    - `/providers/{name}/reset` - Reset circuit breakers
  - Metrics endpoint: `/metrics` - Prometheus-compatible metrics
  - Graceful startup/shutdown with lifespan management
  - Structured logging with worker identification
  - Docker Compose setup for easy deployment
  - Kubernetes manifests with HPA
- Comprehensive deployment documentation (1,300+ lines):
  - `docs/multi_worker_deployment.md` (682 lines):
    - Architecture overview with ASCII diagrams
    - Quick start guide (5-minute setup)
    - 4 deployment scenarios (single, multiple, Docker, K8s)
    - Load balancing configs (Nginx, HAProxy, Kubernetes)
    - Monitoring and observability guide
    - Troubleshooting and performance tuning
  - `docs/production_best_practices.md` (650 lines):
    - Redis production setup (Sentinel, Cluster, persistence)
    - 3-tier health check strategies
    - Scaling guidelines (vertical and horizontal)
    - Performance optimization (connection pooling, caching, batching)
    - Security hardening (auth, TLS, secrets management, rate limiting)
    - Observability (structured logging, Prometheus, tracing)
    - Disaster recovery procedures
    - Production readiness checklist

**✅ Testing & Quality**
- 599 total tests passing (up from 461 in v0.3.0)
- 90% code coverage (up from 87%)
- All Phase 7 components fully tested:
  - 36 decorator tests
  - 64 sync unit tests
  - 14 Redis integration tests
  - 2 circuit breaker sync integration tests
- All pre-commit hooks passing
- All examples tested with real API calls

### Changed
- Updated `FlexiAI` client to support optional sync manager
- Updated `CircuitBreaker` to broadcast state changes when sync is enabled
- Updated `ProviderRegistry` to pass sync manager to circuit breakers
- Improved error handling and logging throughout
- Enhanced documentation with real-world examples

### Documentation
- Added comprehensive Phase 7 documentation
- Updated README with decorator examples
- Created production deployment guides
- Added Docker and Kubernetes deployment configs
- Updated TODO.md with Phase 7 completion status

## [Unreleased]

### Added
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
