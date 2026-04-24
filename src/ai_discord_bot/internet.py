from __future__ import annotations

from duckduckgo_search import DDGS

from .config import settings


def web_context(query: str, max_results: int = 3) -> str:
    if not settings.internet_enabled:
        return ""
    snippets: list[str] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            title = item.get("title", "Без названия")
            body = item.get("body", "")
            href = item.get("href", "")
            snippets.append(f"- {title}: {body} ({href})")
    return "\n".join(snippets)
