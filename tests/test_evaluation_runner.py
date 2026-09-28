"""Unit tests for the live evaluation harness without API calls."""

from app.state import RouterDecision
from evaluation.run_routing_eval import evaluate_cases


def _case() -> dict[str, object]:
    return {
        "id": "case",
        "language": "en",
        "prompt": "Summarize this.",
        "expected_skills": ["summarizer"],
        "expected_mode": "single",
    }


def test_successful_route_counts_toward_accuracy() -> None:
    def router(state: dict[str, str]) -> dict[str, RouterDecision]:
        return {
            "router_decision": RouterDecision(
                skills=["summarizer"],
                execution_mode="single",
            )
        }

    report = evaluate_cases(
        [_case()],
        router=router,
        delay_seconds=0,
        max_retries=0,
    )

    assert report["completed_routes"] == 1
    assert report["evaluation_complete"] is True
    assert report["full_route_accuracy"] == 1.0
    assert report["rate_limit_errors"] == 0


def test_rate_limit_is_reported_separately_from_routing_accuracy() -> None:
    class FakeRateLimitError(RuntimeError):
        pass

    def router(state: dict[str, str]) -> dict[str, RouterDecision]:
        raise FakeRateLimitError("429 rate limit exceeded")

    report = evaluate_cases(
        [_case()],
        router=router,
        delay_seconds=0,
        max_retries=0,
    )

    assert report["completed_routes"] == 0
    assert report["evaluation_complete"] is False
    assert report["rate_limit_errors"] == 1
    assert report["full_route_accuracy"] is None
    assert report["cases"][0]["error_kind"] == "rate_limit"


def test_wrong_route_is_a_real_accuracy_failure() -> None:
    def router(state: dict[str, str]) -> dict[str, RouterDecision]:
        return {
            "router_decision": RouterDecision(
                skills=["general_chat"],
                execution_mode="single",
            )
        }

    report = evaluate_cases(
        [_case()],
        router=router,
        delay_seconds=0,
        max_retries=0,
    )

    assert report["completed_routes"] == 1
    assert report["evaluation_complete"] is True
    assert report["full_route_accuracy"] == 0.0
    assert report["cases"][0]["full_route_match"] is False
