from langgraph.graph import StateGraph, START, END

from app.agents.state import AgentState
from app.agents.nodes import (
    critic_node,
    execution_node,
    memory_node,
    planning_node,
    research_node,
)


def _route_critic(state: AgentState) -> str:
    # Allow at most 2 execution attempts
    if state["is_acceptable"] or state["iteration"] >= 2:
        return "memory"
    return "executor"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planning_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("executor", execution_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("memory", memory_node)

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "executor")
    workflow.add_edge("executor", "critic")
    workflow.add_conditional_edges("critic", _route_critic, {"memory": "memory", "executor": "executor"})
    workflow.add_edge("memory", END)

    return workflow.compile()


agent_graph = build_graph()
