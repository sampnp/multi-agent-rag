from typing import TypedDict


class AgentState(TypedDict):
    query: str
    request_id: str
    plan: list[str]
    research_results: list[dict]
    draft_response: str
    critique: str
    is_acceptable: bool
    final_response: str
    iteration: int
    memory_context: dict   # retrieved memories injected into execution
