"""Structured LLM routing node."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.prompts.router import ROUTER_SYSTEM_PROMPT
from app.state import AgentState, RouterDecision


def make_router_node(llm: BaseChatModel | None = None):
    """Return a LangGraph node that emits a validated RouterDecision."""

    model = llm or get_llm()
    structured_model = model.with_structured_output(
        RouterDecision,
        method="json_schema",
        strict=True,
    )

    def router_node(state: AgentState) -> dict[str, RouterDecision]:
        decision = structured_model.invoke(
            [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                HumanMessage(content=state["user_input"]),
            ]
        )
        return {"router_decision": decision}

    return router_node
