"""
Benchmark runner: evaluates a list of (query, response, contexts) triples,
stores every metric score to eval_results, and returns a summary.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal as async_session
from app.models.eval_result import EvalResult
from app.services.eval.metrics import evaluate_response

# Built-in benchmark test cases (question, golden_answer_hint)
DEFAULT_CASES: list[dict] = [
    {
        "query": "What is the purpose of this enterprise AI system?",
        "response": "This system is an enterprise AI operating system that combines multi-agent orchestration, adaptive retrieval, layered memory, and knowledge graph capabilities to answer questions and automate workflows.",
        "contexts": [],
    },
    {
        "query": "How does the adaptive retrieval engine work?",
        "response": "The adaptive retrieval engine classifies the query intent and routes it to the most appropriate retrieval path: vector similarity search, BM25 keyword search, knowledge graph traversal, or live web search. Results from all active paths are merged and re-ranked.",
        "contexts": [],
    },
    {
        "query": "What is the capital of France?",
        "response": "The capital of France is the Eiffel Tower.",  # intentional wrong answer to test hallucination
        "contexts": ["France is a country in Western Europe. Its capital city is Paris."],
    },
]


async def run_benchmark(
    cases: list[dict] | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Evaluate a list of test cases.
    Each case: {query, response, contexts}
    Returns: {run_id, timestamp, cases_evaluated, avg_scores, results}
    """
    cases = cases or DEFAULT_CASES
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    all_results = []

    async def _save_metrics(case: dict) -> dict:
        scores = await evaluate_response(
            question=case["query"],
            answer=case["response"],
            contexts=case.get("contexts", []),
        )
        rows = []
        for metric_name, metric_data in scores.items():
            rows.append(EvalResult(
                run_id=run_id,
                query=case["query"],
                response=case["response"],
                contexts=case.get("contexts"),
                metric_name=metric_name,
                score=metric_data["score"],
                details={"reasoning": metric_data.get("reasoning", "")},
            ))
        return {"query": case["query"], "scores": {k: v["score"] for k, v in scores.items()}}

    import asyncio
    all_results = await asyncio.gather(*[_save_metrics(c) for c in cases])

    # Persist to DB
    own_session = session is None
    db = session or async_session()
    try:
        if own_session:
            async with db as s:
                for case_result in all_results:
                    for metric_name, score in case_result["scores"].items():
                        s.add(EvalResult(
                            run_id=run_id,
                            query=case_result["query"],
                            response=next(
                                c["response"] for c in cases if c["query"] == case_result["query"]
                            ),
                            metric_name=metric_name,
                            score=score,
                        ))
                await s.commit()
    except Exception:
        pass

    # Compute average scores across all cases
    avg: dict[str, list[float]] = {}
    for r in all_results:
        for m, s in r["scores"].items():
            avg.setdefault(m, []).append(s)
    avg_scores = {m: round(sum(v) / len(v), 3) for m, v in avg.items()}

    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "cases_evaluated": len(cases),
        "avg_scores": avg_scores,
        "results": all_results,
    }


async def get_recent_runs(limit: int = 20) -> list[dict]:
    """Return the last N distinct run_ids with their avg scores."""
    try:
        async with async_session() as s:
            rows = await s.execute(
                select(
                    EvalResult.run_id,
                    sa_func.min(EvalResult.timestamp).label("timestamp"),
                    EvalResult.metric_name,
                    sa_func.avg(EvalResult.score).label("avg_score"),
                )
                .group_by(EvalResult.run_id, EvalResult.metric_name)
                .order_by(sa_func.min(EvalResult.timestamp).desc())
                .limit(limit * 4)  # 4 metrics per run
            )
            records = rows.fetchall()

        # Group by run_id
        runs: dict[str, dict] = {}
        for row in records:
            rid = row.run_id
            if rid not in runs:
                runs[rid] = {"run_id": rid, "timestamp": row.timestamp.isoformat(), "scores": {}}
            runs[rid]["scores"][row.metric_name] = round(float(row.avg_score), 3)

        return list(runs.values())[:limit]
    except Exception:
        return []


async def get_aggregate_stats() -> dict:
    """Return overall average per metric across all stored results."""
    try:
        async with async_session() as s:
            rows = await s.execute(
                select(
                    EvalResult.metric_name,
                    sa_func.avg(EvalResult.score).label("avg"),
                    sa_func.count(EvalResult.id).label("count"),
                ).group_by(EvalResult.metric_name)
            )
            return {
                row.metric_name: {"avg": round(float(row.avg), 3), "count": row.count}
                for row in rows.fetchall()
            }
    except Exception:
        return {}
