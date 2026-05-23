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
    request_timeout_seconds: int = 10
    enrichment_timeout_seconds: int = 4


def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return Settings(
        telegram_bot_token=token,
        solana_rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com").strip(),
        db_path=os.getenv("DEXGUARD_DB_PATH", "data/dexguard.sqlite3").strip(),
        request_timeout_seconds=int(os.getenv("DEXGUARD_REQUEST_TIMEOUT_SECONDS", "10")),
        enrichment_timeout_seconds=int(os.getenv("DEXGUARD_ENRICHMENT_TIMEOUT_SECONDS", "4")),
    )
