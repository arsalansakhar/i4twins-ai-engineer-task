"""LangGraph skeleton: START -> router -> selected execution path -> END."""

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.router import make_router_node
from app.skills.calculator import calculator_node
from app.skills.general_chat import general_chat_node
from app.skills.summarizer import summarizer_node
from app.skills.translator import translator_node
from app.state import AgentState


def _route_after_router(state: AgentState) -> str:
    decision = state["router_decision"]
    if len(decision.skills) == 1:
        return decision.skills[0]
    return "multi_skill"


def _multi_skill_placeholder(state: AgentState) -> dict[str, str]:
    decision = state["router_decision"]
    selected = " -> ".join(decision.skills)
    return {
        "final_response": (
            f"[Milestone 1] Multi-skill execution pending: "
            f"{decision.execution_mode}: {selected}"
        )
    }


def build_graph(llm: BaseChatModel | None = None):
    """Build the Milestone 1 graph.

    Single-skill requests already route to one of the four explicit skill
    nodes. Two-skill orchestration is deliberately isolated behind a control
    node for implementation in the next milestone.
    """

    graph = StateGraph(AgentState)

    graph.add_node("router", make_router_node(llm))
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("translator", translator_node)
    graph.add_node("calculator", calculator_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("multi_skill", _multi_skill_placeholder)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "summarizer": "summarizer",
            "translator": "translator",
            "calculator": "calculator",
            "general_chat": "general_chat",
            "multi_skill": "multi_skill",
        },
    )

    for node in ("summarizer", "translator", "calculator", "general_chat", "multi_skill"):
        graph.add_edge(node, END)

    return graph.compile()
