import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _require_env(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env: {name}")
    return val

@dataclass(frozen=True)
class Config:
    telegram_token: str
    admin_uid: str
    llm_base: str
    llm_api_key: str
    llm_model: str

config = Config(
    telegram_token=_require_env("TELEGRAM_BOT_TOKEN"),
    admin_uid=int(os.getenv("ADMIN_USER_ID", "0")),
    llm_base=_require_env("LLM_BASE_URL"),
    llm_api_key=_require_env("LLM_API_KEY"),
    llm_model=_require_env("LLM_MODEL"),
)