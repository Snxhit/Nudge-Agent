import asyncio
from openai import AsyncOpenAI
from bot.config import config

# temp system prompt, replace later
SYSTEM_PROMPT = "You are Nudge, a concise, proactive personal assistant on Telegram."

_default_client = AsyncOpenAI(base_url=config.llm_base, api_key=config.llm_api_key)

async def run_agent(user_message: str, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> str:
    # use default client UNLESS BYOK used
    # note: BYOK is todfo
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