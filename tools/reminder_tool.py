"""
tools/reminder_tool.py
Persists reminders as JSON and fires them at the right time via Telegram.
Behaves like the "cron" feature in OpenClaw.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from config import Config

log = logging.getLogger(__name__)


class ReminderTool:
    def __init__(self, cfg: Config, tg):
        self.tg = tg
        self.path = Path(cfg.REMINDERS_FILE)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    # ---- persistence ---- #

    def _load(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, reminders: list[dict]):
        self.path.write_text(
            json.dumps(reminders, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- public API ---- #

    def schedule(self, chat_id: int, when: datetime, message: str):
        """Add a reminder."""
        reminders = self._load()
        reminders.append(
            {
                "chat_id": chat_id,
                "when": when.isoformat(),
                "message": message,
                "fired": False,
            }
        )
        self._save(reminders)
        log.info(f"⏰ Reminder scheduled: {when.isoformat()} → chat {chat_id}")

    def list_pending(self, chat_id: int) -> list[dict]:
        """Return upcoming (not fired) reminders for a chat."""
        return [
            r
            for r in self._load()
            if r["chat_id"] == chat_id and not r["fired"]
        ]

    async def fire_due(self):
        """Check all reminders; fire those whose time has come."""
        now = datetime.now(timezone.utc)
        reminders = self._load()
        changed = False

        for r in reminders:
            if r["fired"]:
                continue
            try:
                when = datetime.fromisoformat(r["when"])
                # Make timezone-aware if naive
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                if now >= when:
                    log.info(f"🔔 Firing reminder for chat {r['chat_id']}: {r['message']}")
                    await self.tg.send_message(
                        r["chat_id"],
                        f"🔔 *Напоминание*\n\n{r['message']}",
                    )
                    r["fired"] = True
                    changed = True
            except Exception as e:
                log.error(f"Reminder fire error: {e}")

        if changed:
            self._save(reminders)
            # Clean up old fired reminders (keep last 50)
            all_r = self._load()
            kept = [r for r in all_r if not r["fired"]][-50:] + [
                r for r in all_r if r["fired"]
            ][-50:]
            self._save(kept)
