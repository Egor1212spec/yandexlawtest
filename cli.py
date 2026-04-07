"""
cli.py — run the agent in interactive CLI mode (no Telegram).
Useful for testing prompts before deploying the full bot.

Usage:
    python cli.py
    python cli.py "What did I commit this week?"
"""

import sys
import asyncio
from agent import YandexAgent


async def main():
    ag = YandexAgent()

    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        print(f"\n🧑 You: {query}\n")
        response = ag.ask(query)
        print(f"🤖 Agent: {response}\n")
        return

    # Interactive REPL
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

        response = ag.ask(user_input)
        print(f"\n🤖 Agent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
