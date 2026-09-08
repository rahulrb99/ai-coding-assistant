# Vertex — Frozen Contracts

These 5 contracts are fixed before implementation. They eliminate cross-person dependencies.

---

## Contract 1 — Tool Interface

**Defined in:** `tools/base.py`

```python
class Tool:
    name: str
    description: str
    schema: dict

    def execute(self, **kwargs) -> dict:
        pass
```

**Return format (never change):**
```python
# Success
{"status": "success", "tool": "read_file", "output": "..."}

# Error
{"status": "error", "tool": "read_file", "message": "..."}
```

---

## Contract 2 — Tool Executor API

**Defined in:** `tools/executor.py`

**Caller:**
```python
executor.execute(tool_name: str, arguments: dict) -> dict
```

**Returns:**
```python
# Success
{"status": "success", "tool": "...", "output": "..."}

# Error
{"status": "error", "tool": "...", "message": "..."}

# Schema validation failure
{"status": "tool_schema_error", "message": "Invalid tool call parameters for <tool>"}
```

---

## Contract 3 — Provider Interface

**Defined in:** `providers/base_provider.py`

**Caller:**
```python
provider.generate(messages: List[dict], tools: List[dict]) -> dict
```

**Returns (normalized, one tool call per iteration):**
```python
{
    "content": str | None,
    "tool_call": {"name": str, "arguments": dict} | None
}
```

---

## Contract 4 — Prompt Builder

**Defined in:** `agent/prompt_builder.py`

**Caller:**
```python
prompt_builder.build(
    system_prompt: str,
    tools: List[dict],
    history: List[dict],
    user_input: str
) -> List[dict]  # messages in OpenAI chat format
```

**Returns:** `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]`

---

## Contract 5 — Memory Interface

**Defined in:** `agent/memory.py`

**Caller:**
```python
memory.add_user_message(content)
memory.add_assistant_message(content)
memory.get_history() -> List[dict]
```

---

## Parallel Work with Mocks

The agent loop can be implemented against mocks before other layers land:

```python
class MockProvider:
    def generate(self, messages, tools):
        return {"content": "hello", "tool_call": None}

class MockExecutor:
    def execute(self, tool_name, arguments):
        return {"status": "success", "tool": tool_name, "output": "ok"}

class MockMemory:
    def add_user_message(self, content): ...
    def add_assistant_message(self, content): ...
    def get_history(self): return []
```
