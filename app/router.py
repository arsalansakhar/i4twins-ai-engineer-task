"""Structured LLM routing node."""

import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.prompts.router import ROUTER_SYSTEM_PROMPT
from app.state import AgentState, RouterDecision

_EN_SEQUENTIAL_SUMMARY_TRANSLATION = re.compile(
    r"\bsummari[sz]e\b.*(?:\band\s+then\b|\bthen\b).*\btranslate\b"
    r"|\bsummari[sz]e\b.*\btranslate\s+the\s+summary\b",
    re.IGNORECASE | re.DOTALL,
)


def _enforce_explicit_workflow(
    user_input: str,
    decision: RouterDecision,
) -> RouterDecision:
    """Correct only explicit, high-confidence workflow contradictions."""

    english_match = _EN_SEQUENTIAL_SUMMARY_TRANSLATION.search(user_input)
    persian_match = (
        "خلاصه" in user_input
        and "ترجمه" in user_input
        and any(cue in user_input for cue in ("و بعد", "سپس", "بعد از"))
    )
    if english_match or persian_match:
        return RouterDecision(
            skills=["summarizer", "translator"],
            execution_mode="sequential",
        )
    return decision


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
        decision = _enforce_explicit_workflow(state["user_input"], decision)
        return {"router_decision": decision}

    return router_node
