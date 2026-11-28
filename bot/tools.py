from datetime import timedelta
import json
from bot.database import (
    to_iso,
    utc_now,
    parse_iso,
    insert_reminder,
    insert_note,
    query_notes,
    fetch_recent_notes,
    insert_todo,
    update_todos,
    fetch_active_todos,
    delete_todo,
    complete_todo,
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
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search the user's saved notes by keywords on titles, content and category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Keyword or topic to search for."},
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List the user's most recently saved notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of notes to return (Default 10)"},
                },
            },
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
    {
        "type": "function",
        "function": {
            "name": "add_todo",
            "description":
                "Create an actionable todo list item with a deadline. Automatically sets a reminder 6 hours before the deadline. Provide EITHER 'due_at_utc' (YYYY-MM-DDTHH:MM:SSZ) OR 'due_in_hours'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The tasks description."},
                    "due_at_utc": {"type": "string", "description": "Deadline in UTC."},
                    "due_in_hours": {"type": "string", "description": "Hours from now until the deadline."},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_todo",
            "description": "Mark a todo as completed and cancel reminders linked to it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer", "description": "Numeric ID of the completed todo."},
                },
                "required": ["todo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detete_todo",
            "description": "Remove a todo along with its linked reminders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer", "description": "Numeric ID of the todo to be deleted."},
                },
                "required": ["todo_id"],
            },
        },
    },
]

def _resolve_due_iso(due_at_utc: str | None, offset: float | None = None) -> str | None:
    if due_at_utc:
        return to_iso(parse_iso(due_at_utc))
    if offset is not None:
        return to_iso(utc_now() + timedelta(hours=float(offset)))
    return None

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
        elif name == "save_note":
            note_id = await insert_note(acc_id=acc_id, title=args["title"], content=args["content"], category=args.get("category", "general"))
            return json.dumps({"status": "saved", "note_id": note_id, "title": args["title"]})
        elif name == "search_notes":
            notes = await query_notes(acc_id=acc_id, keyword=args["keyword"])
            return json.dumps({"count": len(notes), "notes": notes})
        elif name == "list_notes":
            limit = min(int(args.get("limit", 10)), 25)
            notes = await fetch_recent_notes(acc_id=acc_id, limit=limit)
            return json.dumps({"count": len(notes), "notes": notes})
        elif name == "add_todo":
            due_iso = _resolve_due_iso(args.get("due_at_utc"), args.get("due_in_hours"))
            if not due_iso:
                return json.dumps({"error": "Provide due_at_utc or due_in_hours!"})
            created = await insert_todo(acc_id=acc_id, title=args["title"], due_at_iso=due_iso, platform=platform, chat_id=chat_id)
            return json.dumps({"status": "created", **created})
        elif name == "complete_todo":
            ok = await complete_todo(acc_id=acc_id, todo_id=int(args["todo_id"]))
            return json.dumps({"status": "completed" if ok else "not_found", "todo_id": args["todo_id"]})
        elif name == "delete_todo":
            ok =  await delete_todo(acc_id=acc_id, todo_id=int(args["todo_id"]))
            return json.dumps({"status": "deleted" if ok else "not_found", "todo_id": args["todo_id"]})


        return json.dumps({"error": f"Unknown tool."})
    except Exception as exc:
        return json.dumps({"error": str(exc)})
