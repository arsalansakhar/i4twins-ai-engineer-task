"""LLM-backed translator skill."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.prompts.translator import TRANSLATOR_SYSTEM_PROMPT
from app.state import AgentState


def make_translator_node(llm: BaseChatModel | None = None):
    """Return a LangGraph node that translates the user's requested text."""

    model = llm or get_llm()

    def translator_node(state: AgentState) -> dict[str, str]:
        response = model.invoke(
            [
                SystemMessage(content=TRANSLATOR_SYSTEM_PROMPT),
                HumanMessage(content=state["user_input"]),
            ]
        )
        if not isinstance(response.content, str):
            raise TypeError("Translator model returned non-text content.")
        return {"final_response": response.content.strip()}

    return translator_node
