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
