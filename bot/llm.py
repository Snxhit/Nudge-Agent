import asyncio
import json
from openai import AsyncOpenAI
from bot.config import config
from bot.tools import (TOOL_SCHEMA, execute_tool)

SYSTEM_PROMPT = "You are Nudge, a concise, proactive personal assistant on Telegram. Your job is to act as an assistant, and only reply with whatever the user says, that is worth noting for you. If the user tells you there's an event coming up tomorrow, that is important for you. If the user tells you the sky is blue, that is not relevant for you, so you don't consider that. The format of the reply should be: One heading and then every important event you noted from the user's prompt in bullet points. "

_default_client = AsyncOpenAI(base_url=config.llm_base, api_key=config.llm_api_key)

async def run_agent(user_message: str, acc_id: int, platform: str, chat_id: str | int, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
    # use default client UNLESS BYOK used
    # note: BYOK is todo
    client = (
        AsyncOpenAI(base_url=base_url or config.llm_base, api_key=api_key or config.llm_api_key)
        if (base_url or api_key)
        else _default_client
    )
    active_model = model or config.llm_model

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for i in range(5):
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
                    "content": result,
                }
            )

    return "Tool call limit exceeded, please rephrase and try again."