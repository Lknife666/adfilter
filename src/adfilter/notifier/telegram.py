"""Telegram Bot API notifier."""

from __future__ import annotations

import aiohttp

from .base import Notifier, NotifyPayload


class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id

    async def send(self, payload: NotifyPayload) -> bool:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        data = {
            "chat_id": self._chat_id,
            "text": payload.summary(),
            "parse_mode": "HTML",
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            return resp.status == 200
