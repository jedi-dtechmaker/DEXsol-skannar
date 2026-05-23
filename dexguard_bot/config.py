from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    solana_rpc_url: str
    db_path: str
    request_timeout_seconds: int = 5
    enrichment_timeout_seconds: int = 2
    send_photos: bool = False
    send_typing: bool = False
    deep_enrichment: bool = False
    webhook_url: str = ""
    webhook_path: str = "/telegram/webhook"
    port: int = 8080


def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return Settings(
        telegram_bot_token=token,
        solana_rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com").strip(),
        db_path=os.getenv("DEXGUARD_DB_PATH", "data/dexguard.sqlite3").strip(),
        request_timeout_seconds=int(os.getenv("DEXGUARD_REQUEST_TIMEOUT_SECONDS", "5")),
        enrichment_timeout_seconds=int(os.getenv("DEXGUARD_ENRICHMENT_TIMEOUT_SECONDS", "2")),
        send_photos=_bool_env("DEXGUARD_SEND_PHOTOS", False),
        send_typing=_bool_env("DEXGUARD_SEND_TYPING", False),
        deep_enrichment=_bool_env("DEXGUARD_DEEP_ENRICHMENT", False),
        webhook_url=os.getenv("WEBHOOK_URL", "").strip().rstrip("/"),
        webhook_path=os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip() or "/telegram/webhook",
        port=int(os.getenv("PORT", "8080")),
    )


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
