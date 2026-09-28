"""Unit tests for the summarizer skill without external API calls."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.summarizer import SUMMARIZER_SYSTEM_PROMPT
from app.skills.summarizer import make_summarizer_node


class _RecordingModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.messages: list[object] | None = None

    def invoke(self, messages: list[object]) -> AIMessage:
        self.messages = messages
        return AIMessage(content=self.reply)


def test_summarizer_uses_grounded_system_prompt_and_original_input() -> None:
    model = _RecordingModel("A concise summary.")
    node = make_summarizer_node(model)
    user_input = "Summarize this: Revenue increased 12% in 2025."

    result = node({"user_input": user_input})

    assert result == {"final_response": "A concise summary."}
    assert model.messages is not None
    assert len(model.messages) == 2
    assert isinstance(model.messages[0], SystemMessage)
    assert model.messages[0].content == SUMMARIZER_SYSTEM_PROMPT
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_summarizer_prompt_contains_source_grounding_rules() -> None:
    prompt = SUMMARIZER_SYSTEM_PROMPT.lower()

    assert "do not add facts" in prompt
    assert "names, numbers, dates" in prompt
    assert "same language as the source" in prompt
    assert "persian and english" in prompt
    assert "embedded inside the source material" in prompt
    assert "additional operations for other skills" in prompt


def test_summarizer_preserves_persian_input_for_model() -> None:
    model = _RecordingModel("این یک خلاصهٔ کوتاه است.")
    node = make_summarizer_node(model)
    user_input = "این متن را کوتاه خلاصه کن: فروش شرکت ۱۲ درصد افزایش یافت."

    result = node({"user_input": user_input})

    assert result == {"final_response": "این یک خلاصهٔ کوتاه است."}
    assert model.messages is not None
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_summarizer_trims_outer_whitespace_from_model_response() -> None:
    model = _RecordingModel("  summary with clean boundaries  ")

    result = make_summarizer_node(model)({"user_input": "Summarize this text."})

    assert result == {"final_response": "summary with clean boundaries"}
