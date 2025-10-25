# Anthropic Claude API Research

## Authentication
- Uses `x-api-key` header with API key
- Format: `x-api-key: sk-ant-...`
- Also accepts `anthropic-version` header (e.g., "2023-06-01")

## Available Models (as of 2025)
- `claude-3-opus-20240229` - Most capable, best for complex tasks
- `claude-3-sonnet-20240229` - Balanced performance and speed
- `claude-3-haiku-20240307` - Fastest, most compact
- `claude-3-5-sonnet-20241022` - Latest Sonnet model
- `claude-3-5-haiku-20241022` - Latest Haiku model

## Messages API Structure

### Request Format
```python
{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,  # REQUIRED
    "system": "You are a helpful assistant",  # Optional, separate from messages
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ],
    "temperature": 0.7,  # Optional, 0-1
    "top_p": 0.9,  # Optional
    "top_k": 40,  # Optional, Claude-specific
    "stop_sequences": ["END"],  # Optional
    "stream": false  # Optional
}
```

### Key Differences from OpenAI
1. **System messages are separate** - not part of messages array
2. **max_tokens is REQUIRED** - no default value
3. **No consecutive messages with same role** - must alternate user/assistant
4. **top_k parameter** - Claude-specific (not in OpenAI)
5. **stop_sequences** instead of "stop"

### Response Format
```python
{
    "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "Hello! How can I help you today?"
        }
    ],
    "model": "claude-3-5-sonnet-20241022",
    "stop_reason": "end_turn",  # or "max_tokens", "stop_sequence"
    "stop_sequence": null,
    "usage": {
        "input_tokens": 10,
        "output_tokens": 25
    }
}
```

## Stop Reasons
- `end_turn` → maps to "stop"
- `max_tokens` → maps to "length"
- `stop_sequence` → maps to "stop"
- `tool_use` → maps to "tool_calls" (if using tools)

## Error Handling

### Error Types
```python
from anthropic import (
    APIError,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
)
```

### Status Codes
- `400` - Bad Request (invalid parameters)
- `401` - Authentication failed
- `403` - Permission denied
- `404` - Resource not found
- `429` - Rate limit exceeded
- `500` - Internal server error
- `529` - Overloaded

## Rate Limits
- Varies by model and plan
- Claude Opus: Lower rate limits
- Claude Sonnet: Medium rate limits
- Claude Haiku: Higher rate limits
- Headers include: `anthropic-ratelimit-requests-limit`, `anthropic-ratelimit-requests-remaining`

## Streaming
```python
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

## Tool Use (Function Calling)
Claude supports tools with a different format than OpenAI:
```python
{
    "tools": [
        {
            "name": "get_weather",
            "description": "Get weather for a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    ]
}
```

## Content Blocks
Claude can return multiple content blocks:
```python
{
    "content": [
        {"type": "text", "text": "Here's the weather:"},
        {"type": "tool_use", "id": "toolu_123", "name": "get_weather", "input": {"location": "SF"}}
    ]
}
```

## Implementation Notes for FlexiAI

### ClaudeRequestNormalizer
1. Extract system messages from `messages` array
2. Put system content in `system` parameter
3. Ensure `max_tokens` is always set (default: 4096)
4. Keep only user/assistant messages in `messages`
5. Validate no consecutive same-role messages
6. Map `stop` to `stop_sequences`

### ClaudeResponseNormalizer
1. Extract text from `content[0].text` (or concatenate multiple blocks)
2. Map `usage.input_tokens` → `prompt_tokens`
3. Map `usage.output_tokens` → `completion_tokens`
4. Map `stop_reason` to unified format
5. Handle multiple content blocks if present

### ClaudeProvider
1. Use `anthropic.Anthropic(api_key=...)`
2. Call `client.messages.create(...)`
3. Handle all Claude-specific errors
4. Implement retry logic for rate limits
5. Support streaming with `client.messages.stream()`
6. Health check: Simple message request

## Migration from OpenAI to Claude
- System messages need extraction
- Must set max_tokens
- top_k is Claude-specific (ignore for other providers)
- Response structure is different (content array vs single text)
