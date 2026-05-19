"""
Jira REST API integration for creating tasks from meeting action items.
If JIRA_BASE_URL is not configured, returns simulated issue keys.
"""
import httpx

from app.config import settings


def _is_configured() -> bool:
    return bool(settings.JIRA_BASE_URL and settings.JIRA_USERNAME and settings.JIRA_API_TOKEN)


async def create_issues(action_items: list[dict]) -> list[dict]:
    """
    Push action items to Jira as tasks.
    Returns list of {task, key, url, status}.
    """
    results = []

    if not _is_configured():
        # Simulate Jira response when not configured
        for i, item in enumerate(action_items, start=1):
            results.append({
                "task": item.get("task", ""),
                "key": f"{settings.JIRA_PROJECT_KEY}-{1000 + i}",
                "url": f"https://your-jira.atlassian.net/browse/{settings.JIRA_PROJECT_KEY}-{1000 + i}",
                "status": "simulated (Jira not configured)",
            })
        return results

    auth = (settings.JIRA_USERNAME, settings.JIRA_API_TOKEN)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    base = settings.JIRA_BASE_URL.rstrip("/")

    async with httpx.AsyncClient(auth=auth, headers=headers, timeout=10.0) as client:
        for item in action_items:
            desc = f"Owner: {item.get('owner', 'TBD')}\nDue: {item.get('due', 'TBD')}\nPriority: {item.get('priority', 'medium')}"
            payload = {
                "fields": {
                    "project": {"key": settings.JIRA_PROJECT_KEY},
                    "summary": item.get("task", "Action item"),
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [{"type": "paragraph", "content": [{"type": "text", "text": desc}]}],
                    },
                    "issuetype": {"name": "Task"},
                    "priority": {"name": item.get("priority", "medium").capitalize()},
                }
            }
            try:
                resp = await client.post(f"{base}/rest/api/3/issue", json=payload)
                resp.raise_for_status()
                data = resp.json()
                results.append({
                    "task": item.get("task", ""),
                    "key": data["key"],
                    "url": f"{base}/browse/{data['key']}",
                    "status": "created",
                })
            except Exception as e:
                results.append({
                    "task": item.get("task", ""),
                    "key": "",
                    "url": "",
                    "status": f"error: {e}",
                })

    return results
