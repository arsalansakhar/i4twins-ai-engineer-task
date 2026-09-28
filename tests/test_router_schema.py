"""Unit tests for the structured router contract."""

import pytest
from pydantic import ValidationError

from app.state import RouterDecision


def test_single_skill_decision_is_valid() -> None:
    decision = RouterDecision(skills=["summarizer"], execution_mode="single")
    assert decision.skills == ["summarizer"]


def test_two_skill_sequential_decision_is_valid() -> None:
    decision = RouterDecision(
        skills=["summarizer", "translator"],
        execution_mode="sequential",
    )
    assert len(decision.skills) == 2


def test_more_than_two_skills_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RouterDecision(
            skills=["summarizer", "translator", "calculator"],
            execution_mode="sequential",
        )


def test_single_skill_cannot_claim_parallel_execution() -> None:
    with pytest.raises(ValidationError):
        RouterDecision(skills=["calculator"], execution_mode="parallel")


def test_duplicate_skills_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RouterDecision(
            skills=["translator", "translator"],
            execution_mode="parallel",
        )
