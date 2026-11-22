import asyncio
from openai import AsyncOpenAI
from bot.config import config

SYSTEM_PROMPT = "You are Nudge, a concise, proactive personal assistant on Telegram. Your job is to act as an assistant, and only reply with whatever the user says, that is worth noting for you. If the user tells you there's an event coming up tomorrow, that is important for you. If the user tells you the sky is blue, that is not relevant for you, so you don't consider that. The format of the reply should be: One heading and then every important event you noted from the user's prompt in bullet points."

_default_client = AsyncOpenAI(base_url=config.llm_base, api_key=config.llm_api_key)

async def run_agent(user_message: str, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> str:
    # use default client UNLESS BYOK used
    # note: BYOK is todo
    if base_url or api_key:
        client = AsyncOpenAI(base_url=base_url or config.llm_base, api_key=api_key or config.llm_api_key)
    else:
        client = _default_client

    response = await client.chat.completions.create(
        model=model or config.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or "..."