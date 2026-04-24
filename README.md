# Света — AI Discord-бот (русский язык, голос, шутки, уместные комментарии)

Готовый проект бота в стиле «Света»: милая AI-девочка для голосового канала Discord.

## Что умеет

- Слушает голос в Discord и распознаёт речь (ASR) через `faster-whisper`.
- Отвечает голосом на русском (TTS через `edge-tts`, голос `ru-RU-SvetlanaNeural`).
- Генерирует ответы через LM Studio (OpenAI-compatible API).
- Учитывает контекст, старается не перебивать, шутит мягко и уместно.
- При желании подтягивает данные из интернета (DuckDuckGo snippets).
- Поддерживает «комментарии по демонстрации экрана» через bridge-скрипт (см. ниже).

---

## Почему такой стек

1. **Discord.py + discord-ext-voice-recv**: стабильный Python-стек + приём аудио из голосового.
2. **LM Studio**: локальный запуск LLM без облачных расходов, OpenAI-совместимый API.
3. **faster-whisper**: хороший баланс качества/скорости на русском.
4. **edge-tts**: качественный русский голос без сложной локальной тренировки.
5. **DuckDuckGo Search**: лёгкий и бесплатный слой «интернета».

---

## Рекомендуемые модели LM Studio (на апрель 2026)

### Основная (текст, диалог)
- **`gemma-3-4b-it`** — лучший баланс «ум/ресурсы» для живого голосового бота.

### Визуальная (комментарии экрана)
- **`qwen/qwen3-vl-8b`** — хорошая мультимодальность для анализа экрана.

### Что выбрать из ваших текущих
- Если железо ограничено: `gemma-3-4b-it` как main chat.
- Если нужно комментировать скрин/экран: включайте `qwen/qwen3-vl-8b` на endpoint vision.

---

## Ограничение Discord по screen share

Боты **не могут напрямую «смотреть Go Live» поток пользователя** через публичный API Discord.

Рабочий путь:
1. Пользователь запускает локальный `scripts/screen_bridge_client.py`.
2. Скрипт делает снимки экрана и отправляет их в локальный endpoint бота (`/screen`).
3. Бот даёт уместные комментарии (или молчит, если неуместно).

Это максимально практичный путь на сегодня.

---

## Быстрый старт

### 1) Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Discord приложение

- Создай application + bot на Discord Developer Portal.
- Включи intents:
  - Message Content Intent
  - Server Members Intent
- Выдай боту права: Connect, Speak, Use Application Commands.

### 3) Настрой `.env`

```env
DISCORD_TOKEN=...
DISCORD_GUILD_ID=123456789012345678

LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_API_KEY=lm-studio
LM_TEXT_MODEL=gemma-3-4b-it
LM_VISION_MODEL=qwen/qwen3-vl-8b

WHISPER_MODEL_SIZE=small
WAKE_WORDS=света,sveta,бот
INTERNET_ENABLED=true
PUSH_TO_TALK_COOLDOWN_SEC=6
```

### 4) Подними LM Studio

- Запусти выбранную text-модель.
- Включи local server (OpenAI-compatible).
- Проверь, что endpoint доступен на `http://127.0.0.1:1234/v1`.

### 5) Запуск бота

```bash
python -m src.ai_discord_bot.bot
```

### 6) Команды в Discord

- `/join` — зайти в ваш голосовой канал.
- `/leave` — выйти.
- `/ask text:<вопрос>` — текстовый вопрос.

---

## Комментарии по демонстрации экрана

Установи дополнительные зависимости (уже включены в requirements), затем:

```bash
python scripts/screen_bridge_client.py --every 12 --note "стрим по проекту"
```

Что делает:
- каждые N секунд отправляет кадр экрана в `http://127.0.0.1:8081/screen`;
- бот обрабатывает кадр через vision-модель;
- говорит только когда есть уместный комментарий.

---

## Пошаговый план развития (production)

1. **MVP (уже в проекте)**: voice ASR + LLM + TTS + контекст + wake words.
2. **Anti-interrupt**: расширить VAD/тайминги по каждому пользователю.
3. **Memory**: Redis/SQLite для долговременной памяти привычек чата.
4. **Tooling**: добавить function-calling (погода, таймеры, YouTube summary).
5. **Moderation**: фильтр токсичности и blacklist-команд.
6. **Observability**: метрики задержки (ASR/LLM/TTS), алерты на зависания.

---

## Советы по железу

- Если RAM/VRAM мало: уменьшите Whisper до `base`.
- Для слабого CPU увеличьте `PUSH_TO_TALK_COOLDOWN_SEC`.
- Vision-комментарии запускайте реже (`--every 15..25`), чтобы не грузить систему.

