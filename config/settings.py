"""
Config — Person 1
Load from .env via python-dotenv. Provider-agnostic.
"""
import os
from pathlib import Path

from dotenv import load_dotenv


def get_settings() -> dict:
    """
    Load settings from .env file and environment variables.
    Returns a dict with all configuration needed to run the agent.
    Raises ValueError if required variables are missing.
    """
    load_dotenv()

    model_provider = os.getenv("MODEL_PROVIDER", "").strip()
    if not model_provider:
        raise ValueError("MODEL_PROVIDER is required in .env (e.g. openai or groq)")

    model_name = os.getenv("MODEL_NAME", "").strip()
    if not model_name:
        raise ValueError("MODEL_NAME is required in .env")

    # Load only the API key for the selected provider
    api_key: str | None = None
    if model_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    elif model_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip() or None

    workspace_root = Path(os.getenv("WORKSPACE_ROOT", "./workspace"))
    execution_mode = os.getenv("EXECUTION_MODE", "auto").strip().lower()
    if execution_mode not in {"safe", "auto"}:
        execution_mode = "auto"

    return {
        "model_provider": model_provider,
        "model_name": model_name,
        "api_key": api_key,
        "workspace_root": workspace_root,
        "execution_mode": execution_mode,
        # MCP server URLs (optional — agent works without them using local tools)
        "mcp_tavily_url": os.getenv("MCP_TAVILY_URL", "").strip() or None,
        "mcp_context7_url": os.getenv("MCP_CONTEXT7_URL", "").strip() or None,
        "mcp_rag_server_url": os.getenv("MCP_RAG_SERVER_URL", "").strip() or None,
        # API keys for external MCP services
        "tavily_api_key": os.getenv("TAVILY_API_KEY", "").strip() or None,
    }
