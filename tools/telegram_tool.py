"""
tools/telegram_tool.py
Thin async wrapper around the Telegram Bot HTTP API.
Supports SOCKS5/HTTP proxy via TELEGRAM_PROXY in .env
"""

import aiohttp
import logging
import os
from config import Config

log = logging.getLogger(__name__)
TG_BASE = "https://api.telegram.org/bot{token}/{method}"


def _make_connector():
    """Return a SOCKS5/HTTP connector if TELEGRAM_PROXY is set, else None."""
    proxy_url = os.getenv("TELEGRAM_PROXY", "").strip()
    if not proxy_url:
        return None, None
    if proxy_url.startswith("socks"):
        try:
            from aiohttp_socks import ProxyConnector
            return ProxyConnector.from_url(proxy_url), None
        except ImportError:
            log.warning("aiohttp-socks not installed. Run: pip install aiohttp-socks")
    return None, proxy_url  # plain HTTP proxy


class TelegramTool:
    def __init__(self, cfg: Config):
        self.token = cfg.TELEGRAM_BOT_TOKEN
        self.allowed = set(cfg.TELEGRAM_ALLOWED_CHAT_IDS)

    def _url(self, method: str) -> str:
        return TG_BASE.format(token=self.token, method=method)

    def _session(self) -> aiohttp.ClientSession:
        connector, http_proxy = _make_connector()
        self._http_proxy = http_proxy  # store for request kwargs
        if connector:
            return aiohttp.ClientSession(connector=connector)
        return aiohttp.ClientSession()

    def _proxy_kwargs(self) -> dict:
        proxy = getattr(self, "_http_proxy", None)
        return {"proxy": proxy} if proxy else {}

    async def send_message(self, chat_id: int, text: str) -> bool:
        if self.allowed and chat_id not in self.allowed:
            log.warning(f"Blocked message to unauthorized chat {chat_id}")
            return False

        chunks = [text[i: i + 4000] for i in range(0, len(text), 4000)]
        async with self._session() as session:
            for chunk in chunks:
                try:
                    async with session.post(
                        self._url("sendMessage"),
                        json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                        timeout=aiohttp.ClientTimeout(total=10),
                        **self._proxy_kwargs(),
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
        params: dict = {"timeout": 30, "allowed_updates": ["message"]}
        if offset is not None:
            params["offset"] = offset

        async with self._session() as session:
            try:
                async with session.get(
                    self._url("getUpdates"),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=35),
                    **self._proxy_kwargs(),
                ) as resp:
                    data = await resp.json()
                    return data.get("result", [])
            except Exception as e:
                log.error(f"get_updates error: {e}")
                return []

    async def get_chat_history(self, chat_id: int, limit: int = 100) -> list[dict]:
        return []