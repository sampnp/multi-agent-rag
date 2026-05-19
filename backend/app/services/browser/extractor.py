"""
LLM-based structured data extraction from raw page text.
"""
import json

from ollama import AsyncClient

from app.config import settings


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def extract_structured(page_text: str, description: str, url: str) -> dict:
    """
    Ask the LLM to extract structured data from page text according to a description.
    Returns a dict with extracted fields (or {"items": [...]} for lists).
    """
    system = (
        "You are a data extraction assistant. Extract structured information from webpage text.\n"
        "Output ONLY valid JSON. Use arrays for lists of items.\n"
        "If a field is not found, use null."
    )
    user = (
        f"URL: {url}\n\n"
        f"What to extract: {description}\n\n"
        f"Page text:\n{page_text[:2000]}"
    )
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = (resp.message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        return json.loads(raw)
    except Exception:
        # Return raw text snippet as fallback
        return {"raw_excerpt": page_text[:500], "url": url}


async def extract_links(page) -> list[str]:
    """Return all href links from the current page."""
    try:
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href).filter(h => h.startsWith('http')).slice(0, 20)",
        )
        return links
    except Exception:
        return []
