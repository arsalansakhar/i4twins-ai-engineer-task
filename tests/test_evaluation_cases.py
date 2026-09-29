"""Offline checks for the committed routing evaluation dataset."""

import json
from pathlib import Path

from app.state import RouterDecision

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "evaluation_cases.json"
)


def _load_cases() -> list[dict[str, object]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def test_evaluation_set_contains_15_cases() -> None:
    assert len(_load_cases()) == 15


def test_evaluation_set_covers_all_required_skills_and_modes() -> None:
    cases = _load_cases()

    covered_skills = {
        skill
        for case in cases
        for skill in case["expected_skills"]
    }
    covered_modes = {case["expected_mode"] for case in cases}

    assert covered_skills == {
        "summarizer",
        "translator",
        "calculator",
        "general_chat",
    }
    assert covered_modes == {"single", "sequential", "parallel"}


def test_evaluation_set_contains_persian_and_edge_cases() -> None:
    cases = _load_cases()

    assert sum(case["language"] == "fa" for case in cases) >= 4
    ids = {case["id"] for case in cases}
    assert "translator_missing_target" in ids
    assert "fallback_unclear_general" in ids
    assert "translate_question_as_content" in ids


def test_expected_routes_are_valid_router_decisions() -> None:
    for case in _load_cases():
        RouterDecision(
            skills=case["expected_skills"],
            execution_mode=case["expected_mode"],
        )
