"""LLM-backed translator skill."""

import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.prompts.translator import TRANSLATOR_SYSTEM_PROMPT
from app.state import AgentState

_RELATIVE_PERCENT_RE = re.compile(
    r"\b(?:reduced|decreased|increased|raised|lowered|cut)\b"
    r"[^.\n]*?\bby\s+(\d+(?:\.\d+)?)\s*(?:%|percent)\b",
    re.IGNORECASE,
)


def _preserve_quantitative_direction(source: str, translation: str) -> str:
    """Repair a narrow, high-impact English-to-Persian direction reversal.

    Small models sometimes render ``changed by N percent`` as Persian
    ``changed to N percent``. Only that explicit contradiction is corrected;
    the function does not attempt general translation post-processing.
    """

    result = translation
    for match in _RELATIVE_PERCENT_RE.finditer(source):
        number = match.group(1)
        digit_variants = {number, number.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))}
        for digits in digit_variants:
            result = re.sub(
                rf"به\s+{re.escape(digits)}\s*درصد\s+(?=(?:کاهش|افزایش))",
                f"{digits} درصد ",
                result,
            )
    return result


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
        translated = _preserve_quantitative_direction(
            state["user_input"],
            response.content.strip(),
        )
        return {"final_response": translated}

    return translator_node
