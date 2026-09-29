"""Run live routing evaluation against the configured LLM provider."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.llm import get_llm
from app.router import make_router_node
from app.state import RouterDecision

DEFAULT_CASES = Path(__file__).with_name("evaluation_cases.json")
RouterNode = Callable[[dict[str, str]], dict[str, RouterDecision]]


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate routing evaluation cases."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation file must contain a JSON list.")
    return data


def _classify_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "ratelimit" in text or "rate limit" in text or "429" in text:
        return "rate_limit"
    if "validationerror" in text or "json_invalid" in text:
        return "model_output_validation"
    return "provider_or_runtime"


def _invoke_with_retry(
    router: RouterNode,
    prompt: str,
    *,
    max_retries: int,
    retry_backoff_seconds: float,
) -> dict[str, RouterDecision]:
    """Retry only transient rate-limit failures."""

    attempt = 0
    while True:
        try:
            return router({"user_input": prompt})
        except Exception as exc:
            error_kind = _classify_error(exc)
            if error_kind != "rate_limit" or attempt >= max_retries:
                raise
            attempt += 1
            wait_seconds = retry_backoff_seconds * attempt
            print(
                f"  rate limited; retrying in {wait_seconds:.1f}s "
                f"(retry {attempt}/{max_retries})"
            )
            time.sleep(wait_seconds)


def evaluate_cases(
    cases: list[dict[str, Any]],
    *,
    router: RouterNode | None = None,
    delay_seconds: float = 4.0,
    max_retries: int = 1,
    retry_backoff_seconds: float = 15.0,
) -> dict[str, Any]:
    """Run cases and separate routing quality from provider availability.

    Accuracy is calculated only over cases that produced a valid structured
    RouterDecision. Provider/rate-limit/format failures are reported separately
    so an infrastructure outage cannot be misreported as 0% routing accuracy.
    """

    router = router or make_router_node(get_llm())
    rows: list[dict[str, Any]] = []

    ordered_skill_hits = 0
    skill_set_hits = 0
    mode_hits = 0
    full_route_hits = 0
    completed_routes = 0
    rate_limit_errors = 0
    model_output_errors = 0
    other_errors = 0

    for index, case in enumerate(cases):
        expected_skills = list(case["expected_skills"])
        expected_mode = str(case["expected_mode"])

        row: dict[str, Any] = {
            "id": case["id"],
            "language": case.get("language"),
            "prompt": case["prompt"],
            "expected_skills": expected_skills,
            "expected_mode": expected_mode,
        }

        try:
            result = _invoke_with_retry(
                router,
                str(case["prompt"]),
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )
            decision = result["router_decision"]
            if not isinstance(decision, RouterDecision):
                decision = RouterDecision.model_validate(decision)

            actual_skills = list(decision.skills)
            actual_mode = decision.execution_mode

            ordered_skill_match = actual_skills == expected_skills
            skill_set_match = set(actual_skills) == set(expected_skills)
            mode_match = actual_mode == expected_mode
            full_route_match = ordered_skill_match and mode_match

            completed_routes += 1
            ordered_skill_hits += int(ordered_skill_match)
            skill_set_hits += int(skill_set_match)
            mode_hits += int(mode_match)
            full_route_hits += int(full_route_match)

            row.update(
                {
                    "actual_skills": actual_skills,
                    "actual_mode": actual_mode,
                    "ordered_skill_match": ordered_skill_match,
                    "skill_set_match": skill_set_match,
                    "mode_match": mode_match,
                    "full_route_match": full_route_match,
                    "error_kind": None,
                    "error": None,
                }
            )
        except Exception as exc:
            error_kind = _classify_error(exc)
            rate_limit_errors += int(error_kind == "rate_limit")
            model_output_errors += int(error_kind == "model_output_validation")
            other_errors += int(error_kind == "provider_or_runtime")
            row.update(
                {
                    "actual_skills": None,
                    "actual_mode": None,
                    "ordered_skill_match": None,
                    "skill_set_match": None,
                    "mode_match": None,
                    "full_route_match": None,
                    "error_kind": error_kind,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        rows.append(row)

        if delay_seconds > 0 and index < len(cases) - 1:
            time.sleep(delay_seconds)

    def metric(hits: int) -> float | None:
        return hits / completed_routes if completed_routes else None

    total = len(cases)
    return {
        "total_cases": total,
        "completed_routes": completed_routes,
        "evaluation_complete": completed_routes == total,
        "rate_limit_errors": rate_limit_errors,
        "model_output_errors": model_output_errors,
        "other_errors": other_errors,
        "ordered_skill_accuracy": metric(ordered_skill_hits),
        "skill_set_accuracy": metric(skill_set_hits),
        "execution_mode_accuracy": metric(mode_hits),
        "full_route_accuracy": metric(full_route_hits),
        "cases": rows,
    }


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def print_report(report: dict[str, Any]) -> None:
    """Print a concise human-readable report."""

    for row in report["cases"]:
        if row["error"] is not None:
            status = "ERROR"
            actual = f"{row['error_kind']}: {row['error']}"
        else:
            status = "PASS" if row["full_route_match"] else "FAIL"
            actual = f"{row['actual_skills']} / {row['actual_mode']}"

        print(
            f"{status:5} {row['id']}: expected "
            f"{row['expected_skills']} / {row['expected_mode']} -> {actual}"
        )

    print()
    print(
        f"Structured routing decisions: "
        f"{report['completed_routes']}/{report['total_cases']}"
    )
    print(f"Rate-limit errors:          {report['rate_limit_errors']}")
    print(f"Model-output errors:        {report['model_output_errors']}")
    print(f"Other provider/runtime:     {report['other_errors']}")
    print(
        f"Ordered skill accuracy:     "
        f"{_format_metric(report['ordered_skill_accuracy'])}"
    )
    print(
        f"Skill-set accuracy:         "
        f"{_format_metric(report['skill_set_accuracy'])}"
    )
    print(
        f"Execution-mode accuracy:    "
        f"{_format_metric(report['execution_mode_accuracy'])}"
    )
    print(
        f"Full-route accuracy:        "
        f"{_format_metric(report['full_route_accuracy'])}"
    )
    if not report["evaluation_complete"]:
        print(
            "Evaluation incomplete: do not report the accuracy as a final "
            "15-case result until every case returns a structured decision."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="Path to the routing evaluation JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for a JSON result report.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=4.0,
        help="Delay between cases to stay below free-tier RPM limits.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Maximum retries for transient 429/rate-limit failures.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=15.0,
        help="Base backoff for a rate-limit retry.",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    report = evaluate_cases(
        cases,
        delay_seconds=args.delay_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved JSON report to {args.output}")


if __name__ == "__main__":
    main()
