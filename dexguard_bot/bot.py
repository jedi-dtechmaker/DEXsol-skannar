from __future__ import annotations

import logging
import re
import time

from .config import get_settings
from .dexscreener import DexScreenerClient
from .formatting import (
    flow_message,
    help_keyboard,
    help_message,
    holder_text,
    lock_message,
    risk_scan_message,
    scan_card,
    scan_message,
)
from .holders import HolderProvider
from .locks import LockProvider
from .models import OutgoingResponse
from .providers import GeckoTerminalClient, SecurityAggregator
from .scanner import Scanner
from .storage import Storage
from .telegram import TelegramClient


LOG = logging.getLogger("dexguard_bot")
ADDRESS_RE = re.compile(r"\b(?:0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})\b")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required. Add it to .env or the environment.")

    scanner = Scanner(
        dexscreener=DexScreenerClient(timeout=settings.request_timeout_seconds),
        holders=HolderProvider(settings.solana_rpc_url, timeout=settings.enrichment_timeout_seconds),
        locks=LockProvider(),
        security=SecurityAggregator(timeout=settings.enrichment_timeout_seconds),
        market=GeckoTerminalClient(timeout=settings.enrichment_timeout_seconds),
        storage=Storage(settings.db_path),
    )
    telegram = TelegramClient(settings.telegram_bot_token, timeout=settings.request_timeout_seconds)
    LOG.info("DexGuard Bot started with long polling.")

    offset: int | None = None
    while True:
        try:
            updates = telegram.get_updates(offset)
            for update in updates:
                offset = int(update["update_id"]) + 1
                handle_update(update, telegram, scanner)
        except KeyboardInterrupt:
            LOG.info("DexGuard Bot stopped.")
            return
        except Exception:
            LOG.exception("Polling loop error")
            time.sleep(3)


def handle_update(update: dict, telegram: TelegramClient, scanner: Scanner) -> None:
    if update.get("callback_query"):
        handle_callback(update["callback_query"], telegram, scanner)
        return

    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not text or chat_id is None:
        return

    try:
        if should_show_scan_action(text):
            telegram.send_chat_action(int(chat_id))
        response = route_message(text, scanner)
    except Exception as exc:
        LOG.exception("Failed to handle message")
        response = OutgoingResponse(text=f"Scan failed: {str(exc)}")
    telegram.send_response(int(chat_id), response)


def handle_callback(callback: dict, telegram: TelegramClient, scanner: Scanner) -> None:
    callback_id = str(callback.get("id") or "")
    data = str(callback.get("data") or "")
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        if callback_id:
            telegram.answer_callback_query(callback_id, "Missing chat context.")
        return

    try:
        telegram.answer_callback_query(callback_id)
        telegram.send_chat_action(int(chat_id))
        response = route_callback(data, scanner)
    except Exception as exc:
        LOG.exception("Failed to handle callback")
        response = OutgoingResponse(text=f"Action failed: {str(exc)}")
    telegram.send_response(int(chat_id), response)


def route_message(text: str, scanner: Scanner) -> OutgoingResponse:
    command, arg = parse_command(text)
    if command in ("/start", "/help"):
        return OutgoingResponse(text=help_message(), reply_markup=help_keyboard())
    if command == "/trending":
        return OutgoingResponse(text=trending_message(scanner.storage.trending()))
    if command == "/scan":
        error = require_arg(arg, "/scan")
        return OutgoingResponse(text=error) if error else scan_card(scanner.scan(arg))
    if command == "/lock":
        error = require_arg(arg, "/lock")
        return OutgoingResponse(text=error) if error else OutgoingResponse(text=lock_message(scanner.scan(arg)))
    if command == "/flow":
        error = require_arg(arg, "/flow")
        return OutgoingResponse(text=error) if error else OutgoingResponse(text=flow_message(scanner.scan(arg)))

    match = ADDRESS_RE.search(text)
    if match:
        return scan_card(scanner.scan(match.group(0)))
    return OutgoingResponse(text=help_message())


def route_callback(data: str, scanner: Scanner) -> OutgoingResponse:
    if data == "trending":
        return OutgoingResponse(text=trending_message(scanner.storage.trending()))

    action, query = parse_callback_data(data)
    if action == "details":
        return OutgoingResponse(text=scan_message(scanner.scan(query)))
    if action == "holders":
        result = scanner.scan(query)
        return OutgoingResponse(text=f"<b>Whale Signals: {result.pair.base_symbol}</b>\n{holder_text(result)}")
    if action == "risk":
        return OutgoingResponse(text=risk_scan_message(scanner.scan(query)))
    return OutgoingResponse(text="Unknown action.")


def parse_callback_data(data: str) -> tuple[str, str]:
    parts = data.split(":", 2)
    if len(parts) != 3:
        return data, ""
    action, chain_id, address = parts
    return action, f"{chain_id}:{address}"


def parse_command(text: str) -> tuple[str, str]:
    if not text.startswith("/"):
        return "", text
    parts = text.split(maxsplit=1)
    command = parts[0].split("@", 1)[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return command, arg


def should_show_scan_action(text: str) -> bool:
    command, _ = parse_command(text)
    if command in {"/scan", "/lock", "/flow"}:
        return True
    return ADDRESS_RE.search(text) is not None


def require_arg(arg: str, command: str) -> str:
    if arg:
        return ""
    return f"Usage: {command} &lt;contract | chain:contract | symbol&gt;"


def trending_message(rows: list[tuple[str, str, str, int]]) -> str:
    if not rows:
        return "No scans recorded yet."
    lines = ["<b>DexGuard Trending</b>"]
    for index, (chain_id, address, symbol, count) in enumerate(rows, start=1):
        short = f"{address[:6]}...{address[-6:]}" if len(address) > 14 else address
        lines.append(f"{index}. <b>{symbol}</b> ({chain_id}) <code>{short}</code> - {count} scans")
    return "\n".join(lines)
