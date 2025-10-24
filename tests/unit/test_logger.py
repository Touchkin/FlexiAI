"""
Unit tests for FlexiAI logging utilities.

Tests the FlexiAILogger class, sensitive data masking,
and correlation ID functionality.
"""

import logging
import tempfile
from pathlib import Path

from flexiai.utils.logger import CorrelationIdFilter, FlexiAILogger, SensitiveDataFilter, get_logger


class TestSensitiveDataFilter:
    """Tests for SensitiveDataFilter."""

    def test_mask_openai_api_key(self) -> None:
        """Test masking of OpenAI API keys."""
        filter_obj = SensitiveDataFilter()
        text = "Using API key: sk-1234567890abcdefghij"
        masked = filter_obj._mask_sensitive_data(text)
        assert "sk-1234567890abcdefghij" not in masked
        assert "***MASKED***" in masked
        assert "Using API key:" in masked

    def test_mask_bearer_token(self) -> None:
        """Test masking of Bearer tokens."""
        filter_obj = SensitiveDataFilter()
        text = "Authorization: Bearer abc123xyz456"
        masked = filter_obj._mask_sensitive_data(text)
        assert "abc123xyz456" not in masked
        assert "***MASKED***" in masked
        assert "Authorization:" in masked

    def test_mask_api_key_in_json(self) -> None:
        """Test masking of API key in JSON format."""
        filter_obj = SensitiveDataFilter()
        text = '{"api_key": "sk-secretkey12345"}'
        masked = filter_obj._mask_sensitive_data(text)
        assert "sk-secretkey12345" not in masked
        assert "***MASKED***" in masked

    def test_mask_token_field(self) -> None:
        """Test masking of token field."""
        filter_obj = SensitiveDataFilter()
        text = "token=abc123def456ghi789jkl012"
        masked = filter_obj._mask_sensitive_data(text)
        assert "abc123def456ghi789jkl012" not in masked
        assert "***MASKED***" in masked

    def test_preserve_non_sensitive_data(self) -> None:
        """Test that non-sensitive data is preserved."""
        filter_obj = SensitiveDataFilter()
        text = "model=gpt-4 temperature=0.7"
        masked = filter_obj._mask_sensitive_data(text)
        assert masked == text

    def test_filter_log_record(self) -> None:
        """Test filtering of log records."""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API key: sk-test123456789",
            args=(),
            exc_info=None,
        )
        result = filter_obj.filter(record)
        assert result is True
        assert "sk-test123456789" not in str(record.msg)


class TestCorrelationIdFilter:
    """Tests for CorrelationIdFilter."""

    def test_add_correlation_id(self) -> None:
        """Test adding correlation ID to log record."""
        FlexiAILogger.set_correlation_id("test-corr-id-123")
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = filter_obj.filter(record)
        assert result is True
        assert hasattr(record, "correlation_id")
        assert record.correlation_id == "test-corr-id-123"
        FlexiAILogger.clear_correlation_id()

    def test_default_correlation_id(self) -> None:
        """Test default correlation ID when none is set."""
        FlexiAILogger.clear_correlation_id()
        filter_obj = CorrelationIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        filter_obj.filter(record)
        assert record.correlation_id == "N/A"


class TestFlexiAILogger:
    """Tests for FlexiAILogger class."""

    def setup_method(self) -> None:
        """Reset logger configuration before each test."""
        FlexiAILogger._configured = False
        FlexiAILogger._loggers = {}
        FlexiAILogger.clear_correlation_id()
        # Clear all handlers from flexiai logger
        logger = logging.getLogger("flexiai")
        logger.handlers.clear()

    def test_setup_logging_default(self) -> None:
        """Test default logging setup."""
        FlexiAILogger.setup_logging()
        assert FlexiAILogger._configured is True

        logger = logging.getLogger("flexiai")
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1  # At least console handler

    def test_setup_logging_with_file(self) -> None:
        """Test logging setup with file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            FlexiAILogger.setup_logging(level="DEBUG", log_file=str(log_file))

            logger = logging.getLogger("flexiai")
            assert logger.level == logging.DEBUG
            assert log_file.exists()

    def test_setup_logging_custom_format(self) -> None:
        """Test logging setup with custom format."""
        custom_format = "%(levelname)s - %(message)s"
        FlexiAILogger.setup_logging(format_string=custom_format)
        assert FlexiAILogger._configured is True

    def test_get_logger(self) -> None:
        """Test getting a logger instance."""
        logger = FlexiAILogger.get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "flexiai"

    def test_get_logger_with_name(self) -> None:
        """Test getting a logger with custom name."""
        logger = FlexiAILogger.get_logger("flexiai.test")
        assert logger.name == "flexiai.test"

    def test_get_logger_caching(self) -> None:
        """Test that loggers are cached."""
        logger1 = FlexiAILogger.get_logger("flexiai.test")
        logger2 = FlexiAILogger.get_logger("flexiai.test")
        assert logger1 is logger2

    def test_set_correlation_id(self) -> None:
        """Test setting correlation ID."""
        corr_id = FlexiAILogger.set_correlation_id("test-123")
        assert corr_id == "test-123"

    def test_set_correlation_id_auto_generate(self) -> None:
        """Test auto-generating correlation ID."""
        corr_id = FlexiAILogger.set_correlation_id()
        assert corr_id is not None
        assert len(corr_id) > 0

    def test_clear_correlation_id(self) -> None:
        """Test clearing correlation ID."""
        FlexiAILogger.set_correlation_id("test-123")
        FlexiAILogger.clear_correlation_id()
        # Correlation ID should be None or default

    def test_correlation_context(self) -> None:
        """Test correlation context manager."""
        with FlexiAILogger.correlation_context("ctx-123") as corr_id:
            assert corr_id == "ctx-123"
        # After context, correlation ID should be cleared

    def test_correlation_context_auto_generate(self) -> None:
        """Test correlation context with auto-generated ID."""
        with FlexiAILogger.correlation_context() as corr_id:
            assert corr_id is not None
            assert len(corr_id) > 0

    def test_mask_sensitive_data_dict(self) -> None:
        """Test masking sensitive data in dictionary."""
        data = {"api_key": "sk-secret", "model": "gpt-4", "token": "abc123"}
        masked = FlexiAILogger.mask_sensitive_data(data)
        assert masked["api_key"] == "***MASKED***"
        assert masked["model"] == "gpt-4"
        assert masked["token"] == "***MASKED***"

    def test_mask_sensitive_data_nested_dict(self) -> None:
        """Test masking sensitive data in nested dictionary."""
        data = {
            "config": {"api_key": "sk-secret", "timeout": 30},
            "model": "gpt-4",
        }
        masked = FlexiAILogger.mask_sensitive_data(data)
        assert masked["config"]["api_key"] == "***MASKED***"
        assert masked["config"]["timeout"] == 30
        assert masked["model"] == "gpt-4"

    def test_mask_sensitive_data_list(self) -> None:
        """Test masking sensitive data in list."""
        data = [
            {"api_key": "sk-secret1"},
            {"api_key": "sk-secret2"},
        ]
        masked = FlexiAILogger.mask_sensitive_data(data)
        assert all(item["api_key"] == "***MASKED***" for item in masked)

    def test_mask_sensitive_data_string(self) -> None:
        """Test masking sensitive data in string."""
        data = "Using API key: sk-1234567890abcdef"
        masked = FlexiAILogger.mask_sensitive_data(data)
        assert "sk-1234567890abcdef" not in masked
        assert "***MASKED***" in masked

    def test_is_sensitive_key(self) -> None:
        """Test detection of sensitive keys."""
        assert FlexiAILogger._is_sensitive_key("api_key") is True
        assert FlexiAILogger._is_sensitive_key("API_KEY") is True
        assert FlexiAILogger._is_sensitive_key("api-key") is True
        assert FlexiAILogger._is_sensitive_key("token") is True
        assert FlexiAILogger._is_sensitive_key("password") is True
        assert FlexiAILogger._is_sensitive_key("model") is False
        assert FlexiAILogger._is_sensitive_key("temperature") is False

    def test_logging_masks_sensitive_data(self) -> None:
        """Test that actual logging masks sensitive data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            FlexiAILogger.setup_logging(level="INFO", log_file=str(log_file))

            logger = FlexiAILogger.get_logger()
            logger.info("API key: sk-testsecretkey12345")

            # Read log file and verify masking
            log_content = log_file.read_text()
            assert "sk-testsecretkey12345" not in log_content
            assert "***MASKED***" in log_content


class TestGetLogger:
    """Tests for get_logger convenience function."""

    def setup_method(self) -> None:
        """Reset logger configuration."""
        FlexiAILogger._configured = False
        FlexiAILogger._loggers = {}

    def test_get_logger_default(self) -> None:
        """Test getting default logger."""
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "flexiai"

    def test_get_logger_with_name(self) -> None:
        """Test getting logger with custom name."""
        logger = get_logger("flexiai.custom")
        assert logger.name == "flexiai.custom"
