"""Unit tests for the General Chat skill without external API calls."""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.prompts.general_chat import GENERAL_CHAT_SYSTEM_PROMPT
from app.skills.general_chat import make_general_chat_node


class _RecordingModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.messages: list[object] | None = None

    def invoke(self, messages: list[object]) -> AIMessage:
        self.messages = messages
        return AIMessage(content=self.reply)


def test_general_chat_uses_dedicated_prompt_and_original_input() -> None:
    model = _RecordingModel("Hello! How can I help?")
    node = make_general_chat_node(model)
    user_input = "Hi there!"

    result = node({"user_input": user_input})

    assert result == {"final_response": "Hello! How can I help?"}
    assert model.messages is not None
    assert len(model.messages) == 2
    assert isinstance(model.messages[0], SystemMessage)
    assert model.messages[0].content == GENERAL_CHAT_SYSTEM_PROMPT
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_general_chat_prompt_covers_fallback_behavior() -> None:
    prompt = GENERAL_CHAT_SYSTEM_PROMPT.lower()

    assert "greetings, small talk, and general questions" in prompt
    assert "persian and english" in prompt
    assert "ask one concise clarification" in prompt
    assert "do not mention internal routing" in prompt


def test_general_chat_preserves_persian_input_for_model() -> None:
    model = _RecordingModel("سلام! چطور می‌توانم کمک کنم؟")
    node = make_general_chat_node(model)
    user_input = "سلام، حالت چطوره؟"

    result = node({"user_input": user_input})

    assert result == {"final_response": "سلام! چطور می‌توانم کمک کنم؟"}
    assert model.messages is not None
    assert isinstance(model.messages[1], HumanMessage)
    assert model.messages[1].content == user_input


def test_general_chat_handles_general_question_response() -> None:
    model = _RecordingModel("A CPU executes general-purpose instructions.")
    node = make_general_chat_node(model)

    result = node({"user_input": "What does a CPU do?"})

    assert result == {
        "final_response": "A CPU executes general-purpose instructions."
    }


def test_general_chat_trims_outer_whitespace() -> None:
    model = _RecordingModel("  hello  ")

    result = make_general_chat_node(model)({"user_input": "Hi"})

    assert result == {"final_response": "hello"}
