from datetime import timedelta
import json
from bot.database import (
    to_iso,
    utc_now,
    parse_iso,
    insert_reminder
)

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a passive idea, fact, or spontaneous brainstorm into the user's Second Brain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short descriptive title for the note."},
                    "content": {"type": "string", "description": "Full note content or structured plan."},
                    "category": {"type": "string", "description": "Category such as 'fact', 'idea'."},
                },
            },
            "required": ["title", "content"],
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_reminder",
            "description": (
                "Schedule a one-off reminder for an event. (ex.: a meeting, class)"
                "Provide a message and EITHER a delay_minutes or a due_at_utc (YYYY-MM-DDTHH:MM:SSZ)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to remind the user about."},
                    "delay_minutes": {"type": "integer", "description": "Minutes from now until the reminder fires."},
                    "due_at_utc": {"type": "string", "description": "Exact UTC timestamp in format YYYY-MM-DDTHH:MM:SSZ.",
                    },
                },
                "required": ["message"],
            },
        },
    },
]

async def execute_tool(name: str, args: dict, acc_id: int, platform: str, chat_id: str | int) -> str:
    try:
        if name == "add_reminder":
            if args.get("delay_minutes") is not None:
                due_iso = to_iso(utc_now() + timedelta(minutes=int(args["delay_minutes"])))
            elif args.get("due_at_utc"):
                due_iso = to_iso(parse_iso(args["due_at_utc"]))
            else:
                return json.dumps({"error": "Provide either delay_minutes or due_at_utc."})

            rem_id = await insert_reminder(acc_id=acc_id, platform=platform, chat_id=chat_id, message=args["message"], due_at_iso=due_iso)
            return json.dumps({"status": "scheduled", "reminder_id": rem_id, "due_at_utc": due_iso})

        return json.dumps({"error": f"Unknown tool."})
    except Exception as exc:
        return json.dumps({"error": str(exc)})
