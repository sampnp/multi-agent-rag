"""
LLM-as-judge evaluation metrics (RAGAS-equivalent, fully local via Ollama).

Metrics implemented:
  faithfulness        — are all claims in the answer supported by the context?
  answer_relevancy    — does the answer address the question?
  context_precision   — are the retrieved contexts relevant to the question?
  hallucination_score — 1.0 - faithfulness (derived)

Each metric returns a dict: {score: float, reasoning: str}
All scores are 0.0–1.0 (higher is better, except hallucination_score).
"""
import asyncio
import re

from ollama import AsyncClient
from app.config import settings

_MODEL = "llama3.1"


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


def _parse_score(text: str) -> float:
    """Extract the first float 0.0–1.0 from an LLM response."""
    matches = re.findall(r"\b([01](?:\.\d+)?|\d*\.\d+)\b", text)
    for m in matches:
        v = float(m)
        if 0.0 <= v <= 1.0:
            return round(v, 3)
    # fallback: look for single digit 0-9 / 10 scale
    digit = re.search(r"\b([0-9]|10)\b", text)
    if digit:
        return round(int(digit.group(1)) / 10, 2)
    return 0.5


async def _judge(system: str, user: str) -> tuple[float, str]:
    try:
        resp = await _client().chat(
            model=_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw = resp.message.content or ""
        score = _parse_score(raw)
        return score, raw[:300]
    except Exception as e:
        return 0.5, f"Eval error: {e}"


async def score_faithfulness(question: str, answer: str, contexts: list[str]) -> dict:
    """Rate whether every claim in the answer is supported by the provided contexts."""
    ctx_text = "\n---\n".join(f"[Context {i+1}]: {c[:600]}" for i, c in enumerate(contexts[:5]))
    system = (
        "You are an evaluation judge. Your task is to assess if a given answer is fully "
        "grounded in the provided context (i.e. no hallucinations). "
        "Respond with a score from 0.0 to 1.0 where 1.0 means every claim is fully supported "
        "by the context, and 0.0 means the answer contains significant unsupported claims. "
        "Start your response with the numeric score on its own line, then briefly explain."
    )
    user = f"Question: {question}\n\nAnswer: {answer}\n\nContext:\n{ctx_text}"
    score, reasoning = await _judge(system, user)
    return {"score": score, "reasoning": reasoning}


async def score_answer_relevancy(question: str, answer: str) -> dict:
    """Rate whether the answer actually addresses what the question asked."""
    system = (
        "You are an evaluation judge. Rate how well the given answer addresses the question. "
        "Score 0.0 to 1.0: 1.0 = directly and completely answers the question, "
        "0.0 = completely off-topic or refuses to answer. "
        "Start with the numeric score, then briefly explain."
    )
    user = f"Question: {question}\n\nAnswer: {answer}"
    score, reasoning = await _judge(system, user)
    return {"score": score, "reasoning": reasoning}


async def score_context_precision(question: str, contexts: list[str]) -> dict:
    """Rate whether the retrieved context chunks are relevant to the question."""
    if not contexts:
        return {"score": 0.0, "reasoning": "No contexts provided"}
    ctx_text = "\n---\n".join(f"[Context {i+1}]: {c[:400]}" for i, c in enumerate(contexts[:5]))
    system = (
        "You are an evaluation judge. Rate how relevant the retrieved context chunks are "
        "for answering the question. Score 0.0–1.0: 1.0 = all chunks are highly relevant, "
        "0.0 = none are relevant. Start with the numeric score, then briefly explain."
    )
    user = f"Question: {question}\n\nRetrieved Contexts:\n{ctx_text}"
    score, reasoning = await _judge(system, user)
    return {"score": score, "reasoning": reasoning}


async def evaluate_response(
    question: str,
    answer: str,
    contexts: list[str],
) -> dict[str, dict]:
    """Run all metrics concurrently and return a dict keyed by metric name."""
    faith_task = asyncio.create_task(score_faithfulness(question, answer, contexts))
    rel_task = asyncio.create_task(score_answer_relevancy(question, answer))
    prec_task = asyncio.create_task(score_context_precision(question, contexts))

    faith, rel, prec = await asyncio.gather(faith_task, rel_task, prec_task)

    hallucination = {"score": round(1.0 - faith["score"], 3), "reasoning": "Derived: 1 − faithfulness"}

    return {
        "faithfulness": faith,
        "answer_relevancy": rel,
        "context_precision": prec,
        "hallucination_score": hallucination,
    }
