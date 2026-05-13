"""Discord webhook notifier."""

from __future__ import annotations

import aiohttp

from .base import Notifier, NotifyPayload, register_notifier


class DiscordNotifier(Notifier):
    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(self, payload: NotifyPayload) -> bool:
        data = {"content": payload.summary()}
        async with (
            aiohttp.ClientSession() as session,
            session.post(self._url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            return resp.status in (200, 204)


register_notifier("discord", DiscordNotifier)
