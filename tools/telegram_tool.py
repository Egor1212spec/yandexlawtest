"""
tools/telegram_tool.py
Thin async wrapper around the Telegram Bot HTTP API.
"""

import aiohttp
import logging
from config import Config

log = logging.getLogger(__name__)
TG_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramTool:
    def __init__(self, cfg: Config):
        self.token = cfg.TELEGRAM_BOT_TOKEN
        self.allowed = set(cfg.TELEGRAM_ALLOWED_CHAT_IDS)

    def _url(self, method: str) -> str:
        return TG_BASE.format(token=self.token, method=method)

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send a text message. Returns True on success."""
        if self.allowed and chat_id not in self.allowed:
            log.warning(f"Blocked message to unauthorized chat {chat_id}")
            return False

        # Telegram max message length is 4096 chars
        chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
        async with aiohttp.ClientSession() as session:
            for chunk in chunks:
                try:
                    async with session.post(
                        self._url("sendMessage"),
                        json={
                            "chat_id": chat_id,
                            "text": chunk,
                            "parse_mode": "Markdown",
                        },
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            log.error(f"TG sendMessage failed: {resp.status} {body}")
                            return False
                except Exception as e:
                    log.error(f"TG sendMessage exception: {e}")
                    return False
        return True

    async def get_updates(self, offset: int | None = None) -> list[dict]:
        """Long-poll for updates. Returns list of update dicts."""
        params: dict = {"timeout": 30, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._url("getUpdates"),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=35),
                ) as resp:
                    data = await resp.json()
                    return data.get("result", [])
            except Exception as e:
                log.error(f"get_updates error: {e}")
                return []

    async def get_chat_history(self, chat_id: int, limit: int = 100) -> list[dict]:
        """
        NOTE: The Bot API doesn't expose message history directly.
        We rely on memory/telegram_history.md stored locally instead.
        This method is a placeholder for future webhook/export integration.
        """
        return []
