"""
Config — Person 1
Load from .env via python-dotenv. Provider-agnostic.
"""
from pathlib import Path


def get_settings() -> dict:
    """Load settings from environment. Return dict with MODEL_PROVIDER, MODEL_NAME, etc."""
    # TODO: python-dotenv load_dotenv()
    # TODO: Return dict with required and optional vars
    return {
        "model_provider": "groq",
        "model_name": "llama-3.1-8b-instant",
        "workspace_root": Path("./workspace"),
        "execution_mode": "auto",
    }
