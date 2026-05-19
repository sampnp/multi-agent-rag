"""
LLM-based report generator from structured data gathered during browsing.
"""
import json

from ollama import AsyncClient

from app.config import settings

TEMPLATES = [
    {
        "id": "ai_hiring",
        "name": "AI Startup Hiring Report",
        "description": "Finds AI startups hiring engineers and extracts job info",
        "task": (
            "Search for AI startups that are actively hiring software engineers in 2025. "
            "Visit at least 2-3 company pages or job boards and extract: company name, "
            "job titles, locations, and tech stack. Use sites like wellfound.com, "
            "greenhouse.io, or LinkedIn jobs."
        ),
    },
    {
        "id": "github_trending",
        "name": "GitHub Trending Repos",
        "description": "Extracts today's top trending Python repositories from GitHub",
        "task": (
            "Navigate to github.com/trending?l=python and extract the top 10 trending "
            "Python repositories. For each repo get: repository name, owner, description, "
            "stars today, and total stars."
        ),
    },
    {
        "id": "hn_top",
        "name": "Hacker News Top Stories",
        "description": "Gets today's top 10 Hacker News stories",
        "task": (
            "Navigate to news.ycombinator.com and extract the top 10 front-page stories. "
            "For each story get: title, URL domain, points, and number of comments."
        ),
    },
    {
        "id": "product_hunt",
        "name": "Product Hunt Top Products",
        "description": "Scrapes today's top products from Product Hunt",
        "task": (
            "Navigate to producthunt.com and extract today's top 8 products. "
            "For each get: product name, tagline, upvotes, and category."
        ),
    },
]


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def generate_report(task: str, gathered_data: list[dict]) -> str:
    """Synthesize all extracted data into a structured markdown report."""
    data_str = json.dumps(gathered_data, indent=2)[:3000]
    system = (
        "You are a research report writer. Synthesize the extracted web data into a "
        "clear, structured markdown report. Use headings, bullet points, and tables "
        "where appropriate. Be concise but comprehensive."
    )
    user = f"Task: {task}\n\nExtracted data:\n{data_str}\n\nWrite the report:"
    try:
        client = _client()
        resp = await client.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.message.content or "Report generation failed."
    except Exception as e:
        return f"Report generation failed: {e}"
