"""
cli.py — run the agent in interactive CLI mode (no Telegram).
Routes through the same handle_message() logic as the real bot,
so GitHub context, intent detection, and reminders all work.

Usage:
    python cli.py
    python cli.py "Покажи мои последние коммиты"
"""

import sys
import asyncio
from agent import YandexAgent

CLI_CHAT_ID = 0  # dummy chat id for CLI mode


async def cli_handle(ag: YandexAgent, text: str) -> str:
    """Route through handle_message, capture reply instead of sending to TG."""
    replies = []

    original_send = ag.tg.send_message
    async def capture(chat_id, msg):
        replies.append(msg)
    ag.tg.send_message = capture

    await ag.handle_message(CLI_CHAT_ID, text, "cli_user")

    ag.tg.send_message = original_send
    return "\n".join(replies) if replies else "_(нет ответа)_"


async def main():
    ag = YandexAgent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\n🧑 You: {query}\n")
        response = await cli_handle(ag, query)
        print(f"🤖 Agent: {response}\n")
        return

    print("YandexAgent CLI — type 'exit' to quit\n")
    while True:
        try:
            user_input = input("🧑 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            break
        if not user_input:
            continue

        response = await cli_handle(ag, user_input)
        print(f"\n🤖 Agent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())