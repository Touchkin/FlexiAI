"""
Logging configuration and utilities for FlexiAI.

This module provides structured logging with:
- Rotating file handler
- Console handler for warnings/errors
- Sensitive data masking (API keys)
- Log correlation IDs for request tracing
- Debug mode for request/response logging
"""

import logging
import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Generator, Optional

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class SensitiveDataFilter(logging.Filter):
    """
    Filter to mask sensitive data in log messages.

    Masks API keys, tokens, and other sensitive information before logging.
    """

    # Patterns for sensitive data
    PATTERNS = [
        # API keys (sk-..., key-..., etc.)
        (re.compile(r"sk-[a-zA-Z0-9]{8,}", re.IGNORECASE), "***MASKED***"),
        (re.compile(r"key-[a-zA-Z0-9]{8,}", re.IGNORECASE), "***MASKED***"),
        # Bearer tokens
        (re.compile(r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*", re.IGNORECASE), "***MASKED***"),
        # Generic tokens
        (
            re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9\-._~+/]{8,})", re.IGNORECASE),
            r"\1***MASKED***",
        ),
        # API key fields in JSON/dict
        (
            re.compile(r"(['\"]api_key['\"]:\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
            r"\1***MASKED***\3",
        ),
        # Authorization headers
        (
            re.compile(r"(Authorization[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)", re.IGNORECASE),
            r"\1***MASKED***",
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and mask sensitive data in log records.

        Args:
            record: Log record to filter

        Returns:
            True (always allows the record through after masking)
        """
        record.msg = self._mask_sensitive_data(str(record.msg))
        if record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _mask_sensitive_data(self, text: str) -> str:
        """
        Mask sensitive data in text.

        Args:
            text: Text to mask

        Returns:
            Text with sensitive data masked
        """
        for pattern, replacement in self.PATTERNS:
            text = pattern.sub(replacement, text)
        return text


class CorrelationIdFilter(logging.Filter):
    """
    Filter to add correlation ID to log records.

    Adds a correlation ID to each log record for request tracing.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to log record.

        Args:
            record: Log record to enhance

        Returns:
            True (always allows the record through)
        """
        record.correlation_id = correlation_id.get() or "N/A"
        return True


class FlexiAILogger:
    """
    Custom logger for FlexiAI with structured logging and sensitive data masking.

    Features:
    - Rotating file handler for persistent logs
    - Console handler for warnings and errors
    - Automatic sensitive data masking
    - Correlation ID support for request tracing
    - Configurable log levels

    Example:
        >>> logger = FlexiAILogger.get_logger()
        >>> logger.info("Processing request", extra={"model": "gpt-4"})
        >>> with FlexiAILogger.correlation_context():
        ...     logger.info("Request started")
    """

    _loggers: Dict[str, logging.Logger] = {}
    _configured = False

    @classmethod
    def setup_logging(
        cls,
        level: str = "INFO",
        log_file: Optional[str] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        format_string: Optional[str] = None,
    ) -> None:
        """
        Set up logging configuration for FlexiAI.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (None for no file logging)
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            format_string: Custom log format string

        Example:
            >>> FlexiAILogger.setup_logging(
            ...     level="DEBUG",
            ...     log_file="flexiai.log",
            ...     max_bytes=5*1024*1024
            ... )
        """
        if cls._configured:
            return

        # Default format with correlation ID
        if format_string is None:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - " "[%(correlation_id)s] - %(message)s"
            )

        formatter = logging.Formatter(format_string)

        # Get root logger for flexiai
        logger = logging.getLogger("flexiai")
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers.clear()

        # Console handler (WARNING and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter())
        console_handler.addFilter(CorrelationIdFilter())
        logger.addHandler(console_handler)

        # File handler (all levels)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            file_handler.addFilter(SensitiveDataFilter())
            file_handler.addFilter(CorrelationIdFilter())
            logger.addHandler(file_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str = "flexiai") -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (default: "flexiai")

        Returns:
            Logger instance

        Example:
            >>> logger = FlexiAILogger.get_logger("flexiai.providers.openai")
            >>> logger.info("OpenAI request completed")
        """
        if not cls._configured:
            cls.setup_logging()

        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)

        return cls._loggers[name]

    @classmethod
    def set_correlation_id(cls, corr_id: Optional[str] = None) -> str:
        """
        Set correlation ID for request tracing.

        Args:
            corr_id: Correlation ID (generates UUID if None)

        Returns:
            The correlation ID that was set

        Example:
            >>> corr_id = FlexiAILogger.set_correlation_id()
            >>> logger.info("Request processing")  # Will include correlation ID
        """
        if corr_id is None:
            corr_id = str(uuid.uuid4())
        correlation_id.set(corr_id)
        return corr_id

    @classmethod
    def clear_correlation_id(cls) -> None:
        """
        Clear the correlation ID.

        Example:
            >>> FlexiAILogger.clear_correlation_id()
        """
        correlation_id.set(None)

    @classmethod
    @contextmanager
    def correlation_context(cls, corr_id: Optional[str] = None) -> Generator[str, None, None]:
        """
        Context manager for correlation ID.

        Args:
            corr_id: Correlation ID (generates UUID if None)

        Yields:
            The correlation ID

        Example:
            >>> with FlexiAILogger.correlation_context() as corr_id:
            ...     logger.info("Processing request")
            ...     # All logs in this block will have the same correlation ID
        """
        token = correlation_id.set(corr_id or str(uuid.uuid4()))
        try:
            yield correlation_id.get()
        finally:
            correlation_id.reset(token)

    @classmethod
    def mask_sensitive_data(cls, data: Any) -> Any:
        """
        Mask sensitive data in dictionaries, strings, or other objects.

        Args:
            data: Data to mask (dict, str, list, etc.)

        Returns:
            Data with sensitive information masked

        Example:
            >>> masked = FlexiAILogger.mask_sensitive_data({
            ...     "api_key": "sk-1234567890",
            ...     "model": "gpt-4"
            ... })
            >>> print(masked)
            {'api_key': '***MASKED***', 'model': 'gpt-4'}
        """
        if isinstance(data, dict):
            return {
                key: (
                    "***MASKED***" if cls._is_sensitive_key(key) else cls.mask_sensitive_data(value)
                )
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [cls.mask_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            filter_instance = SensitiveDataFilter()
            return filter_instance._mask_sensitive_data(data)
        else:
            return data

    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        """
        Check if a dictionary key contains sensitive data.

        Args:
            key: Dictionary key

        Returns:
            True if the key is sensitive
        """
        sensitive_keys = {
            "api_key",
            "apikey",
            "api-key",
            "token",
            "access_token",
            "secret",
            "password",
            "authorization",
            "auth",
        }
        return key.lower().replace("_", "").replace("-", "") in sensitive_keys


# Convenience function to get the default logger
def get_logger(name: str = "flexiai") -> logging.Logger:
    """
    Get a FlexiAI logger instance.

    Args:
        name: Logger name (default: "flexiai")

    Returns:
        Logger instance

    Example:
        >>> from flexiai.utils.logger import get_logger
        >>> logger = get_logger()
        >>> logger.info("Starting FlexiAI")
    """
    return FlexiAILogger.get_logger(name)
