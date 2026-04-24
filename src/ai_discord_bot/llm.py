from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from .config import settings


SYSTEM_PROMPT = """
Ты Света — милая, умная и остроумная AI-девочка в голосовом Discord.
Правила:
1) Пиши и говори ТОЛЬКО по-русски.
2) Будь дружелюбной, короткой и по делу (1-3 предложения), с лёгкими шутками.
3) Не перебивай: если пользователь не обращался к тебе и контекст не требует ответа, верни [SILENCE].
4) Если просят мнение по теме — добавляй полезный комментарий.
5) Если не уверена, скажи честно и предложи уточнить.
6) Не выдумывай факты про интернет: используй блок INTERNET, если он дан.
""".strip()


@dataclass(slots=True)
class LLMReply:
    text: str
    should_speak: bool


class LMStudioClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.lm_studio_api_key,
            base_url=settings.lm_studio_base_url,
        )

    async def chat(self, user_text: str, context: str = "", internet: str = "") -> LLMReply:
        prompt = f"CONTEXT:\n{context or '-'}\n\nINTERNET:\n{internet or '-'}\n\nUSER:\n{user_text}"
        completion = await self.client.chat.completions.create(
            model=settings.lm_text_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=180,
        )
        text = (completion.choices[0].message.content or "").strip()
        if not text or text.upper() == "[SILENCE]":
            return LLMReply(text="", should_speak=False)
        return LLMReply(text=text, should_speak=True)

    async def vision_comment(self, description_payload: list[dict[str, Any]], context: str = "") -> str:
        completion = await self.client.chat.completions.create(
            model=settings.lm_vision_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты Света. Коротко и уместно комментируй скриншот только если это полезно. "
                        "Если нечего добавить — [SILENCE]."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Контекст разговора: {context or '-'}"},
                        *description_payload,
                    ],
                },
            ],
            max_tokens=120,
            temperature=0.4,
        )
        return (completion.choices[0].message.content or "").strip()
