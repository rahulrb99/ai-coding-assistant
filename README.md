# AI Coding Assistant CLI

Command-line AI coding assistant. Autonomous agent with MCP tool integration.

## Setup

```bash
cp .env.example .env
# Edit .env with your API keys (OPENAI_API_KEY or GROQ_API_KEY)

pip install -r requirements.txt
```

## Run

```bash
cd ai_agent
python main.py
```

## Custom RAG Server (run separately)

```bash
cd custom_rag_server
python main.py
```

## Project Structure

- `ai_agent/` — Main assistant (CLI, agent loop, tools, providers, MCP client)
- `custom_rag_server/` — Documentation RAG server (LangChain docs, HyDE)
