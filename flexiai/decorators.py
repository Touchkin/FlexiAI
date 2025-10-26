"""
FlexiAI decorators for simplified API integration.

This module provides decorator-based APIs for easy integration of FlexiAI
into existing functions. The decorators automatically handle API calls,
failover, and response extraction.

Example:
    >>> from flexiai import FlexiAI
    >>> from flexiai.decorators import flexiai_chat
    >>>
    >>> FlexiAI.set_global_config({
    ...     "providers": [
    ...         {"name": "openai", "api_key": "sk-...", "priority": 1}  # pragma: allowlist secret
    ...     ]
    ... })
    >>>
    >>> @flexiai_chat
    ... def ask_question(question: str) -> str:
    ...     pass
    >>>
    >>> answer = ask_question("What is Python?")
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from flexiai.models import FlexiAIConfig

logger = logging.getLogger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Global FlexiAI configuration
_global_config: Optional[Union[Dict, FlexiAIConfig]] = None
_global_client = None


def set_global_config(config: Union[Dict, FlexiAIConfig]) -> None:
    """
    Set global FlexiAI configuration for decorators.

    This allows decorators to use a shared configuration without
    needing to pass a FlexiAI instance explicitly.

    Args:
        config: FlexiAI configuration dict or FlexiAIConfig object

    Example:
        >>> from flexiai import FlexiAI
        >>> from flexiai.decorators import set_global_config
        >>>
        >>> set_global_config({
        ...     "providers": [
        ...         {
        ...             "name": "openai",
        ...             "api_key": "sk-...",  # pragma: allowlist secret
        ...             "priority": 1,
        ...         }
        ...     ]
        ... })
    """
    global _global_config, _global_client
    _global_config = config
    _global_client = None  # Reset client to force recreation
    logger.info("Global FlexiAI configuration set")


def get_global_client():
    """
    Get or create the global FlexiAI client.

    Returns:
        FlexiAI: Global FlexiAI client instance

    Raises:
        RuntimeError: If global config is not set
    """
    global _global_client

    if _global_client is None:
        if _global_config is None:
            raise RuntimeError(
                "Global FlexiAI config not set. "
                "Call FlexiAI.set_global_config() or set_global_config() first."
            )

        # Import here to avoid circular imports
        from flexiai import FlexiAI

        if isinstance(_global_config, dict):
            from flexiai.models import FlexiAIConfig

            _global_client = FlexiAI(FlexiAIConfig(**_global_config))
        else:
            _global_client = FlexiAI(_global_config)

    return _global_client


def _extract_message_parameter(func: Callable, args: tuple, kwargs: dict) -> Union[str, List[Dict]]:
    """
    Extract the message parameter from function arguments.

    Analyzes the function signature and extracts the parameter that
    should be used as the user message or messages list.

    Args:
        func: The decorated function
        args: Positional arguments passed to the function
        kwargs: Keyword arguments passed to the function

    Returns:
        str or List[Dict]: The message content or messages list

    Raises:
        ValueError: If no suitable message parameter is found
    """
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Try to get 'messages' parameter first
    if "messages" in kwargs:
        return kwargs["messages"]

    # Try to get first string parameter
    if args:
        # Use the first positional argument
        return args[0]

    # Check for keyword arguments
    for param in params:
        if param.name in kwargs:
            return kwargs[param.name]

    raise ValueError(
        f"Could not extract message parameter from function {func.__name__}. "
        "Function must have at least one parameter for the user message."
    )


def _construct_messages(
    user_input: Union[str, List[Dict]], system_message: Optional[str] = None
) -> List[Dict]:
    """
    Construct messages list for FlexiAI.

    Args:
        user_input: User message string or messages list
        system_message: Optional system message to prepend

    Returns:
        List[Dict]: Properly formatted messages list
    """
    messages = []

    # Add system message if provided
    if system_message:
        messages.append({"role": "system", "content": system_message})

    # Add user input
    if isinstance(user_input, str):
        messages.append({"role": "user", "content": user_input})
    elif isinstance(user_input, list):
        messages.extend(user_input)
    else:
        raise ValueError(
            f"Invalid user_input type: {type(user_input)}. " "Expected str or List[Dict]"
        )

    return messages


def flexiai_chat(
    func: Optional[F] = None,
    *,
    system_message: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model_preference: Optional[List[str]] = None,
    provider: Optional[str] = None,
    fallback: bool = True,
    stream: bool = False,
    retry_attempts: Optional[int] = None,
    client: Optional[Any] = None,
    **kwargs: Any,
) -> Union[F, Callable[[F], F]]:
    """Wrap function with FlexiAI chat completion decorator.

    The decorated function should take a string parameter (user message) or
    a List[Dict] of messages, and return a string (AI response).

    Args:
        func: Function to decorate (auto-filled when used without parentheses)
        system_message: System message for the AI
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate
        model_preference: List of models in preference order (not yet implemented)
        provider: Force specific provider (disables failover if set)
        fallback: Enable automatic failover (default: True)
        stream: Enable streaming responses (returns generator)
        retry_attempts: Number of retry attempts (not yet implemented)
        client: Specific FlexiAI instance to use (instead of global)
        **kwargs: Additional parameters passed to chat_completion

    Returns:
        Decorated function or decorator

    Example:
        >>> # Simple usage with global config
        >>> @flexiai_chat
        ... def ask_ai(question: str) -> str:
        ...     pass
        >>>
        >>> # With parameters
        >>> @flexiai_chat(temperature=0.7, max_tokens=500)
        ... def creative_writer(prompt: str) -> str:
        ...     pass
        >>>
        >>> # With system message
        >>> @flexiai_chat(system_message="You are a helpful Python expert")
        ... def code_helper(question: str) -> str:
        ...     pass
        >>>
        >>> # Async function
        >>> @flexiai_chat
        ... async def async_ask(question: str) -> str:
        ...     pass
    """

    def decorator(f: F) -> F:
        # Check if function is async
        is_async = asyncio.iscoroutinefunction(f)

        if is_async:
            # Async wrapper
            @functools.wraps(f)
            async def async_wrapper(*args: Any, **func_kwargs: Any) -> Any:
                # Get FlexiAI client
                flexiai_client = client if client else get_global_client()

                # Extract message parameter
                user_input = _extract_message_parameter(f, args, func_kwargs)

                # Construct messages
                messages = _construct_messages(user_input, system_message)

                # Build request parameters
                request_params = {"messages": messages}

                if temperature is not None:
                    request_params["temperature"] = temperature
                if max_tokens is not None:
                    request_params["max_tokens"] = max_tokens
                if provider is not None:
                    request_params["provider"] = provider
                if stream is not None:
                    request_params["stream"] = stream

                # Add any additional kwargs
                request_params.update(kwargs)

                # Make the API call
                # Note: Async support will be implemented in future phase
                # For now, run sync version in executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, lambda: flexiai_client.chat_completion(**request_params)
                )

                # Extract and return text content
                if stream:
                    # TODO: Handle streaming in future phase
                    return response
                else:
                    return response.content if hasattr(response, "content") else str(response)

            return async_wrapper  # type: ignore

        else:
            # Sync wrapper
            @functools.wraps(f)
            def sync_wrapper(*args: Any, **func_kwargs: Any) -> Any:
                # Get FlexiAI client
                flexiai_client = client if client else get_global_client()

                # Extract message parameter
                user_input = _extract_message_parameter(f, args, func_kwargs)

                # Construct messages
                messages = _construct_messages(user_input, system_message)

                # Build request parameters
                request_params = {"messages": messages}

                if temperature is not None:
                    request_params["temperature"] = temperature
                if max_tokens is not None:
                    request_params["max_tokens"] = max_tokens
                if provider is not None:
                    request_params["provider"] = provider
                if stream is not None:
                    request_params["stream"] = stream

                # Add any additional kwargs
                request_params.update(kwargs)

                # Make the API call
                response = flexiai_client.chat_completion(**request_params)

                # Extract and return text content
                if stream:
                    # TODO: Handle streaming in future phase
                    return response
                else:
                    return response.content if hasattr(response, "content") else str(response)

            return sync_wrapper  # type: ignore

    # Handle both @decorator and @decorator() syntax
    if func is None:
        # Called with parameters: @decorator(param=value)
        return decorator
    else:
        # Called without parameters: @decorator
        return decorator(func)


# Alias for backward compatibility
flexiai = flexiai_chat
