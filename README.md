# AI Coding Assistant CLI
# Vertex — AI Coding Assistant CLI
Command-line AI coding assistant. Autonomous agent with MCP tool integration.
An autonomous command-line coding assistant powered by an LLM. Reads, writes, and edits files, runs shell commands, searches your codebase, and retrieves web documentation — all via a ReAct agent loop with MCP tool integration.
---
## Features
- **Agentic loop** — ReAct pattern with up to 10 tool-calling iterations per task
- **Streaming responses** — final answers stream token-by-token in the terminal
- **Multiple LLM providers** — Groq, OpenAI, Ollama (local)
- **MCP tool servers** — Filesystem, Tavily web search, Custom RAG (LangChain docs)
- **Safe / Auto mode** — confirm before write/shell commands or let the agent run freely
- **Session memory** — conversation history persists across restarts
- **`@file` mentions** — type `fix @app.py` to inject a file into your prompt
- **Token usage** — shows prompt + completion tokens after every response
---
## Requirements
- Python 3.10+
- Node.js 18+ and `npx` (required for MCP filesystem and Tavily servers)
- A Groq or OpenAI API key (free Groq tier works)
**Check Node.js:**
```bash
node --version   # should be 18+
npx --version
```
Install Node.js from https://nodejs.org if not installed.
---
**1. Clone and install dependencies**
```bash
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY or GROQ_API_KEY)
git clone https://github.com/rahulrb99/ai-coding-assistant.git
cd ai-coding-assistant
pip install -r requirements.txt
## Run
**2. Configure environment**
```bash
cp .env.example .env
```
Edit `.env` and fill in your API key:
```env
MODEL_PROVIDER=groq
MODEL_NAME=llama-3.3-70b-versatile
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here   # optional but recommended for web search
WORKSPACE_ROOT=.
```
Get a free Groq API key at https://console.groq.com  
Get a free Tavily API key at https://tavily.com
**3. Run**
```bash
cd ai_agent
python main.py
## Custom RAG Server (run separately)
---
## Usage
On first launch, choose an execution mode:
| Mode | Behaviour |
|------|-----------|
| `auto` | Agent executes all tools automatically |
| `safe` | Agent asks for confirmation before write/shell commands |
Your choice is saved — subsequent runs skip this prompt.
### Example prompts
```
> create a streamlit sentiment analyser app
> fix the bug in @app.py
> what is the time complexity of quicksort?
> search the web for the latest LangChain release
> write a Python function that reverses a linked list
> add error handling to @tools/run_shell.py
```
### REPL commands
| Command | Action |
|---------|--------|
| `/help` | Show all commands and loaded tools |
| `set mode safe` | Switch to safe mode |
| `set mode auto` | Switch to auto mode |
| `exit` / `quit` | Exit the assistant |
---
## LLM Providers
### Groq (default, free tier)
```env
MODEL_PROVIDER=groq
MODEL_NAME=llama-3.3-70b-versatile
GROQ_API_KEY=your_key
```
### OpenAI
```env
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=your_key
```
### Ollama (local, no API key)
```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.2
ollama serve
```
```env
MODEL_PROVIDER=ollama
MODEL_NAME=llama3.2
```
---
## MCP Servers
Three MCP servers load automatically at startup:
| Server | Purpose | Requirement |
|--------|---------|-------------|
| `filesystem` | Read/write/list files | Node.js + npx |
| `tavily` | Web search & research | `TAVILY_API_KEY` in `.env` |
| `custom_rag` | LangChain docs retrieval (HyDE) | See below |
### Custom RAG Server setup (one-time)
```bash
# 1. Download LangChain docs into langchain_docs/ folder
#    (copy .md files from https://github.com/langchain-ai/langchain/tree/master/docs/docs)
# 2. Index the docs (runs once, saves to chroma_db/)
python -m custom_rag_server.main
# Both langchain_docs/ and chroma_db/ are gitignored — local only
```
---
## Running Tests
```bash
cd custom_rag_server
python main.py
pip install pytest
pytest tests/test_person1.py -v
```
Expected: **27 passed**
---
- `ai_agent/` — Main assistant (CLI, agent loop, tools, providers, MCP client)
- `custom_rag_server/` — Documentation RAG server (LangChain docs, HyDE)
```
├── main.py                  # Entry point — wires all components
├── agent/
│   ├── agent_loop.py        # ReAct loop (Person 1)
│   ├── memory.py            # Conversation history with persistence (Person 5)
│   └── prompt_builder.py    # Assembles LLM messages (Person 5)
├── cli/
│   └── interface.py         # Rich REPL, streaming display (Person 1)
├── config/
│   └── settings.py          # Loads .env configuration (Person 1)
├── providers/
│   ├── base_provider.py     # Abstract LLM interface
│   ├── groq_provider.py     # Groq API (Person 3)
│   ├── openai_provider.py   # OpenAI API (Person 3)
│   └── ollama_provider.py   # Ollama local (Person 3)
├── tools/
│   ├── registry.py          # Tool registration and schema export (Person 2)
│   ├── executor.py          # Validation, safe mode, execution (Person 2)
│   ├── read_file.py         # (Person 2)
│   ├── write_file.py        # (Person 2)
│   ├── edit_file.py         # (Person 2)
│   ├── run_shell.py         # (Person 2)
│   └── search_codebase.py   # ripgrep / regex search (Person 2)
├── mcp/
│   └── mcp_client.py        # MCP server connections and tool loading (Person 4)
├── custom_rag_server/
│   ├── main.py              # MCP server entrypoint (Person 5)
│   ├── indexer.py           # Document ingestion → Chroma (Person 5)
│   ├── retriever.py         # HyDE retrieval (Person 5)
│   └── embeddings.py        # sentence-transformers embeddings (Person 5)
├── tests/
│   └── test_person1.py      # Unit tests (27 tests)
├── .env.example             # Environment variable template
├── design_document.md       # Architecture and design decisions
└── CONTRACTS.md             # Cross-person interface contracts
```
---
## Troubleshooting
**`ModuleNotFoundError: No module named 'mcp'`**
```bash
pip install mcp
```
**`npx: command not found`**  
Install Node.js from https://nodejs.org
**Groq rate limit (429)**  
Free tier: 100k tokens/day. Wait for reset or use `MODEL_PROVIDER=openai`.
**Agent stuck / repeating tool calls**  
The loop stops after 10 iterations automatically. Try rephrasing the task.
