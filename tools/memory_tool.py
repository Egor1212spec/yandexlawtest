"""
tools/memory_tool.py
All agent memory and skills live as Markdown files.
Structure:
  memory/
    notes.md            ← user notes saved via /remember
    telegram_history.md ← running log of Telegram messages
    github_snapshot.md  ← latest GitHub commit dump
  skills/
    core.md             ← agent identity & instructions
    github.md           ← GitHub summarization skill
    summarizer.md       ← general summarization skill
    reminders.md        ← reminder handling skill
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from config import Config

log = logging.getLogger(__name__)


class MemoryTool:
    def __init__(self, cfg: Config):
        self.mem_dir = Path(cfg.MEMORY_DIR)
        self.skills_dir = Path(cfg.SKILLS_DIR)
        self.mem_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._init_defaults()

    # ------------------------------------------------------------------ #
    #  Skills (read-only at runtime, editable by user)                    #
    # ------------------------------------------------------------------ #

    def load_skills(self) -> str:
        """Concatenate all skill MD files into one system-context string."""
        parts = []
        for md in sorted(self.skills_dir.glob("*.md")):
            parts.append(f"# SKILL: {md.stem.upper()}\n")
            parts.append(md.read_text(encoding="utf-8"))
            parts.append("\n---\n")
        return "\n".join(parts) if parts else "No skills loaded."

    # ------------------------------------------------------------------ #
    #  Memory (read / write)                                              #
    # ------------------------------------------------------------------ #

    def load_memory(self) -> str:
        """Load notes and a recent slice of Telegram history."""
        notes = self._read("notes.md")
        history = self._read_last_lines("telegram_history.md", 100)
        github = self._read("github_snapshot.md")
        return (
            f"## Notes\n{notes}\n\n"
            f"## Recent Telegram messages (last 100)\n{history}\n\n"
            f"## GitHub snapshot\n{github}"
        )

    def save_note(self, text: str):
        self._append("notes.md", f"- [{self._ts()}] {text}")

    def append_telegram_message(self, user: str, text: str):
        self._append(
            "telegram_history.md",
            f"[{self._ts()}] @{user}: {text}",
        )

    def load_telegram_history(self, last_n: int = 200) -> str:
        return self._read_last_lines("telegram_history.md", last_n)

    def save_github_snapshot(self, content: str):
        path = self.mem_dir / "github_snapshot.md"
        path.write_text(
            f"# GitHub Snapshot — {self._ts()}\n\n{content}\n",
            encoding="utf-8",
        )
        log.info(f"GitHub snapshot saved to {path}")

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _path(self, filename: str) -> Path:
        return self.mem_dir / filename

    def _read(self, filename: str) -> str:
        p = self._path(filename)
        if p.exists():
            return p.read_text(encoding="utf-8")
        return "_empty_"

    def _read_last_lines(self, filename: str, n: int) -> str:
        p = self._path(filename)
        if not p.exists():
            return "_no history yet_"
        lines = p.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[-n:])

    def _append(self, filename: str, line: str):
        p = self._path(filename)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

    # ------------------------------------------------------------------ #
    #  Default skill files (written once if missing)                      #
    # ------------------------------------------------------------------ #

    def _init_defaults(self):
        defaults = {
            "skills/core.md": SKILL_CORE,
            "skills/github.md": SKILL_GITHUB,
            "skills/summarizer.md": SKILL_SUMMARIZER,
            "skills/reminders.md": SKILL_REMINDERS,
            "memory/notes.md": "# Notes\n",
            "memory/telegram_history.md": "# Telegram History\n",
            "memory/github_snapshot.md": "# GitHub Snapshot\n_Not yet synced._\n",
        }
        for rel, content in defaults.items():
            p = Path(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(content, encoding="utf-8")
                log.info(f"Created default file: {p}")


# ------------------------------------------------------------------ #
#  Default skill content                                              #
# ------------------------------------------------------------------ #

SKILL_CORE = """\
# Core Identity

You are a personal productivity agent. You help the user:
1. Stay on top of their GitHub development work by summarizing commits.
2. Recap Telegram conversation history on demand.
3. Set and fire reminders at specified times.
4. Remember notes and context across sessions.

## Behavior rules
- Always reply in the same language the user used.
- Be concise but complete. Bullet points are preferred for summaries.
- When asked for a summary, group information by topic or date, not by raw chronology.
- Never make up information. If you don't know something, say so.
- When setting a reminder, always confirm the exact date and time back to the user.
"""

SKILL_GITHUB = """\
# GitHub Summarization Skill

When the user asks about GitHub activity, commits, or repository progress:

1. Use the provided GITHUB COMMITS context block.
2. Group commits by date or feature area.
3. Highlight: new features, bug fixes, refactors, and notable authors.
4. Format output as Markdown with sections per repository.
5. Provide a one-sentence TL;DR at the top.

## Example output format
**TL;DR**: This week focused on auth refactor and CI fixes.

### repo-name
- 2024-01-15: Added OAuth2 flow (alice)
- 2024-01-14: Fixed CI pipeline timeout (bob)
"""

SKILL_SUMMARIZER = """\
# Conversation Summarizer Skill

When the user asks to summarize Telegram messages or conversation history:

1. Use the TELEGRAM HISTORY context block.
2. Extract: key decisions, action items, progress updates, blockers, plans.
3. Group by topic, not chronologically.
4. Use emoji markers: ✅ done, 🔄 in progress, ❌ blocked, 📋 planned.
5. Keep summaries scannable — max 200 words unless asked for more.

## Example output format
✅ **Done**: Deployed v2.1 to staging
🔄 **In Progress**: Database migration
📋 **Planned**: Load testing next week
❌ **Blocker**: Waiting for AWS credentials
"""

SKILL_REMINDERS = """\
# Reminder Skill

When the user asks to set a reminder:

1. Extract the exact date/time and the reminder message.
2. Handle relative times: "in 2 hours", "tomorrow at 9am", "next Monday".
3. Always confirm: "⏰ Reminder set for DD.MM.YYYY HH:MM — [message]"
4. If the time is ambiguous, ask for clarification.
5. When a reminder fires, send it as: "🔔 Reminder: [message]"

## Supported reminder patterns
- "Remind me at 3pm to call John"
- "Напомни завтра в 10 утра о встрече"
- "Set a reminder for Friday 18:00 — submit report"
- "In 30 minutes remind me to take a break"
"""
