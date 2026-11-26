"""Application configuration and environment variable management."""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv, set_key


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

# Load environment variables from .env in project root if present.
load_dotenv(dotenv_path=ENV_FILE_PATH, override=False)

ALLOWED_UPLOAD_EXTENSIONS = (".pdf", ".docx", ".txt")
SUPPORTED_PROVIDERS = ("openai", "gemini", "openai_compatible", "offline_demo")

# Weighted dimensions used to compute the 0-100 Requirement Completeness Score.
SCORE_WEIGHTS: Dict[str, int] = {
    "business_goal": 15,
    "functional_scope": 25,
    "user_roles": 15,
    "non_functional": 15,
    "data_and_integrations": 10,
    "timeline_and_budget": 10,
    "success_criteria": 10,
}

DIMENSION_LABELS: Dict[str, str] = {
    "business_goal": "Business Goal & Problem Statement",
    "functional_scope": "Functional Scope & Core Features",
    "user_roles": "Target Users & Personas",
    "non_functional": "Non-Functional & Security Needs",
    "data_and_integrations": "Data Model & Third-Party Integrations",
    "timeline_and_budget": "Timeline, Budget & Constraints",
    "success_criteria": "Success Metrics & Acceptance Criteria",
}


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    app_name: str
    base_dir: Path
    database_path: Path
    exports_dir: Path
    samples_dir: Path
    llm_provider: str
    openai_api_key: str
    openai_model: str
    openai_base_url: str
    gemini_api_key: str
    gemini_model: str
    max_upload_size_mb: int
    min_input_chars: int
    max_input_chars: int
    log_level: str

    def active_model_name(self) -> str:
        """Return the active model identifier for the configured provider."""
        if self.llm_provider == "offline_demo":
            return "heuristic-v1 (no key)"
        if self.llm_provider == "gemini":
            return self.gemini_model
        return self.openai_model

    def is_llm_configured(self) -> bool:
        """Check whether the active LLM provider is ready to execute analyses."""
        if self.llm_provider == "offline_demo":
            return True
        placeholders = {"", "your_openai_api_key_here", "your_gemini_api_key_here"}
        if self.llm_provider == "gemini":
            return self.gemini_api_key.strip() not in placeholders
        if self.llm_provider == "openai_compatible":
            return bool(self.openai_base_url.strip()) and bool(self.openai_api_key.strip())
        return self.openai_api_key.strip() not in placeholders


def _resolve_path(raw_path: str, default_relative: str) -> Path:
    """Resolve a path relative to BASE_DIR when not absolute."""
    candidate = Path(raw_path.strip() or default_relative)
    return candidate if candidate.is_absolute() else (BASE_DIR / candidate)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache application settings from environment variables."""
    raw_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    placeholders = {"", "your_openai_api_key_here", "your_gemini_api_key_here"}

    if raw_provider in SUPPORTED_PROVIDERS:
        provider = raw_provider
    elif openai_key not in placeholders:
        provider = "openai"
    elif gemini_key not in placeholders:
        provider = "gemini"
    else:
        # Default to Offline Smart Mode out of the box when no API key is configured yet.
        provider = "offline_demo"

    max_upload_mb = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    db_path = _resolve_path(os.getenv("DATABASE_PATH", "data/analyzer.db"), "data/analyzer.db")

    return Settings(
        app_name="AI Client Requirement Analyzer",
        base_dir=BASE_DIR,
        database_path=db_path,
        exports_dir=BASE_DIR / "exports",
        samples_dir=BASE_DIR / "data" / "samples",
        llm_provider=provider,
        openai_api_key=openai_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
        gemini_api_key=gemini_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
        max_upload_size_mb=max(1, max_upload_mb),
        min_input_chars=50,
        max_input_chars=60000,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )


def reload_settings() -> Settings:
    """Clear cached settings and reload from environment variables."""
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)
    get_settings.cache_clear()
    return get_settings()


def save_provider_configuration(
    provider: str,
    model_name: str,
    api_key: str = "",
    base_url: str = "",
    persist_to_env: bool = True,
) -> Settings:
    """Update runtime environment variables and optionally persist to local .env file."""
    clean_provider = provider.strip().lower()
    if clean_provider not in SUPPORTED_PROVIDERS:
        clean_provider = "openai"

    updates: Dict[str, str] = {"LLM_PROVIDER": clean_provider}
    clean_model = model_name.strip()
    clean_key = api_key.strip()
    clean_base = base_url.strip()

    if clean_provider == "gemini":
        if clean_model:
            updates["GEMINI_MODEL"] = clean_model
        if clean_key:
            updates["GEMINI_API_KEY"] = clean_key
    elif clean_provider in {"openai", "openai_compatible"}:
        if clean_model:
            updates["OPENAI_MODEL"] = clean_model
        if clean_key:
            updates["OPENAI_API_KEY"] = clean_key
        if clean_provider == "openai_compatible":
            updates["OPENAI_BASE_URL"] = clean_base

    for env_key, env_val in updates.items():
        os.environ[env_key] = env_val

    if persist_to_env:
        if not ENV_FILE_PATH.exists():
            example_path = BASE_DIR / ".env.example"
            if example_path.exists():
                ENV_FILE_PATH.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                ENV_FILE_PATH.touch()
        for env_key, env_val in updates.items():
            set_key(str(ENV_FILE_PATH), env_key, env_val)

    get_settings.cache_clear()
    return get_settings()
