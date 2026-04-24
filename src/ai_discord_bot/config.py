from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Settings:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    discord_guild_id: int = int(os.getenv("DISCORD_GUILD_ID", "0"))
    lm_studio_base_url: str = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    lm_studio_api_key: str = os.getenv("LM_STUDIO_API_KEY", "lm-studio")
    lm_text_model: str = os.getenv("LM_TEXT_MODEL", "gemma-3-4b-it")
    lm_vision_model: str = os.getenv("LM_VISION_MODEL", "qwen/qwen3-vl-8b")
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    wake_words: tuple[str, ...] = tuple(
        w.strip().lower() for w in os.getenv("WAKE_WORDS", "света,sveta,бот").split(",")
    )
    internet_enabled: bool = os.getenv("INTERNET_ENABLED", "true").lower() == "true"
    push_to_talk_cooldown_sec: float = float(os.getenv("PUSH_TO_TALK_COOLDOWN_SEC", "6"))

    def validate(self) -> None:
        if not self.discord_token:
            raise ValueError("DISCORD_TOKEN is required")
        if self.discord_guild_id <= 0:
            raise ValueError("DISCORD_GUILD_ID must be set to your server id")


settings = Settings()
