# Vertex ΓÇö Frozen Contracts

These 5 contracts are fixed before implementation. They eliminate cross-person dependencies.

---

## Contract 1 ΓÇö Tool Interface (Person 2)

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

## Contract 2 ΓÇö Tool Executor API (Person 2)

**Defined in:** `tools/executor.py`

**Person 1 calls:**
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

## Contract 3 ΓÇö Provider Interface (Person 3)

**Defined in:** `providers/base_provider.py`

**Person 1 calls:**
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

## Contract 4 ΓÇö Prompt Builder (Person 5)

**Defined in:** `agent/prompt_builder.py`

**Person 1 calls:**
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

## Contract 5 ΓÇö Memory Interface (Person 5)

**Defined in:** `agent/memory.py`

**Person 1 calls:**
```python
memory.add_user_message(content)
memory.add_assistant_message(content)
memory.get_history() -> List[dict]
```

---

## Parallel Work with Mocks

Person 1 can implement the Agent Loop using mocks before others finish:

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
