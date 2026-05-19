"""
Playwright browser session manager.
Creates isolated browser contexts per task and cleans up after completion.
"""
from contextlib import asynccontextmanager


@asynccontextmanager
async def browser_context():
    """
    Async context manager that yields a (browser, page) pair.
    Always cleans up, even on exception.
    """
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    try:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()
    finally:
        await pw.stop()


async def get_page_state(page) -> dict:
    """Return clean page state for the LLM (URL, title, visible text)."""
    try:
        url = page.url
        title = await page.title()
        # inner_text is much cleaner than innerHTML for LLM consumption
        text = await page.inner_text("body")
        # Collapse whitespace
        text = " ".join(text.split())
        return {"url": url, "title": title, "text": text[:2500]}
    except Exception as e:
        return {"url": page.url, "title": "unknown", "text": f"Error reading page: {e}"}
