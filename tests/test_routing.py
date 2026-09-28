"""Focused unit tests for the routing layer."""

from collections.abc import Callable

import pytest

import app.graph as graph_module
from app.router import make_router_node
from app.state import RouterDecision


class _StructuredModelStub:
    def __init__(self, decision: RouterDecision) -> None:
        self.decision = decision

    def invoke(self, messages: list[object]) -> RouterDecision:
        assert len(messages) == 2
        return self.decision


class _ChatModelStub:
    def __init__(self, decision: RouterDecision) -> None:
        self.decision = decision
        self.schema: type[RouterDecision] | None = None

    def with_structured_output(
        self, schema: type[RouterDecision]
    ) -> _StructuredModelStub:
        self.schema = schema
        return _StructuredModelStub(self.decision)


def test_router_node_produces_valid_router_decision() -> None:
    expected = RouterDecision(skills=["summarizer"], execution_mode="single")
    model = _ChatModelStub(expected)

    result = make_router_node(model)({"user_input": "Summarize this text."})

    assert model.schema is RouterDecision
    assert result == {"router_decision": expected}
    assert isinstance(result["router_decision"], RouterDecision)


def _marker_node(name: str) -> Callable[[dict[str, object]], dict[str, str]]:
    def node(state: dict[str, object]) -> dict[str, str]:
        return {"final_response": name}

    return node


@pytest.mark.parametrize(
    ("skill", "expected_node"),
    [
        ("summarizer", "summarizer"),
        ("translator", "translator"),
        ("calculator", "calculator"),
        ("general_chat", "general_chat"),
    ],
)
def test_single_skill_decision_routes_to_selected_node(
    monkeypatch: pytest.MonkeyPatch,
    skill: str,
    expected_node: str,
) -> None:
    monkeypatch.setattr(
        graph_module,
        "make_summarizer_node",
        lambda llm: _marker_node("summarizer"),
    )
    monkeypatch.setattr(
        graph_module,
        "make_translator_node",
        lambda llm: _marker_node("translator"),
    )
    for node_name in ("calculator", "general_chat"):
        monkeypatch.setattr(
            graph_module,
            f"{node_name}_node",
            _marker_node(node_name),
        )

    decision = RouterDecision(skills=[skill], execution_mode="single")
    graph = graph_module.build_graph(_ChatModelStub(decision))

    result = graph.invoke({"user_input": "route this request"})

    assert result["final_response"] == expected_node


def test_two_skill_decision_routes_to_multi_skill_control_path() -> None:
    decision = RouterDecision(
        skills=["summarizer", "translator"],
        execution_mode="sequential",
    )
    graph = graph_module.build_graph(_ChatModelStub(decision))

    result = graph.invoke({"user_input": "summarize, then translate"})

    assert result["final_response"] == (
        "[Milestone 1] Multi-skill execution pending: "
        "sequential: summarizer -> translator"
    )
