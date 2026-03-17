# AI Coding Assistant CLI — Design Document

## Overview

This document specifies the design for a command-line AI coding assistant with an agentic architecture, similar to Claude Code / Cursor. It combines the implementation plan and final design decisions into a single reference.

---

## 1. Project Goal

Build a command-line AI coding assistant that:

1. Accepts natural language instructions from the developer
2. Understands the local codebase
3. Reads, edits, and creates files
4. Runs shell commands
5. Searches local codebase (direct file read or regex) and retrieves documentation via custom RAG MCP server when needed
6. Improves results using a feedback loop
7. Supports multiple LLM providers
8. Connects to MCP tool servers

**This is NOT a chatbot.** It must behave as an autonomous agent.

---

## 2. Minimum Capabilities Required

| Capability | Example |
|------------|---------|
| Solve coding problems | User provides LeetCode problem → assistant generates optimal solution |
| Generate new problems | User gives DP problems → assistant generates related DP problem |
| Build simple frontends | User asks for Streamlit/Gradio → assistant generates working code |
| Iterative feedback loop | User: "Build streamlit sentiment analyzer" → Agent creates app → User: "Move button below textbox" → Agent updates code |

The system must support continuous improvement.

---

## 3. Architecture Overview

```
User
  ↓
CLI Interface
  ↓
Agent Controller
  ↓
Memory
  ↓
Prompt Builder
  ↓
LLM Provider
  ↓
Tool Registry
  ↓
Tool Executor
  ↓
Local Tools / MCP Tools
  ↓
Results returned to Agent
  ↓
Feedback Loop continues
```

**System Components:**

1. CLI Interface
2. Agent Loop
3. Memory
4. Prompt Builder
5. LLM Provider Layer
6. Tool Registry
7. Tool Executor
8. Tool Layer (local tools + MCP tools)
9. MCP Client
10. Custom MCP RAG Server (documentation)
11. Feedback Loop

---

## 4. Project Structure

```
genaiproject3/
├── main.py
├── cli/
│   └── interface.py
├── agent/
│   ├── agent_loop.py
│   ├── prompt_builder.py
│   └── memory.py
├── providers/
│   ├── base_provider.py
│   ├── openai_provider.py
│   ├── groq_provider.py
│   └── (anthropic_provider.py, ollama_provider.py optional)
├── tools/
│   ├── base.py
│   ├── registry.py
│   ├── executor.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── run_shell.py
│   └── search_codebase.py
├── mcp/
│   └── mcp_client.py
├── config/
│   └── settings.py
└── custom_rag_server/          (separate MCP server; run independently)
    ├── main.py
    ├── indexer.py
    ├── retriever.py
    └── embeddings.py
```

---

## 5. Core Design Decisions

| Decision | Choice |
|----------|--------|
| Workspace size | Small-to-medium (10–200 files) |
| Primary LLM | OpenAI-compatible APIs with function calling |
| OS / paths | `pathlib` for paths, `subprocess` for shell (cross-platform) |
| Conversation history | Session-only (not persisted) |
| MCP | Required; at least one web search + one resource server; agent continues with local tools if servers unavailable |
| File safety | Confirm before overwriting existing files |
| Tool schema | OpenAI JSON function calling format |
| search_codebase | Ripgrep if available, else regex; no RAG for local codebase |
| Memory | Sliding window with summarization when needed |
| Streaming | Only for final responses (not during tool-call parsing) |
| Context control | Truncated history; system prompt always pinned; RAG from custom MCP when called |

---

## 6. Component Specifications

### 6.1 Tool Registry (tools/registry.py)

- **Responsibilities**: Register local and MCP tools; expose JSON schemas to LLM; provide lookup for execution
- **Interface**:
  - `register(tool)` — Register a tool by name
  - `get_tool(name)` — Get tool by name
  - `get_tool_schemas()` — Return JSON schemas for all tools

**Tool interface**: All tools implement `name`, `description`, `schema`, `execute(**kwargs)`.

**Registration flow at startup:**
1. Initialize ToolRegistry
2. Register local tools
3. Connect MCP client
4. Load MCP tools via `mcp_client.load_tools()`
5. Register MCP tools in ToolRegistry

### 6.2 Tool Executor (tools/executor.py)

- **Responsibilities**: Validate tool existence; validate parameters against schema; validate paths within workspace_root; handle SAFE_MODE confirmation; execute tool; format structured result
- **Flow**: Agent → Tool Executor → Tool Registry → Local tool OR MCP tool
- Tool execution must NOT occur directly in the agent loop.

### 6.3 Tool Result Format

- **Success**: `{"status": "success", "tool": "read_file", "output": "..."}`
- **Error**: `{"status": "error", "tool": "read_file", "message": "file not found"}`
- **Tool schema error**: `{"status": "tool_schema_error", "message": "Invalid tool call parameters for <tool>"}` — returned to LLM for self-correction

### 6.4 Prompt Builder (agent/prompt_builder.py)

- Isolate prompt construction
- **Required order**: (1) System instructions, (2) Tool definitions, (3) Conversation history, (4) Current user request
- Handle context truncation
- RAG context injected when agent calls custom RAG MCP tool (on-demand, not automatic)

### 6.5 Memory (agent/memory.py)

- Store conversation history
- Sliding window (`max_messages`)
- Optional: `summarize_old_messages()` when token limit reached

### 6.6 Provider Normalization

- Normalize provider responses to: `{"content": "...", "tool_call": {"name": "...", "arguments": {...}}}`
- Keeps agent loop provider-agnostic

### 6.7 MCP Tool Loading

- MCP client: connect to servers, discover tool schemas, convert MCP tools to internal Tool objects, register in ToolRegistry
- Method: `mcp_client.load_tools()` → `registry.register(tool)`

---

## 7. Tools Specification

### read_file(path)

Read file contents.

### write_file(path, content)

Write content to a file.

### edit_file(path, search_block, replace_block)

- **Behavior**: Replace `search_block` with `replace_block` in the file at `path`
- **Normalized matching**:
  1. Attempt exact match first
  2. If not found, normalize whitespace (strip leading/trailing) and compare
  3. If found via normalized match, apply replacement preserving original whitespace
  4. If still not found, return structured error: `{"status": "error", "message": "search_block not found"}`
- Block-based search/replace; replaces first match only

### run_shell(command)

Execute a shell command.

### search_codebase(query)

- Use **ripgrep** if available; fallback to Python regex if ripgrep unavailable
- Regex/file-based search through local codebase — **do NOT use RAG for local code**
- Significantly improves performance on large repositories

**File tools (Option B)**: Use filesystem MCP when available; fall back to local read_file, write_file, edit_file when MCP unavailable.

---

## 8. MCP Requirements

**Three required servers:**

1. **Official filesystem server** (@modelcontextprotocol/server-filesystem) — read, write, edit files
2. **At least one external resource server**: Tavily (web search) or Context7 (code docs)
3. **Custom MCP RAG server** — LangChain docs, HyDE technique (see Section 10)

Agent includes MCP client even if servers unavailable; falls back to local tools (Option B).

---

## 9. Custom RAG MCP Server

- **Purpose**: Documentation retrieval (LangChain docs)
- **Storage**: Chroma on disk; setup runs once, persists for future sessions
- **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Chunk parameters**: chunk_size=1000, chunk_overlap=200
- **Advanced RAG**: **HyDE (Hypothetical Document Embeddings)** — required
  - Generate hypothetical answer to query using LLM
  - Embed hypothetical answer
  - Retrieve documents similar to hypothetical answer
  - Reference: https://github.com/NirDiamant/RAG_Techniques
- **Flow**: Agent calls tool when needed; retrieved chunks included in prompt
- **Pipeline**: DirectoryLoader/TextLoader → RecursiveCharacterTextSplitter → HuggingFaceEmbeddings → Chroma → Retriever

---

## 10. Context Window Management

- **Fixed order**: (1) System instructions, (2) Tool definitions, (3) Conversation history, (4) Current user request
- **Pinned**: System instructions and tool definitions never truncated
- **Truncation order**: Older conversation history first; then reduce RAG chunks from tool responses if needed

---

## 11. Configuration

- **Loader**: `settings.py` loads env via `python-dotenv`
- **Provider-agnostic**: Load only the API key for selected provider
- **Required env**: `MODEL_PROVIDER` (openai | anthropic | groq | ollama), `MODEL_NAME`
- **Provider-specific keys**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`
- **Optional env**: `TAVILY_API_KEY`, `MCP_TAVILY_URL`, `MCP_CONTEXT7_URL`, `MCP_RAG_SERVER_URL`, `EXECUTION_MODE` (safe | auto), `WORKSPACE_ROOT` (default ./workspace)
- **Overrides**: CLI flags can override configuration

---

## 12. Execution Modes

| Mode | Behavior |
|------|----------|
| **SAFE_MODE** | User confirmation required before write_file, edit_file, run_shell |
| **AUTO_MODE** | All tool calls execute automatically |
| **Read-only tools** (read_file, search_codebase) | Never require confirmation in either mode |

---

## 13. Workspace Root Restriction

- **workspace_root**: Configurable (default `./workspace`); agent cannot modify outside project
- **Enforcement**: Tool Executor validates paths before execution
- Reject read_file, write_file, edit_file, search_codebase for paths outside root
- Reject run_shell if cwd would escape root

---

## 14. Error Handling

- **LLM calls**: Retry up to 3 times with exponential backoff
- **Tool errors**: Return structured responses instead of crashing

---

## 15. Logging

- **Centralized**: Categories AGENT, TOOL, MCP, LLM, ERROR
- **File**: `.logs/agent.log`
- **Example**: `[AGENT] Iteration 2` | `[TOOL] read_file path=app.py`

---

## 16. Implementation Steps (Order)

### Step 1 — CLI Interface

- REPL: continuously accept user input, send prompt to agent, stream responses, display tool execution logs
- Libraries: Typer, Rich

### Step 2 — Agent Loop

- ReAct pattern; MAX_ITERATIONS = 10
- Flow: User input → Memory update → Prompt Builder → LLM Provider → Tool call? → Tool Executor → Result → Memory update → Loop
- Tool execution delegated to Tool Executor (not in agent loop)

### Step 3 — Tool Layer

Implement read_file, write_file, edit_file, run_shell, search_codebase with structured outputs.

### Step 4 — Provider Abstraction

- Base: `LLMProvider.generate(prompt)`
- Implement: OpenAI, Anthropic, Ollama, Groq

### Step 5 — MCP Client

Connect to filesystem, Tavily/Context7, custom RAG servers; load tools dynamically.

### Step 6 — Custom MCP RAG Server

Build RAG server with HyDE; index LangChain docs; expose tools to MCP client.

### Step 7 — Feedback Loop

Store conversation history; support iterative refinement; agent reads file after edit to verify success.

### Step 8 — Tool Execution Confirmation Mode

SAFE_MODE / AUTO_MODE selectable via config or CLI.

### Step 9 — Streaming Output

Stream agent responses progressively.

---

## 17. Edit Verification

After an edit operation, the agent must read the file again to verify the modification was applied successfully before continuing the loop.

---

## 18. Removed Components

- **planner.py**: ReAct plans via LLM; separate planner unnecessary

---

## 19. Demo Scenarios

1. Solving LeetCode problems
2. Generating new dynamic programming problems
3. Creating Streamlit apps
4. Fixing code based on feedback

---

## 20. Bottlenecks

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| Custom RAG server setup | Low–Medium | One-time index; document setup clearly |
| Sequential tool execution | Medium | ReAct is inherently sequential; acceptable for MVP |
| Embedding generation | Low | LangChain docs → manageable; CPU sufficient |
| Single-threaded design | Low | Acceptable for CLI; async deferred |
| Prompt size growth | Addressed | Truncated history + sliding window; RAG on-demand |

---

## 21. Implementation Guidelines

- Write clean modular Python code
- Use type hints
- Add logging for: tool usage, agent reasoning, execution steps
- Implement full project step by step; explain each module before writing code; do not skip steps

---

## Status

All design decisions are finalized. The plan is ready for implementation.
