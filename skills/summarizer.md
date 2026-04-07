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
