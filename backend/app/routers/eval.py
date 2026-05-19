"""
Evaluation & Observability API.

GET  /api/eval/stats           — aggregate metric averages + agent success rates
GET  /api/eval/runs            — list of recent eval runs
POST /api/eval/run             — trigger a benchmark run (async, returns immediately)
POST /api/eval/score           — score a single query/response pair on-demand
GET  /api/eval/agent-stats     — per-agent success/failure/latency breakdown
"""
import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.services.eval.agent_tracker import get_stats as get_agent_stats
from app.services.eval.benchmark import get_aggregate_stats, get_recent_runs, run_benchmark
from app.services.eval.metrics import evaluate_response

router = APIRouter(prefix="/eval", tags=["eval"])


def _require_auth(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


class ScoreRequest(BaseModel):
    query: str
    response: str
    contexts: list[str] = []


class BenchmarkRequest(BaseModel):
    cases: list[dict] | None = None


@router.get("/stats")
async def eval_stats(_: str = Depends(_require_auth)):
    metric_stats, agent_stats = await asyncio.gather(
        get_aggregate_stats(),
        get_agent_stats(),
    )
    return {"metrics": metric_stats, "agents": agent_stats}


@router.get("/runs")
async def eval_runs(_: str = Depends(_require_auth)):
    runs = await get_recent_runs(limit=20)
    return {"runs": runs, "total": len(runs)}


@router.get("/agent-stats")
async def agent_stats(_: str = Depends(_require_auth)):
    stats = await get_agent_stats()
    return {"agents": stats}


@router.post("/score")
async def score_single(req: ScoreRequest, _: str = Depends(_require_auth)):
    """Score a single response on all metrics (synchronous, takes ~5–15s)."""
    results = await evaluate_response(req.query, req.response, req.contexts)
    return {
        "query": req.query,
        "scores": {k: {"score": v["score"], "reasoning": v.get("reasoning", "")} for k, v in results.items()},
    }


@router.post("/run")
async def trigger_benchmark(
    req: BenchmarkRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(_require_auth),
):
    """Kick off a benchmark run in the background. Returns run_id immediately."""
    run_id = str(uuid.uuid4())
    background_tasks.add_task(run_benchmark, req.cases)
    return {"run_id": run_id, "status": "started", "message": "Benchmark running in background"}
