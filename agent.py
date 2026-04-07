"""
YandexAgent — OpenClaw-style agent powered by Yandex AI
Runs as a Telegram bot with GitHub monitoring and reminder scheduling.
"""

import asyncio
import logging
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

        # If real data is injected — tell the model EXPLICITLY to use it
        data_instruction = ""
        if extra_context.strip():
            data_instruction = (
                "\n\nCRITICAL INSTRUCTION: The section below contains REAL DATA "
                "fetched right now from external sources. "
                "You MUST base your answer exclusively on this data. "
                "Do NOT give generic advice. Do NOT suggest commands. "
                "Just summarize and present the data below.\n"
            )

        system_context = (
            f"{skills}\n\n"
            f"---\nAGENT MEMORY:\n{mem}\n\n"
            f"---\nToday is {datetime.now().strftime('%A, %d %B %Y %H:%M')}.\n"
            f"Always reply in the language the user used."
            f"{data_instruction}"
        )

        if extra_context.strip():
            full_input = (
                f"[SYSTEM CONTEXT]\n{system_context}\n\n"
                f"[REAL DATA — USE THIS TO ANSWER]\n{extra_context}\n\n"
                f"[USER QUESTION]\n{user_input}"
            )
        else:
            full_input = f"[SYSTEM CONTEXT]\n{system_context}\n\n[USER]\n{user_input}"

        log.debug(f"Sending to Yandex AI:\n{full_input[:500]}...")

        try:
            response = self.client.responses.create(
                prompt={"id": self.cfg.YANDEX_AGENT_ID},
                input=full_input,
                max_output_tokens=2000,
            )
            texts = []
            for block in response.output:
                contents = getattr(block, "content", None)
                if not contents:
                    continue
                for item in contents:
                    text = getattr(item, "text", None)
                    if text:
                        texts.append(text)
            return "\n".join(texts) if texts else "_(нет текстового ответа)_"
        except Exception as e:
            log.error(f"Yandex AI error: {e}")
            return f"⚠️ Ошибка при обращении к AI: {e}"

    # ------------------------------------------------------------------ #
    #  High-level actions                                                  #
    # ------------------------------------------------------------------ #

    async def handle_message(self, chat_id: int, text: str, user_name: str):
        text_lower = text.lower()

        # --- Reminder intent ---
        if any(k in text_lower for k in ["напомни", "remind me", "reminder", "напоминание", "напомни мне", "можешь напомнить", "можешь мне напомнить", "поставь напоминание", "set a reminder", "в ", "remind"]):
            reply = self._handle_reminder_request(chat_id, text)

        # --- GitHub summary ---
        elif any(k in text_lower for k in [
            "github", "коммит", "комит", "commit", "репозитор",
            "последние изменени", "что сделал", "что было сделано",
            "какие изменени", "история изменени",
            "коммиты", "комиты", "commits",
            "последние коммит", "последние комит",
            "мои коммит", "мои комит",
        ]):
            log.info("📦 GitHub intent detected — fetching commits...")
            commits = self.github.get_recent_commits()
            log.info(f"Commits fetched:\n{commits[:300]}")
            ctx = (
                f"REAL GITHUB COMMITS DATA (fetched right now from GitHub API):\n"
                f"{commits}\n\n"
                f"Present this data to the user as a formatted summary. "
                f"Do not suggest any git commands. Just show what's in the data above."
            )
            reply = self.ask(text, extra_context=ctx)

        # --- Telegram history summary ---
        elif any(k in text_lower for k in ["сообщени", "чат", "telegram", "прогресс", "план", "summary"]):
            history = self.memory.load_telegram_history()
            ctx = f"TELEGRAM HISTORY (real messages):\n{history}"
            reply = self.ask(text, extra_context=ctx)

        # --- Save note ---
        elif text_lower.startswith(("/remember", "/запомни")):
            note = text.split(" ", 1)[1] if " " in text else ""
            self.memory.save_note(note)
            reply = f"✅ Запомнил: {note}"

        # --- Default ---
        else:
            reply = self.ask(text)

        self.memory.append_telegram_message(user_name, text)
        await self.tg.send_message(chat_id, reply)

    def _handle_reminder_request(self, chat_id: int, text: str) -> str:
        local_now = datetime.now()
        parse_prompt = (
            f"Extract reminder details from this text.\n"
            f"Return ONLY valid JSON with keys: "
            f'"time_iso" (ISO 8601 datetime, LOCAL time, no timezone suffix), "message" (what to remind about).\n'
            f'Example: {{"time_iso": "2024-01-15T14:30:00", "message": "Buy groceries"}}\n'
            f"Text: {text}\n"
            f"Current local date and time: {local_now.strftime('%Y-%m-%dT%H:%M:%S')}\n"
            f"Return ONLY the JSON object, no other text."
        )
        raw = self.ask(parse_prompt)
        try:
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            remind_time = datetime.fromisoformat(data["time_iso"])
            self.reminders.schedule(chat_id, remind_time, data["message"])
            return (
                f"⏰ Напоминание установлено на "
                f"{remind_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"📌 {data['message']}"
            )
        except Exception as e:
            log.warning(f"Could not parse reminder: {e}\nRaw: {raw}")
            return (
                "Не смог разобрать время напоминания.\n"
                "Попробуй: «Напомни мне 25 декабря в 10:00 позвонить маме»"
            )

    # ------------------------------------------------------------------ #
    #  Background tasks                                                    #
    # ------------------------------------------------------------------ #

    async def daily_github_sync(self):
        while True:
            try:
                log.info("🔄 Syncing GitHub commits...")
                commits = self.github.get_recent_commits()
                self.memory.save_github_snapshot(commits)
                log.info(f"✅ GitHub sync done. {len(commits.splitlines())} lines saved.")
            except Exception as e:
                log.error(f"GitHub sync failed: {e}")
            await asyncio.sleep(86400)

    async def poll_telegram(self):
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
        while True:
            await self.reminders.fire_due()
            await asyncio.sleep(30)

    async def run(self):
        log.info("🚀 YandexAgent starting...")
        await asyncio.gather(
            self.poll_telegram(),
            self.daily_github_sync(),
            self.run_reminders(),
        )


if __name__ == "__main__":
    asyncio.run(YandexAgent().run())