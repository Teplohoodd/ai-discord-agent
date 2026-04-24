from __future__ import annotations

import asyncio
import base64
import logging
import tempfile
import time
import wave
from collections import deque
from pathlib import Path

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from discord.ext.voice_recv import AudioSink, VoiceRecvClient

from .config import settings
from .internet import web_context
from .llm import LMStudioClient
from .speech import SpeechEngine, run_blocking


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sveta-bot")


class BufferedSink(AudioSink):
    def __init__(self) -> None:
        super().__init__()
        self.buffers: dict[int, bytearray] = {}
        self.last_packet_at: dict[int, float] = {}

    def wants_opus(self) -> bool:
        return False

    def write(self, user: discord.Member | discord.User | None, data) -> None:
        if user is None:
            return
        self.buffers.setdefault(user.id, bytearray()).extend(data.pcm)
        self.last_packet_at[user.id] = time.time()

    def pop_ready(self, idle_after_sec: float = 1.6, min_bytes: int = 12000) -> list[tuple[int, bytes]]:
        ready: list[tuple[int, bytes]] = []
        now = time.time()
        for uid, buff in list(self.buffers.items()):
            if len(buff) < min_bytes:
                continue
            if now - self.last_packet_at.get(uid, now) < idle_after_sec:
                continue
            ready.append((uid, bytes(buff)))
            self.buffers[uid].clear()
        return ready


class SvetaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.speech = SpeechEngine()
        self.llm = LMStudioClient()
        self.voice_client_ref: VoiceRecvClient | None = None
        self.sink: BufferedSink | None = None
        self.dialog_context: deque[str] = deque(maxlen=8)
        self.last_bot_talk = 0.0

    async def setup_hook(self) -> None:
        guild = discord.Object(id=settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        await self._start_screen_bridge()
        log.info("Slash-команды синхронизированы")

    async def _start_screen_bridge(self) -> None:
        app = web.Application()

        async def handle_screen(request: web.Request) -> web.Response:
            payload = await request.json()
            image_base64 = payload.get("image_base64", "")
            note = payload.get("note", "")
            if not image_base64:
                return web.json_response({"ok": False, "error": "image_base64 required"}, status=400)
            context = "\n".join(self.dialog_context)
            image_url = f"data:image/jpeg;base64,{image_base64}"
            text = await self.llm.vision_comment(
                [
                    {"type": "text", "text": f"Примечание: {note or '-'}"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
                context=context,
            )
            if text and text.upper() != "[SILENCE]":
                self.dialog_context.append(f"Экран: {note}")
                self.dialog_context.append(f"Света: {text}")
                await self.speak_to_voice(text)
                return web.json_response({"ok": True, "spoken": True, "text": text})
            return web.json_response({"ok": True, "spoken": False})

        app.add_routes([web.post("/screen", handle_screen)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="127.0.0.1", port=8081)
        await site.start()
        log.info("Screen bridge listening on http://127.0.0.1:8081/screen")

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)

    async def speak_to_voice(self, text: str) -> None:
        if not self.voice_client_ref or self.voice_client_ref.is_playing():
            return
        mp3 = await self.speech.synthesize(text)
        source = discord.FFmpegPCMAudio(str(mp3))
        self.voice_client_ref.play(source, after=lambda _: mp3.unlink(missing_ok=True))
        self.last_bot_talk = time.time()

    async def process_audio_loop(self) -> None:
        while True:
            await asyncio.sleep(0.8)
            if not self.sink:
                continue
            for user_id, pcm in self.sink.pop_ready():
                user = self.get_user(user_id)
                if user is None:
                    continue
                text = await self._pcm_to_text(pcm)
                if not text:
                    continue
                lower = text.lower()
                addressed = any(w in lower for w in settings.wake_words)
                if not addressed and time.time() - self.last_bot_talk < settings.push_to_talk_cooldown_sec:
                    continue
                maybe_web = web_context(text) if ("найди" in lower or "кто такой" in lower) else ""
                context = "\n".join(self.dialog_context)
                reply = await self.llm.chat(text, context=context, internet=maybe_web)
                self.dialog_context.append(f"{user.display_name}: {text}")
                if reply.should_speak:
                    self.dialog_context.append(f"Света: {reply.text}")
                    await self.speak_to_voice(reply.text)

    async def _pcm_to_text(self, pcm: bytes) -> str:
        wav_path = Path(tempfile.mkstemp(suffix=".wav")[1])
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(48000)
            wf.writeframes(pcm)
        text = await run_blocking(self.speech.transcribe, wav_path)
        wav_path.unlink(missing_ok=True)
        return text


bot = SvetaBot()


@bot.tree.command(name="join", description="Света заходит в голосовой канал")
async def join(interaction: discord.Interaction) -> None:
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("Зайди в голосовой канал сначала", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    vc = await channel.connect(cls=VoiceRecvClient)
    sink = BufferedSink()
    vc.listen(sink)
    bot.voice_client_ref = vc
    bot.sink = sink
    asyncio.create_task(bot.process_audio_loop())
    await interaction.response.send_message("Я здесь ✨ Слушаю и не перебиваю.")


@bot.tree.command(name="leave", description="Света выходит из голосового")
async def leave(interaction: discord.Interaction) -> None:
    if bot.voice_client_ref:
        await bot.voice_client_ref.disconnect(force=True)
        bot.voice_client_ref = None
        bot.sink = None
    await interaction.response.send_message("Пока-пока!", ephemeral=True)


@bot.tree.command(name="ask", description="Текстовый вопрос Свете")
@app_commands.describe(text="Что спросить у Светы")
async def ask(interaction: discord.Interaction, text: str) -> None:
    ctx = "\n".join(bot.dialog_context)
    internet = web_context(text) if settings.internet_enabled else ""
    reply = await bot.llm.chat(text, context=ctx, internet=internet)
    if reply.should_speak:
        bot.dialog_context.append(f"{interaction.user.display_name}: {text}")
        bot.dialog_context.append(f"Света: {reply.text}")
        await interaction.response.send_message(reply.text)
    else:
        await interaction.response.send_message("🤫", ephemeral=True)


def main() -> None:
    settings.validate()
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
