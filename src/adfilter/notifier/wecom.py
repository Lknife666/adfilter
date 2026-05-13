"""WeCom (企业微信) group robot webhook notifier."""

from __future__ import annotations

import aiohttp

from .base import Notifier, NotifyPayload


class WecomNotifier(Notifier):
    def __init__(self, webhook_key: str) -> None:
        self._url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"

    async def send(self, payload: NotifyPayload) -> bool:
        data = {
            "msgtype": "text",
            "text": {"content": payload.summary()},
        }
        async with (
            aiohttp.ClientSession() as session,
            session.post(self._url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            return resp.status == 200
