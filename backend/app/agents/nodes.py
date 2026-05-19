import asyncio
import json
import time

from ollama import AsyncClient

from app.agents.state import AgentState
from app.config import settings

# Registry of SSE queues keyed by request_id — populated by the chat router
status_queues: dict[str, asyncio.Queue] = {}

CHAT_MODEL = "llama3.1"


def _client() -> AsyncClient:
    return AsyncClient(host=f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}")


async def _emit(request_id: str, agent: str, status: str, message: str = "") -> None:
    q = status_queues.get(request_id)
    if q:
        await q.put({
            "type": "agent_status",
            "payload": {"agent": agent, "status": status, "message": message},
        })


async def _llm(system: str, user: str) -> str:
    resp = await _client().chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.message.content or ""


# ── Planning Agent ────────────────────────────────────────────────────────────

async def _track(agent: str, start: float, success: bool = True) -> None:
    try:
        from app.services.eval.agent_tracker import record_success, record_failure
        elapsed_ms = (time.time() - start) * 1000
        if success:
            await record_success(agent, elapsed_ms)
        else:
            await record_failure(agent)
    except Exception:
        pass


async def planning_node(state: AgentState) -> dict:
    _t0 = time.time()
    await _emit(state["request_id"], "Planner", "running", "Retrieving memory & breaking down query…")

    # Retrieve memory context before planning
    memory_context: dict = {}
    try:
        from app.services.memory.manager import retrieve_context
        memory_context = await retrieve_context(state["query"])
    except Exception:
        pass

    system = (
        "You are a planning assistant. Break the user query into 2-3 specific subtasks. "
        "Output ONLY a valid JSON array of strings, nothing else."
    )

    # Inject summary and recent history as context if available
    user_input = state["query"]
    if memory_context.get("summary"):
        user_input = f"[Conversation summary so far]\n{memory_context['summary']}\n\n{user_input}"
    if memory_context.get("recent_history"):
        last = memory_context["recent_history"][-1]
        user_input += f"\n\n[Last turn] Q: {last['query']}"

    raw = await _llm(system, user_input)

    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1].removeprefix("json").strip()
        plan: list[str] = json.loads(text)
        if not isinstance(plan, list):
            raise ValueError
    except Exception:
        plan = [state["query"]]

    mem_hint = ""
    if memory_context.get("relevant_memories"):
        mem_hint = f" ({len(memory_context['relevant_memories'])} past memories recalled)"
    await _emit(state["request_id"], "Planner", "done", f"{len(plan)} subtasks created{mem_hint}")
    await _track("Planner", _t0)
    return {"plan": plan, "iteration": 0, "memory_context": memory_context}


# ── Research Agent ────────────────────────────────────────────────────────────

async def research_node(state: AgentState) -> dict:
    _t0 = time.time()
    await _emit(state["request_id"], "Researcher", "running", "Classifying query and routing retrieval…")

    retrieval: dict = {"results": [], "strategies_used": ["vector"], "reasoning": "", "source_counts": {}}
    try:
        from app.services.retrieval.router import adaptive_retrieve
        retrieval = await adaptive_retrieve(state["query"])
    except Exception:
        pass

    results = retrieval["results"]
    strategies = retrieval["strategies_used"]
    source_counts = retrieval["source_counts"]

    # Emit retrieval trace so the frontend can show which paths were used
    q = status_queues.get(state["request_id"])
    if q:
        await q.put({
            "type": "retrieval_trace",
            "payload": {
                "strategies_used": strategies,
                "reasoning": retrieval["reasoning"],
                "source_counts": source_counts,
                "total_results": len(results),
            },
        })

    paths_label = " + ".join(strategies)
    msg = f"[{paths_label}] Found {len(results)} results" if results else f"[{paths_label}] No results — using general knowledge"
    await _emit(state["request_id"], "Researcher", "done", msg)
    await _track("Researcher", _t0)
    return {"research_results": results}


# ── Execution Agent ───────────────────────────────────────────────────────────

async def execution_node(state: AgentState) -> dict:
    _t0 = time.time()
    await _emit(state["request_id"], "Executor", "running", "Generating response…")

    context = "\n\n".join(
        f"[Source {i+1} via {r.get('source', 'unknown')}]: {r['text']}"
        for i, r in enumerate(state["research_results"])
    ) if state["research_results"] else ""

    plan_text = "\n".join(f"- {t}" for t in state["plan"]) or f"- {state['query']}"
    revision_note = (
        f"\n\nPrevious response had issues: {state['critique']}. Please fix them."
        if state["critique"] and state["iteration"] > 0 else ""
    )

    # Build memory preamble
    mem = state.get("memory_context", {})
    memory_preamble = ""
    if mem.get("summary"):
        memory_preamble += f"\n\n[Memory Summary]\n{mem['summary']}"
    if mem.get("relevant_memories"):
        snippets = "\n".join(
            f"- Q: {m['query'][:80]} → A: {m['response'][:120]}"
            for m in mem["relevant_memories"]
        )
        memory_preamble += f"\n\n[Relevant Past Conversations]\n{snippets}"
    if mem.get("recent_history"):
        hist = "\n".join(
            f"User: {h['query'][:80]}\nAssistant: {h['response'][:120]}"
            for h in mem["recent_history"][-3:]
        )
        memory_preamble += f"\n\n[Recent History]\n{hist}"

    user_msg = f"Query: {state['query']}\n\nSubtasks:\n{plan_text}"
    if context:
        user_msg += f"\n\nRetrieved Context:\n{context}"
    if memory_preamble:
        user_msg += memory_preamble
    user_msg += revision_note

    system = (
        "You are a helpful enterprise AI assistant. Answer the query thoroughly "
        "using the provided context and memory. Cite sources where relevant."
    )

    q = status_queues.get(state["request_id"])
    if q:
        await q.put({"type": "stream_start", "payload": {}})

    stream = await _client().chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        stream=True,
    )

    full_response = ""
    async for part in stream:
        token = part.message.content
        if token:
            full_response += token
            if q:
                await q.put({"type": "chat_token", "payload": {"token": token}})

    if q:
        await q.put({"type": "stream_end", "payload": {}})

    await _emit(state["request_id"], "Executor", "done", "Response generated")
    await _track("Executor", _t0)
    return {"draft_response": full_response, "iteration": state["iteration"] + 1}


# ── Critic Agent ──────────────────────────────────────────────────────────────

async def critic_node(state: AgentState) -> dict:
    _t0 = time.time()
    await _emit(state["request_id"], "Critic", "running", "Evaluating quality…")

    system = (
        "You are a quality critic. Evaluate the response for accuracy, completeness, and clarity. "
        'Output ONLY valid JSON: {"is_acceptable": true/false, "critique": "brief feedback"}'
    )
    user_msg = f"Query: {state['query']}\n\nResponse:\n{state['draft_response']}"

    raw = await _llm(system, user_msg)
    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1].removeprefix("json").strip()
        result = json.loads(text)
        is_acceptable: bool = bool(result.get("is_acceptable", True))
        critique: str = str(result.get("critique", ""))
    except Exception:
        is_acceptable = True
        critique = "Evaluation complete"

    label = "Approved" if is_acceptable else f"Needs revision: {critique[:60]}"
    await _emit(state["request_id"], "Critic", "done", label)
    await _track("Critic", _t0)
    return {"critique": critique, "is_acceptable": is_acceptable}


# ── Memory Agent ──────────────────────────────────────────────────────────────

async def memory_node(state: AgentState) -> dict:
    _t0 = time.time()
    await _emit(state["request_id"], "Memory", "running", "Saving to all memory layers…")

    save_info: dict = {}
    try:
        from app.services.memory.manager import save
        save_info = await save(state["query"], state["draft_response"])
    except Exception:
        pass

    # Emit memory trace event
    q = status_queues.get(state["request_id"])
    if q:
        await q.put({
            "type": "memory_saved",
            "payload": save_info,
        })

    label = "Saved"
    if save_info.get("short_term_entries"):
        label += f" · {save_info['short_term_entries']} turns in history"
    if save_info.get("compressed"):
        label += " · history compressed"
    await _emit(state["request_id"], "Memory", "done", label)
    await _track("Memory", _t0)

    # Sentinel — SSE generator exits on None
    if q:
        await q.put(None)

    return {"final_response": state["draft_response"]}
