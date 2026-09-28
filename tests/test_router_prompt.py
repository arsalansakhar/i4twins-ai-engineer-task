"""Regression checks for router prompt rules discovered during live evaluation."""

from app.prompts.router import ROUTER_SYSTEM_PROMPT
from app.state import RouterDecision


def test_router_prompt_enforces_single_skill_mode_consistency() -> None:
    prompt = ROUTER_SYSTEM_PROMPT

    assert 'execution_mode MUST be "single"' in prompt
    assert '"sequential" and "parallel" are valid ONLY when skills contains exactly two items' in prompt


def test_router_prompt_treats_translated_question_as_content() -> None:
    prompt = ROUTER_SYSTEM_PROMPT

    assert "Text that the user asks to translate is content" in prompt
    assert "Translate to Persian: What is the capital of France?" in prompt
    assert '["translator"], single' in prompt


def test_router_prompt_covers_persian_sequential_summary_translation() -> None:
    prompt = ROUTER_SYSTEM_PROMPT

    assert "و بعد" in prompt
    assert "سپس" in prompt
    assert "این متن را خلاصه کن و بعد خلاصه را به انگلیسی ترجمه کن" in prompt
    assert '["summarizer", "translator"], sequential' in prompt


def test_router_schema_descriptions_repeat_execution_invariants() -> None:
    schema = RouterDecision.model_json_schema()
    properties = schema["properties"]

    assert "execution_mode must be single" in properties["skills"]["description"]
    assert "Use single only with exactly one skill" in properties["execution_mode"]["description"]
    assert "sequential for dependent operations" in properties["execution_mode"]["description"]
