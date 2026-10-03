import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def is_placeholder_value(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip()
    if not normalized:
        return True
    lowered = normalized.lower()
    placeholder_prefixes = (
        "your_",
        "replace_",
        "example",
        "sample",
        "placeholder",
        "changeme",
        "demo",
    )
    return lowered in {"your_api_key", "your_groq_api_key", "your_tavily_api_key"} or any(
        lowered.startswith(prefix) for prefix in placeholder_prefixes
    )


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_model: str
    search_api_key: str
    output_dir: Path
    groq_timeout_seconds: float
    search_timeout_seconds: float


@lru_cache

def get_settings() -> Settings:
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
        search_api_key=os.getenv("SEARCH_API_KEY", "").strip(),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
        groq_timeout_seconds=float(os.getenv("GROQ_TIMEOUT_SECONDS", "60")),
        search_timeout_seconds=float(os.getenv("SEARCH_TIMEOUT_SECONDS", "20")),
    )
