"""LangGraph workflow for routing requests to the four supported skills."""

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from app.llm import get_llm
from app.orchestration import make_multi_skill_node
from app.router import make_router_node
from app.skills.calculator import calculator_node
from app.skills.general_chat import make_general_chat_node
from app.skills.summarizer import make_summarizer_node
from app.skills.translator import make_translator_node
from app.state import AgentState, SkillName


def _route_after_router(state: AgentState) -> str:
    decision = state["router_decision"]
    if len(decision.skills) == 1:
        return decision.skills[0]
    return "multi_skill"


def build_graph(llm: BaseChatModel | None = None):
    """Build the agent graph with one shared configured LLM instance."""

    model = llm or get_llm()
    graph = StateGraph(AgentState)

    skill_nodes = {
        "summarizer": make_summarizer_node(model),
        "translator": make_translator_node(model),
        "calculator": calculator_node,
        "general_chat": make_general_chat_node(model),
    }

    graph.add_node("router", make_router_node(model))
    for skill_name, node in skill_nodes.items():
        graph.add_node(skill_name, node)
    graph.add_node(
        "multi_skill",
        make_multi_skill_node(skill_nodes),  # type: ignore[arg-type]
    )

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
