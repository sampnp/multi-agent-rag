"""
LLM-driven autonomous navigation controller.
The LLM decides the next action at each step based on the task and current page state.
Inspired by the browser-use pattern but implemented directly with Playwright + Ollama.
"""
import asyncio
import json

from ollama import AsyncClient

from app.config import settings
from app.services.browser.actions import execute_action
from app.services.browser.extractor import extract_structured
from app.services.browser.session import get_page_state

MAX_STEPS = 12

_SYSTEM = """You are an autonomous web browsing agent. Your job is to complete a task by browsing the web step-by-step.

Available actions (output ONLY one JSON object per turn, no extra text):
{"action": "navigate", "url": "https://example.com"}
{"action": "search", "query": "your search query"}
{"action": "click", "text": "visible link or button text"}
{"action": "fill", "selector": "input[name='q']", "value": "text to type"}
{"action": "scroll_down"}
{"action": "extract", "description": "what structured data to extract from this page"}
{"action": "done", "summary": "brief summary of what was accomplished"}

Rules:
- Always start by navigating or searching
- After landing on a useful page, use extract before leaving
- Use 'done' when you have gathered enough information
- Do not navigate to private IPs, localhost, or file:// URLs
- Prefer well-known URLs when you know them (e.g. github.com/trending)"""


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def _decide_action(task: str, page_state: dict, gathered: list[dict], step: int) -> dict:
    data_summary = f"{len(gathered)} items extracted so far" if gathered else "nothing extracted yet"
    user_msg = (
        f"Task: {task}\n\n"
        f"Step {step}/{MAX_STEPS} | {data_summary}\n\n"
        f"Current page:\n"
        f"  URL: {page_state['url']}\n"
        f"  Title: {page_state['title']}\n"
        f"  Content: {page_state['text'][:1500]}"
    )
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = (resp.message.content or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].removeprefix("json").strip()
        # Handle case where model outputs multiple lines — take first JSON object
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return json.loads(raw)
    except Exception:
        return {"action": "done", "summary": "Could not decide next action"}


async def run_task(task: str, queue: asyncio.Queue) -> None:
    """
    Run the full autonomous browsing loop.
    Pushes SSE-compatible events to `queue`.
    """
    from app.services.browser.session import browser_context

    gathered_data: list[dict] = []
    step = 0

    try:
        async with browser_context() as page:
            for step in range(1, MAX_STEPS + 1):
                page_state = await get_page_state(page)
                action = await _decide_action(task, page_state, gathered_data, step)
                action_type = action.get("action", "done")

                # Emit step start
                await queue.put({
                    "type": "step_start",
                    "payload": {"step": step, "action": action_type, "detail": action},
                })

                if action_type == "extract":
                    description = action.get("description", "key information")
                    extracted = await extract_structured(page_state["text"], description, page_state["url"])
                    gathered_data.append({"step": step, "url": page_state["url"], "data": extracted})
                    await queue.put({
                        "type": "extracted",
                        "payload": {"step": step, "url": page_state["url"], "data": extracted},
                    })
                    result = f"Extracted data from {page_state['url']}"
                elif action_type == "done":
                    result = action.get("summary", "Task complete")
                    await queue.put({
                        "type": "step_done",
                        "payload": {"step": step, "action": action_type, "result": result},
                    })
                    break
                else:
                    result = await execute_action(page, action)

                await queue.put({
                    "type": "step_done",
                    "payload": {"step": step, "action": action_type, "result": result},
                })

                if action_type == "done":
                    break

                # Small pause between steps to be a polite browser
                await asyncio.sleep(0.5)

    except Exception as e:
        error_msg = str(e)
        if "Executable doesn't exist" in error_msg or "chromium" in error_msg.lower():
            error_msg = "Playwright browsers not installed. Run: playwright install chromium"
        await queue.put({"type": "error", "payload": {"message": error_msg}})
        gathered_data = []

    # Generate report
    if gathered_data:
        from app.services.browser.reporter import generate_report
        report = await generate_report(task, gathered_data)
        await queue.put({"type": "report", "payload": {"content": report, "steps": step}})
    else:
        await queue.put({"type": "report", "payload": {
            "content": f"No data was extracted after {step} steps.",
            "steps": step,
        }})

    await queue.put(None)  # sentinel
