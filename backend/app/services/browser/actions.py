"""
Browser action executor.
Takes a structured action dict from the LLM and runs it on the Playwright page.
"""
import re
from urllib.parse import urlparse


_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        if host in _BLOCKED_HOSTS:
            return False
        # Block private IP ranges
        if re.match(r"^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.)", host):
            return False
        return True
    except Exception:
        return False


async def execute_action(page, action: dict) -> str:
    """
    Execute a single browser action. Returns a human-readable result string.
    action: {"action": "navigate|click|fill|extract|scroll_down|done", ...}
    """
    action_type = action.get("action", "done")

    if action_type == "navigate":
        url = action.get("url", "")
        if not url.startswith("http"):
            url = "https://" + url
        if not _is_safe_url(url):
            return f"Blocked navigation to unsafe URL: {url}"
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            title = await page.title()
            return f"Navigated to: {title} ({page.url})"
        except Exception as e:
            return f"Navigation failed: {e}"

    elif action_type == "click":
        text = action.get("text", "")
        selector = action.get("selector", "")
        try:
            if selector:
                await page.click(selector, timeout=5000)
            else:
                # Try text-based click first
                locator = page.get_by_text(text, exact=False).first
                await locator.click(timeout=5000)
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
            return f"Clicked: '{text or selector}'"
        except Exception as e:
            return f"Click failed: {e}"

    elif action_type == "fill":
        selector = action.get("selector", "input")
        value = action.get("value", "")
        try:
            await page.fill(selector, value, timeout=5000)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded", timeout=8000)
            return f"Filled '{selector}' with '{value}'"
        except Exception as e:
            return f"Fill failed: {e}"

    elif action_type == "scroll_down":
        try:
            await page.keyboard.press("End")
            await page.wait_for_timeout(800)
            return "Scrolled to bottom"
        except Exception as e:
            return f"Scroll failed: {e}"

    elif action_type == "search":
        query = action.get("query", "")
        encoded = query.replace(" ", "+")
        url = f"https://www.google.com/search?q={encoded}"
        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            return f"Searched Google for: {query}"
        except Exception as e:
            return f"Search failed: {e}"

    elif action_type == "done":
        return action.get("summary", "Task complete")

    return f"Unknown action: {action_type}"
