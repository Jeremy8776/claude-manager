---
name: Claude API
description: Anthropic Claude API integration, tool use, prompt caching
triggers: [anthropic, claude, API, SDK, tool use, prompt caching, messages, stream]
---

# Claude API

## Tool Use Pattern

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"]
        }
    }],
    messages=[{"role": "user", "content": "What's the weather in London?"}]
)
```

## Agent Loop

Check `response.stop_reason` for `"tool_use"`. When tools are requested, execute the function, add tool_result, and continue:

```python
while response.stop_reason == "tool_use":
    # Execute tool, add result
    messages.append({"role": "user", "content": tool_result})
    response = client.messages.create(model=model, messages=messages, tools=tools)
```

## Prompt Caching (4.6+)

Use `cache_control = {"type": "ephemeral"}` on system messages and tools to reduce costs:

```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
    tools=tools_with_cache,
    messages=messages,
)
```

Cache hits shown via `usage.cache_read_input_tokens` and `usage.cache_creation_input_tokens`.
