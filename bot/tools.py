

TOOL_SCHEMA = [
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