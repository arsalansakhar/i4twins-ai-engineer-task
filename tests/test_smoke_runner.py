"""Offline tests for the end-to-end smoke-evaluation harness."""

from app.state import RouterDecision
from evaluation.run_smoke_eval import _check_output, run_smoke_cases


class _GraphStub:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def invoke(self, state: dict[str, str]) -> dict[str, object]:
        assert "user_input" in state
        return self.result


def _case() -> dict[str, object]:
    return {
        "id": "translator",
        "prompt": "Translate hello to Persian.",
        "expected_skills": ["translator"],
        "expected_mode": "single",
        "checks": {"non_empty": True, "contains_persian": True},
    }


def test_output_checks_cover_language_and_required_text() -> None:
    passed, failures = _check_output(
        "[calculator]\n12*9 = 108\nسلام",
        {
            "non_empty": True,
            "contains_persian": True,
            "contains_ascii_letter": True,
            "contains_all": ["[calculator]", "12*9 = 108"],
        },
    )

    assert passed is True
    assert failures == []


def test_smoke_case_passes_only_when_route_and_output_checks_pass() -> None:
    graph = _GraphStub(
        {
            "router_decision": RouterDecision(
                skills=["translator"],
                execution_mode="single",
            ),
            "final_response": "سلام",
        }
    )

    report = run_smoke_cases(
        [_case()],
        graph=graph,
        delay_seconds=0,
        max_retries=0,
    )

    assert report["automated_passes"] == 1
    assert report["all_automated_checks_pass"] is True
    assert report["manual_review_required"] is True


def test_smoke_case_reports_output_failure_without_hiding_route_success() -> None:
    graph = _GraphStub(
        {
            "router_decision": RouterDecision(
                skills=["translator"],
                execution_mode="single",
            ),
            "final_response": "hello",
        }
    )

    report = run_smoke_cases(
        [_case()],
        graph=graph,
        delay_seconds=0,
        max_retries=0,
    )

    row = report["cases"][0]
    assert row["route_match"] is True
    assert row["output_checks_pass"] is False
    assert report["automated_passes"] == 0
