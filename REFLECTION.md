# Reflection — Vertex (AI Coding Assistant CLI)

## Project summary

Vertex is a command-line AI coding assistant with an agentic (ReAct-style) loop. The user gives a natural language task, Vertex decides whether to call tools (read/edit/write files, run shell, search codebase, and MCP tools), executes them, and iterates until it can return a final answer. The goal was to build something closer to an autonomous “coding agent” than a chatbot, while keeping the UX usable in a terminal and the system robust under real constraints (Windows console quirks, timeouts, and token/cost limits).

## Team contributions (by contract ownership)

We structured the project around “frozen contracts” to allow parallel implementation with minimal coupling (see `CONTRACTS.md`).

- **Rahul (integration + agent UX)**: wired the end-to-end CLI experience (REPL + streaming output), implemented/extended the ReAct agent loop, added Plan Mode confirmation workflow, integrated MCP tool loading and startup reporting, and drove robustness improvements.
- **Dhruti (tooling layer)**: defined the tool interface and executor contract, including schema validation and SAFE mode confirmation behaviors for repo-changing tools.
- **Maya (provider layer)**: implemented provider abstraction/normalization so the agent loop is provider-agnostic, including function-calling compatible responses.
- **Thanmay (MCP integration)**: contributed MCP server/tool integration work, enabling external tool servers to be loaded and used alongside local tools.
- **Mike (memory + prompt/RAG components)**: implemented prompt building and memory contracts, and the custom MCP RAG server components used for documentation retrieval.

This contract-first split reduced integration risk: the agent loop and CLI could be built early with mocks, and later swapped onto real implementations as each component landed.

## Key design decisions and why

### Agent loop: ReAct with tool delegation

We chose a ReAct-style loop because the assistant needs to interleave reasoning with actions (tools), rather than answer in one shot. A strict separation is maintained:

- The **agent loop** decides *what to do next* (tool call vs final answer).
- The **tool executor** is the only component that actually runs repo-changing operations (edit/write/shell), including SAFE-mode confirmations and parameter/schema validation.

This separation made it easier to test the agent logic independently and reduced the chance of accidental side effects.

### Plan Mode (automatic, confirmation-gated)

A key improvement for safety and rubric alignment was **automatic Plan Mode** for *repo-changing, multi-step* prompts:

- Vertex classifies whether a task requires a plan (with a cheap keyword prefilter to avoid unnecessary calls, and then an LLM classifier only when needed).
- If triggered, it generates a short actionable plan and **asks for approval** before making changes.
- One re-plan iteration is supported when the user rejects the plan and provides feedback.

This improves user trust and makes the agent’s actions more auditable, without turning the CLI into a verbose “planner-only” tool.

### MCP integration for extensibility

We integrated MCP to treat external capabilities as tools the agent can call dynamically:

- **Filesystem MCP** for standard file operations (when available).
- **Web search MCP** (e.g., Tavily) for up-to-date info.
- **Custom RAG MCP server** for domain documentation retrieval.

We also made MCP loading **best-effort**: if servers are unavailable/slow, Vertex still works with local tools.

### Token / cost management as a first-class constraint

In practice, an agent can become expensive fast due to multi-iteration loops and large tool outputs. We implemented several controls:

- **Tool-output truncation** before saving to memory (limits both characters and lines).
- **Short sliding history window** to prevent context bloat.
- **Per-task usage reporting** (prompt/completion/total tokens) and **session-wide total token tracking**.

This kept the system responsive and made costs visible during demos.

## Advanced RAG: HyDE + Chroma (custom MCP server)

We implemented a custom MCP RAG server focused on documentation retrieval, using:

- **ChromaDB** as the persistent vector store (on disk).
- **HuggingFace embeddings** (`sentence-transformers/all-MiniLM-L6-v2`) for a lightweight CPU-friendly embedder.
- **HyDE (Hypothetical Document Embeddings)** to improve retrieval: we generate a hypothetical answer (when possible) and embed that instead of embedding the raw query.

### Observations / trade-offs

From testing, **HyDE + Chroma improved retrieval quality and reduced hallucinations** on documentation questions (especially when the query was vague or the user used slightly wrong terminology). However, the trade-offs were clear:

- **Latency**: extra LLM call(s) and retrieval steps increase end-to-end time.
- **Cost**: more tokens and computation, especially if HyDE uses a hosted LLM.
- **Complexity**: more moving parts (indexing, embedding model versioning, dimension consistency, and server startup behavior).

In contrast, **no-RAG** answers are faster and cheaper but noticeably less reliable for domain-specific “what does this API do” questions where exact doc wording matters.

## LLM provider comparison (Groq vs OpenAI vs Ollama)

We supported multiple providers to compare speed/cost/reliability and to keep the architecture provider-agnostic.

- **Groq**: consistently the fastest with very low latency, ideal for interactive CLI use. Quality can be slightly less consistent depending on the specific backend model; tool-call formatting can also vary more.
- **OpenAI**: best overall balance of quality and reliability, with strong reasoning and fewer failures. Trade-offs are higher cost and slower responses relative to Groq.
- **Ollama (local)**: most cost-effective and privacy-friendly since it runs locally. Trade-offs are significantly slower throughput and quality depending heavily on the chosen model and the laptop’s available RAM/CPU.

In practice, “best provider” depends on the task: rapid iteration and UX demos benefit from Groq, while correctness-critical refactors benefit from OpenAI, and offline/private scenarios benefit from Ollama.

## Engineering challenges and what we changed

### Windows terminal constraints

On Windows, some terminals default to encodings that can’t print certain Unicode glyphs cleanly. We avoided “fancy” symbols in terminal output and ensured output remains readable and crash-free across typical Windows consoles.

### Timeouts and long-running commands

Agents often try to run servers/watchers (Streamlit, Flask, etc.) in a way that blocks or times out. We adjusted execution guidance and shell handling to avoid hanging the CLI and to make tool execution safer.

### Tool-call robustness across providers

Not all models emit perfect function-calling output. We added fallback parsing for tool calls printed as text, including a specific malformed pattern observed from local/Ollama-style outputs (`{(name):..., (parameters):...}`), so the agent can still act rather than failing silently.

## What we demonstrated (end-to-end)

In demos we focused on full “agent” behavior rather than isolated functions:

- A **multi-step repo-changing task** that triggered Plan Mode and executed tools after approval.
- Documentation queries using the **custom RAG MCP tool** (HyDE + Chroma) for grounded answers.
- Use of **web search MCP** for up-to-date information when needed.
- Use of **filesystem tools** for reading/editing and verifying changes.

## Lessons learned

- **Contracts prevent integration stalls**: freezing interface contracts early let us parallelize work and reduce “merge-week” failures.
- **UX is part of correctness**: streaming output, clean tool logs, and plan confirmation materially improved user trust and usability.
- **RAG helps, but only when targeted**: “always-on RAG” would be too slow/costly; on-demand tool calls plus HyDE provided a practical balance.
- **Cost controls must be engineered**: without truncation/history limits and usage reporting, agent loops can become unpredictably expensive.

## Future improvements

If we extended Vertex beyond the class project scope:

- **More systematic evaluation**: a small benchmark suite comparing providers and RAG/no-RAG for accuracy and latency.
- **Better planning enforcement**: optionally “execute step-by-step” with plan checkpoints for complex refactors.
- **Richer memory**: summarization of older context rather than hard truncation.
- **Smarter tool routing**: learned tool selection and better handling of ambiguous tool schemas.

