import asyncio
import logging
import json
from openai import (AsyncOpenAI, BadRequestError)
from bot.config import config
from bot.database import (to_iso, utc_now)
from bot.tools import (TOOL_SCHEMA, execute_tool)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Nudge, a concise, proactive personal assistant and a Second Brain.
Your job is to:
1. Schedule point in time reminders via the usage of `add_reminder` when the user asks to reminded at a specific time or delay.
2. Add facts, ideas or brainstorms to the user's Second Brain via the `save_note`.

Current UTC time: {now_utc}
Rules:
- Convert relative times into UTC using the current UTC time above.
- Keep responses good enough for a chat interface.
- Keep naming relevant. Every reminder, note title should describe exactly what it is.
"""

_default_client = AsyncOpenAI(base_url=config.llm_base, api_key=config.llm_api_key, timeout=10.0, max_retries=0)

async def run_agent(user_message: str, acc_id: int, platform: str, chat_id: str | int, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
    # use default client UNLESS BYOK used
    # note: BYOK is todo
    client = (
        AsyncOpenAI(base_url=base_url or config.llm_base, api_key=api_key or config.llm_api_key, timeout=10.0, max_retries=0)
        if (base_url or api_key)
        else _default_client
    )
    active_model = model or config.llm_model

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(now_utc=to_iso(utc_now()))},
        {"role": "user", "content": user_message},
    ]

    try:
        async with asyncio.timeout(60):
            for _ in range(5):
                reponse = await client.chat.completions.create(model=active_model, messages=messages, tools=TOOL_SCHEMA, tool_choice="auto")
                msg = reponse.choices[0].message

                if not msg.tool_calls:
                    return msg.content or "Done."

                messages.append(msg.model_dump(exclude_none=True))

                for tc in msg.tool_calls:
                    try:
                        fn_args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = await execute_tool(name=tc.function.name, args=fn_args, acc_id=acc_id, platform=platform, chat_id=chat_id)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.function.name,
                            "content": result,
                        }
                    )
    except BadRequestError as exc:
        logger.warning("Bad request body: %s", exc.body)
        return "Sorry, bad request error. Please try again."
    except Exception as exc:
        logger.warning("Agent call failed: %s", exc)
        return "Sorry, agent calling failed. Please try again."

    return "Tool call limit exceeded, please rephrase and try again."