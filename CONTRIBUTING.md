# Contributing to FlexiAI

Thank you for your interest in contributing to FlexiAI! This document provides guidelines and instructions for contributing to the project.

## 🌟 Ways to Contribute

- **Bug Reports**: Report bugs through GitHub Issues
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests for bug fixes or new features
- **Documentation**: Improve documentation, fix typos, add examples
- **Testing**: Add test cases, improve test coverage
- **Review**: Review pull requests from other contributors

## 📋 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/flexiai.git
cd flexiai

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/flexiai.git
```

### 2. Set Up Development Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feature/your-feature-name
# Or for bug fixes:
git checkout -b fix/bug-description
```

## 🔧 Development Guidelines

### Code Style

FlexiAI follows PEP 8 and uses automated tools to enforce consistency:

- **black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking (optional but recommended)

```bash
# Format code
black flexiai/ tests/

# Sort imports
isort flexiai/ tests/

# Check linting
flake8 flexiai/ tests/ --max-line-length=100

# Type checking
mypy flexiai/
```

### Type Hints

All functions and methods should include type hints:

```python
def chat_completion(
    self,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> UnifiedResponse:
    """
    Generate a chat completion.

    Args:
        messages: List of message dictionaries
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        UnifiedResponse with completion result

    Raises:
        ValidationError: If parameters are invalid
        AllProvidersFailedError: If all providers fail
    """
    pass
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all public functions/classes
- **Comments**: Add comments for complex logic
- **Type Hints**: Include type hints for better IDE support
- **Examples**: Include usage examples in docstrings

Example docstring:

```python
def validate_api_key(provider: str, api_key: str) -> bool:
    """
    Validate an API key for a specific provider.

    Args:
        provider: Provider name (openai, gemini, anthropic, etc.)
        api_key: API key to validate

    Returns:
        True if the API key is valid

    Raises:
        ValidationError: If the API key format is invalid

    Example:
        >>> validate_api_key("openai", "sk-abc123...")
        True
    """
    pass
```

## ✅ Testing

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage (target: 95%+)
- Use descriptive test names
- Include edge cases and error conditions

```python
def test_circuit_breaker_opens_after_threshold():
    """Test that circuit opens after reaching failure threshold."""
    circuit_breaker = CircuitBreaker(
        name="test",
        config=CircuitBreakerConfig(failure_threshold=3)
    )

    # Simulate failures
    for _ in range(3):
        with pytest.raises(Exception):
            circuit_breaker.call(lambda: raise_exception())

    # Circuit should now be open
    assert circuit_breaker.is_open()
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_circuit_breaker.py

# Run with coverage
pytest tests/ --cov=flexiai --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run with verbose output
pytest tests/ -v

# Run specific test
pytest tests/unit/test_circuit_breaker.py::test_circuit_breaker_opens_after_threshold
```

### Test Organization

```
tests/
├── unit/                  # Unit tests
│   ├── test_client.py
│   ├── test_circuit_breaker.py
│   ├── test_models.py
│   └── ...
├── integration/           # Integration tests (require API keys)
│   ├── conftest.py
│   └── test_openai_integration.py
└── conftest.py           # Shared fixtures
```

## 🔀 Pull Request Process

### 1. Before Submitting

- [ ] Run all tests and ensure they pass
- [ ] Run pre-commit hooks
- [ ] Update documentation if needed
- [ ] Add/update tests for new features
- [ ] Ensure code coverage doesn't decrease

```bash
# Run full check
pytest tests/ --cov=flexiai
pre-commit run --all-files
```

### 2. Commit Messages

Use clear, descriptive commit messages:

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

Example:
```
feat: Add support for custom retry strategies

- Added RetryStrategy class for configurable retry logic
- Implemented exponential backoff with jitter
- Added tests for retry strategy
- Updated documentation

Closes #123
```

### 3. Submit Pull Request

1. Push your branch to your fork
2. Open a Pull Request against `main`
3. Fill out the PR template
4. Wait for CI checks to pass
5. Address review feedback

### 4. PR Checklist

Your PR should include:

- [ ] Clear description of changes
- [ ] Tests for new functionality
- [ ] Documentation updates
- [ ] No decrease in code coverage
- [ ] All CI checks passing
- [ ] Code reviewed and approved

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues to avoid duplicates
2. Verify the bug exists in the latest version
3. Collect relevant information

### Bug Report Template

```markdown
**Description**
A clear description of the bug.

**To Reproduce**
Steps to reproduce the behavior:
1. Configure with '...'
2. Call method '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- FlexiAI version: [e.g., 0.1.0]
- Python version: [e.g., 3.10]
- OS: [e.g., Ubuntu 22.04]
- Provider: [e.g., OpenAI]

**Additional Context**
- Error messages
- Stack traces
- Configuration (redact API keys!)
- Code snippets
```

## 💡 Feature Requests

### Feature Request Template

```markdown
**Problem**
Describe the problem or use case.

**Proposed Solution**
Describe your proposed solution.

**Alternatives Considered**
Other solutions you've considered.

**Additional Context**
Any other relevant information.
```

## 📝 Documentation

### Types of Documentation

1. **Code Documentation**: Docstrings, type hints, comments
2. **User Documentation**: README, guides, examples
3. **API Reference**: Complete API documentation
4. **Architecture Documentation**: Design decisions, patterns

### Documentation Standards

- Use Markdown for all documentation files
- Include code examples
- Keep examples up to date
- Add screenshots where helpful
- Link to related documentation

## 🏗️ Architecture Guidelines

### Project Structure

```
flexiai/
├── __init__.py           # Package exports
├── client.py            # Main FlexiAI client
├── models.py            # Pydantic models
├── exceptions.py        # Custom exceptions
├── config.py            # Configuration management
├── circuit_breaker/     # Circuit breaker implementation
│   ├── __init__.py
│   ├── breaker.py
│   └── state.py
├── providers/           # Provider implementations
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   └── openai_provider.py
├── normalizers/         # Request/response normalizers
│   ├── __init__.py
│   ├── request.py
│   └── response.py
└── utils/               # Utilities
    ├── __init__.py
    ├── logger.py
    └── validators.py
```

### Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Open/Closed Principle**: Open for extension, closed for modification
3. **Dependency Injection**: Use configuration objects, not globals
4. **Type Safety**: Use Pydantic models and type hints
5. **Error Handling**: Explicit error types, meaningful messages
6. **Logging**: Structured logging with correlation IDs

### Adding a New Provider

1. Create provider class inheriting from `BaseProvider`
2. Implement required abstract methods
3. Create request/response normalizers
4. Add provider to registry
5. Write comprehensive tests
6. Update documentation

Example:

```python
from flexiai.providers.base import BaseProvider
from flexiai.normalizers.request import RequestNormalizer
from flexiai.normalizers.response import ResponseNormalizer

class GeminiProvider(BaseProvider):
    """Google Gemini provider implementation."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Initialize Gemini client

    def chat_completion(self, request: UnifiedRequest) -> UnifiedResponse:
        # Implement chat completion
        pass

    def authenticate(self) -> bool:
        # Implement authentication
        pass
```

## 🔒 Security

### Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead, email security@example.com with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Guidelines

- Never commit API keys or secrets
- Validate all user inputs
- Use environment variables for sensitive data
- Keep dependencies updated
- Run security scans (bandit)

## 📜 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information
- Other conduct inappropriate in a professional setting

## 🎯 Development Workflow

### 1. Pick an Issue

- Check "good first issue" labels for beginner-friendly tasks
- Comment on the issue to claim it
- Ask questions if anything is unclear

### 2. Develop

- Write code following guidelines
- Add tests
- Update documentation
- Run pre-commit hooks

### 3. Test

```bash
# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=flexiai --cov-report=term-missing

# Run linting
flake8 flexiai/ tests/
```

### 4. Submit

- Push to your fork
- Create pull request
- Respond to feedback
- Update as needed

## 📚 Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

## ❓ Questions?

- Create a GitHub Discussion
- Check existing documentation
- Ask in pull request comments
- Email maintainers

## 🙏 Thank You!

Every contribution helps make FlexiAI better. We appreciate your time and effort!

---

**Happy Contributing! 🚀**
