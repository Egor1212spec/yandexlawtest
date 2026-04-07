"""
config.py — all settings loaded from environment variables.
Copy .env.example to .env and fill in the values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Yandex AI
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_AGENT_ID: str = os.getenv("YANDEX_AGENT_ID", "")
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_CHAT_IDS: list[int] = [
        int(x)
        for x in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
        if x.strip()
    ]

    # GitHub
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPOS: list[str] = [
        r.strip()
        for r in os.getenv("GITHUB_REPOS", "").split(",")
        if r.strip()
    ]  # format: "owner/repo"
    GITHUB_DAYS_BACK: int = int(os.getenv("GITHUB_DAYS_BACK", "7"))

    # Memory / Skills paths
    MEMORY_DIR: str = os.getenv("MEMORY_DIR", "memory")
    SKILLS_DIR: str = os.getenv("SKILLS_DIR", "skills")
    REMINDERS_FILE: str = os.getenv("REMINDERS_FILE", "memory/reminders.json")
