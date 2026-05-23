from __future__ import annotations

from typing import Any

from .http import get_json, post_json
from .models import OutgoingResponse


class TelegramClient:
    def __init__(self, token: str, timeout: int = 15):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout

    def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        params = {"timeout": 30, "allowed_updates": '["message","callback_query"]'}
        if offset is not None:
            params["offset"] = offset
        data = get_json(f"{self.base_url}/getUpdates", timeout=40, params=params)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {data}")
        return data.get("result") or []

    def send_message(self, chat_id: int, text: str, disable_preview: bool = True) -> None:
        chunks = split_message(text)
        for chunk in chunks:
            data = post_json(
                f"{self.base_url}/sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": disable_preview,
                },
                timeout=self.timeout,
            )
            if not data.get("ok"):
                raise RuntimeError(f"Telegram sendMessage failed: {data}")

    def send_photo(
        self,
        chat_id: int,
        photo_url: str,
        caption: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = post_json(f"{self.base_url}/sendPhoto", payload, timeout=self.timeout)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendPhoto failed: {data}")

    def send_response(self, chat_id: int, response: OutgoingResponse) -> None:
        if response.photo_url:
            try:
                self.send_photo(chat_id, response.photo_url, response.text, response.reply_markup)
                return
            except Exception:
                # Fall back to text if Telegram rejects a remote image URL.
                pass

        chunks = split_message(response.text)
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": response.disable_preview,
            }
            if index == len(chunks) - 1 and response.reply_markup:
                payload["reply_markup"] = response.reply_markup
            data = post_json(f"{self.base_url}/sendMessage", payload, timeout=self.timeout)
            if not data.get("ok"):
                raise RuntimeError(f"Telegram sendMessage failed: {data}")

    def send_chat_action(self, chat_id: int, action: str = "typing") -> None:
        data = post_json(
            f"{self.base_url}/sendChatAction",
            {
                "chat_id": chat_id,
                "action": action,
            },
            timeout=self.timeout,
        )
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendChatAction failed: {data}")

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        data = post_json(f"{self.base_url}/answerCallbackQuery", payload, timeout=self.timeout)
        if not data.get("ok"):
            raise RuntimeError(f"Telegram answerCallbackQuery failed: {data}")


def split_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for line in text.splitlines():
        needed = len(line) + 1
        if current and size + needed > limit:
            chunks.append("\n".join(current))
            current = []
            size = 0
        current.append(line)
        size += needed
    if current:
        chunks.append("\n".join(current))
    return chunks
