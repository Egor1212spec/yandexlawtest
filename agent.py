"""
YandexAgent — OpenClaw-style agent powered by Yandex AI
Runs as a Telegram bot with GitHub monitoring and reminder scheduling.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from openai import OpenAI

from config import Config
from tools.github_tool import GitHubTool
from tools.telegram_tool import TelegramTool
from tools.reminder_tool import ReminderTool
from tools.memory_tool import MemoryTool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log"),
    ],
)
log = logging.getLogger(__name__)


class YandexAgent:
    """
    Agent that:
    - Polls Telegram for user messages
    - Summarizes GitHub commits and Telegram history on request
    - Sets reminders that fire back into Telegram
    - Stores memory and skills as Markdown files
    """

    def __init__(self):
        self.cfg = Config()
        self.client = OpenAI(
            base_url="https://ai.api.cloud.yandex.net/v1",
            api_key=self.cfg.YANDEX_API_KEY,
        )
        self.github = GitHubTool(self.cfg)
        self.tg = TelegramTool(self.cfg)
        self.reminders = ReminderTool(self.cfg, self.tg)
        self.memory = MemoryTool(self.cfg)

    # ------------------------------------------------------------------ #
    #  Core LLM call                                                       #
    # ------------------------------------------------------------------ #

    def ask(self, user_input: str, extra_context: str = "") -> str:
        """Send a prompt to Yandex AI agent and return the text reply."""
        skills = self.memory.load_skills()
        mem = self.memory.load_memory()
        system_context = f"""
{skills}

---
AGENT MEMORY:
{mem}

---
EXTRA CONTEXT (injected automatically):
{extra_context}

Today is {datetime.now().strftime('%A, %d %B %Y %H:%M')}.
Always reply in the language the user used.
""".strip()

        full_input = f"[SYSTEM CONTEXT]\n{system_context}\n\n[USER]\n{user_input}"

        try:
            response = self.client.responses.create(
                prompt={"id": self.cfg.YANDEX_AGENT_ID},
                input=full_input,
                max_output_tokens=2000,
            )
            return response.output[0].content[0].text
        except Exception as e:
            log.error(f"Yandex AI error: {e}")
            return f"⚠️ Ошибка при обращении к AI: {e}"

    # ------------------------------------------------------------------ #
    #  High-level actions                                                  #
    # ------------------------------------------------------------------ #

    async def handle_message(self, chat_id: int, text: str, user_name: str):
        """Decide what to do with an incoming Telegram message."""
        text_lower = text.lower()

        # --- Reminder intent ---
        if any(k in text_lower for k in ["напомни", "remind me", "reminder", "напоминание"]):
            reply = self._handle_reminder_request(chat_id, text)

        # --- GitHub summary ---
        elif any(k in text_lower for k in ["github", "коммит", "commit", "репозитор"]):
            commits = self.github.get_recent_commits()
            ctx = f"GITHUB COMMITS (last 7 days):\n{commits}"
            reply = self.ask(text, extra_context=ctx)

        # --- Telegram history summary ---
        elif any(k in text_lower for k in ["сообщени", "чат", "telegram", "прогресс", "план", "summary"]):
            history = self.memory.load_telegram_history()
            ctx = f"TELEGRAM HISTORY:\n{history}"
            reply = self.ask(text, extra_context=ctx)

        # --- Save something to memory ---
        elif text_lower.startswith(("/remember", "/запомни")):
            note = text.split(" ", 1)[1] if " " in text else ""
            self.memory.save_note(note)
            reply = f"✅ Запомнил: {note}"

        # --- Default: just chat ---
        else:
            reply = self.ask(text)

        # Save user message to Telegram history
        self.memory.append_telegram_message(user_name, text)

        await self.tg.send_message(chat_id, reply)

    def _handle_reminder_request(self, chat_id: int, text: str) -> str:
        """Parse a reminder from natural language and schedule it."""
        parse_prompt = f"""
Extract reminder details from this text.
Return ONLY valid JSON with keys: "time_iso" (ISO 8601), "message" (what to remind about).
Example: {{"time_iso": "2024-01-15T14:30:00", "message": "Buy groceries"}}
Text: {text}
Today: {datetime.now().isoformat()}
"""
        raw = self.ask(parse_prompt)
        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(clean)
            remind_time = datetime.fromisoformat(data["time_iso"])
            self.reminders.schedule(chat_id, remind_time, data["message"])
            return f"⏰ Напоминание установлено на {remind_time.strftime('%d.%m.%Y %H:%M')}\n📌 {data['message']}"
        except Exception as e:
            log.warning(f"Could not parse reminder: {e}\nRaw: {raw}")
            return "Не смог разобрать время напоминания. Попробуй: «Напомни мне 25 декабря в 10:00 позвонить маме»"

    # ------------------------------------------------------------------ #
    #  Background tasks                                                    #
    # ------------------------------------------------------------------ #

    async def daily_github_sync(self):
        """Every 24h fetch GitHub commits and save to memory."""
        while True:
            try:
                log.info("🔄 Syncing GitHub commits...")
                commits = self.github.get_recent_commits()
                self.memory.save_github_snapshot(commits)
                log.info(f"✅ GitHub sync done. {len(commits.splitlines())} lines saved.")
            except Exception as e:
                log.error(f"GitHub sync failed: {e}")
            await asyncio.sleep(86400)  # 24h

    async def poll_telegram(self):
        """Long-poll Telegram for new messages."""
        log.info("🤖 Telegram polling started")
        offset = None
        while True:
            try:
                updates = await self.tg.get_updates(offset)
                for update in updates:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    user = msg.get("from", {}).get("username", "unknown")
                    if text and chat_id:
                        asyncio.create_task(
                            self.handle_message(chat_id, text, user)
                        )
            except Exception as e:
                log.error(f"Telegram poll error: {e}")
            await asyncio.sleep(1)

    async def run_reminders(self):
        """Fire due reminders every 30 seconds."""
        while True:
            await self.reminders.fire_due()
            await asyncio.sleep(30)

    # ------------------------------------------------------------------ #
    #  Entry point                                                         #
    # ------------------------------------------------------------------ #

    async def run(self):
        log.info("🚀 YandexAgent starting...")
        await asyncio.gather(
            self.poll_telegram(),
            self.daily_github_sync(),
            self.run_reminders(),
        )


if __name__ == "__main__":
    asyncio.run(YandexAgent().run())
