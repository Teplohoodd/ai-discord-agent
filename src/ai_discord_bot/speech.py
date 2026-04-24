from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import edge_tts
from faster_whisper import WhisperModel

from .config import settings


class SpeechEngine:
    def __init__(self) -> None:
        self.model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path: Path) -> str:
        segments, _ = self.model.transcribe(str(audio_path), language="ru", vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()

    async def synthesize(self, text: str) -> Path:
        target = Path(tempfile.mkstemp(suffix=".mp3")[1])
        communicate = edge_tts.Communicate(text, voice="ru-RU-SvetlanaNeural")
        await communicate.save(str(target))
        return target


async def run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)
