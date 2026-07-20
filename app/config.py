"""
Application configuration.

Variable resolution order (highest → lowest priority):
  1. Real environment variables (OS / shell exports)
  2. credentials.env  — local secrets file, never committed  ← wins over .env
  3. .env             — shared defaults, safe to commit
  4. Field defaults below

The credentials file is intended for local developer overrides and CI/CD
secret injection.  It is gitignored so secrets are never accidentally
committed.  Copy .env.example to credentials.env to get started:

    copy .env.example credentials.env   # Windows
    cp  .env.example  credentials.env   # Unix
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent

# Build the env_file list; pydantic-settings applies files left-to-right,
# with later files taking lower priority.  We put credentials.env last so
# its values win (pydantic-settings merges in order, last writer wins for
# the same key — see note below).
#
# NOTE: pydantic-settings v2 env_file priority: the *first* file in the list
# has the *lowest* priority; later files override earlier ones.  To make
# credentials.env take precedence over .env we list .env first.
_env_files: list[Path] = []
_credentials = _BASE_DIR / "credentials.env"
_dotenv = _BASE_DIR / ".env"

if _dotenv.exists():
    _env_files.append(_dotenv)        # base defaults (lower priority)
if _credentials.exists():
    _env_files.append(_credentials)   # local secrets (higher priority)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files or None,   # None → skip file loading entirely
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # App
    app_env: str = "development"
    app_title: str = "Cost Allocations API"
    app_version: str = "0.1.0"


settings = Settings()
