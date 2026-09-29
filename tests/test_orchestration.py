"""Tests for two-skill sequential and parallel orchestration."""

from threading import Barrier

from app.orchestration import make_multi_skill_node
from app.state import RouterDecision


def test_sequential_execution_pipes_first_output_into_second_skill() -> None:
    seen: dict[str, str] = {}

    def summarizer(state: dict[str, object]) -> dict[str, str]:
        seen["first_input"] = str(state["user_input"])
        return {"final_response": "condensed source"}

    def translator(state: dict[str, object]) -> dict[str, str]:
        seen["second_input"] = str(state["user_input"])
        return {"final_response": "ترجمهٔ خلاصه"}

    node = make_multi_skill_node(
        {
            "summarizer": summarizer,
            "translator": translator,
        }
    )
    original = "Summarize this report and translate the summary to Persian."
    decision = RouterDecision(
        skills=["summarizer", "translator"],
        execution_mode="sequential",
    )

    result = node({"user_input": original, "router_decision": decision})

    assert result == {"final_response": "ترجمهٔ خلاصه"}
    assert seen["first_input"] == original
    assert "condensed source" in seen["second_input"]
    assert original in seen["second_input"]
    assert "translator" in seen["second_input"]


def test_sequential_calculator_handoff_uses_only_intermediate_result() -> None:
    seen: dict[str, str] = {}

    def translator(state: dict[str, object]) -> dict[str, str]:
        return {"final_response": "12 * 9"}

    def calculator(state: dict[str, object]) -> dict[str, str]:
        seen["calculator_input"] = str(state["user_input"])
        return {"final_response": "12*9 = 108"}

    node = make_multi_skill_node(
        {
            "translator": translator,
            "calculator": calculator,
        }
    )
    decision = RouterDecision(
        skills=["translator", "calculator"],
        execution_mode="sequential",
    )

    result = node(
        {
            "user_input": "Translate the mathematical expression, then calculate it.",
            "router_decision": decision,
        }
    )

    assert result == {"final_response": "12*9 = 108"}
    assert seen["calculator_input"] == "12 * 9"


def test_parallel_execution_scopes_llm_skill_and_preserves_calculator_input() -> None:
    barrier = Barrier(2, timeout=2)
    seen: dict[str, str] = {}

    def translator(state: dict[str, object]) -> dict[str, str]:
        seen["translator"] = str(state["user_input"])
        barrier.wait()
        return {"final_response": "سلام"}

    def calculator(state: dict[str, object]) -> dict[str, str]:
        seen["calculator"] = str(state["user_input"])
        barrier.wait()
        return {"final_response": "12*9 = 108"}

    node = make_multi_skill_node(
        {
            "translator": translator,
            "calculator": calculator,
        }
    )
    original = "Translate hello to Persian and calculate 12 * 9."
    decision = RouterDecision(
        skills=["translator", "calculator"],
        execution_mode="parallel",
    )

    result = node({"user_input": original, "router_decision": decision})

    assert seen["calculator"] == original
    assert "perform ONLY the translator portion" in seen["translator"]
    assert original in seen["translator"]
    assert result == {
        "final_response": "[translator]\nسلام\n\n[calculator]\n12*9 = 108"
    }


def test_multi_skill_node_rejects_non_two_skill_decision() -> None:
    node = make_multi_skill_node({"summarizer": lambda state: {"final_response": "x"}})
    decision = RouterDecision(skills=["summarizer"], execution_mode="single")

    try:
        node({"user_input": "Summarize this.", "router_decision": decision})
    except ValueError as exc:
        assert "exactly two skills" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-two-skill decision")
