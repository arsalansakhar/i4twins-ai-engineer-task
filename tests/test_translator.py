"""Unit tests for the translator skill without external API calls."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.translator import TRANSLATOR_SYSTEM_PROMPT
from app.skills.translator import make_translator_node


class _RecordingModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.messages: list[object] | None = None

    def invoke(self, messages: list[object]) -> AIMessage:
        self.messages = messages
        return AIMessage(content=self.reply)


def test_translator_uses_dedicated_prompt_and_original_input() -> None:
    model = _RecordingModel("سلام دنیا")
    node = make_translator_node(model)
    user_input = "Translate 'Hello world' to Persian."

    result = node({"user_input": user_input})

    assert result == {"final_response": "سلام دنیا"}
    assert model.messages is not None
    assert len(model.messages) == 2
    assert isinstance(model.messages[0], SystemMessage)
    assert model.messages[0].content == TRANSLATOR_SYSTEM_PROMPT
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_translator_prompt_treats_source_instructions_as_content() -> None:
    prompt = TRANSLATOR_SYSTEM_PROMPT.lower()

    assert "do not answer questions" in prompt
    assert "content to translate" in prompt
    assert "do not add explanations" in prompt
    assert "ask one concise clarification" in prompt
    assert "persian and english" in prompt
    assert "additional operations for other skills" in prompt


def test_translator_preserves_persian_request_for_model() -> None:
    model = _RecordingModel("The system pressure is 46.3 bar.")
    node = make_translator_node(model)
    user_input = "این جمله را به انگلیسی ترجمه کن: فشار سیستم ۴۶.۳ بار است."

    result = node({"user_input": user_input})

    assert result == {"final_response": "The system pressure is 46.3 bar."}
    assert model.messages is not None
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_translator_does_not_preprocess_question_like_source_text() -> None:
    model = _RecordingModel("پایتخت فرانسه چیست؟")
    node = make_translator_node(model)
    user_input = "Translate to Persian: What is the capital of France?"

    result = node({"user_input": user_input})

    assert result == {"final_response": "پایتخت فرانسه چیست؟"}
    assert model.messages is not None
    assert model.messages[1].content == user_input


def test_translator_trims_outer_whitespace() -> None:
    model = _RecordingModel("  translated text  ")

    result = make_translator_node(model)({"user_input": "Translate this to Persian."})

    assert result == {"final_response": "translated text"}
