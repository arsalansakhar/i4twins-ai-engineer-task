"""Run live routing evaluation against the configured LLM provider."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.llm import get_llm
from app.router import make_router_node
from app.state import RouterDecision

DEFAULT_CASES = Path(__file__).with_name("evaluation_cases.json")


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate routing evaluation cases."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation file must contain a JSON list.")
    return data


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the router on every case and compute strict routing metrics."""

    router = make_router_node(get_llm())
    rows: list[dict[str, Any]] = []

    ordered_skill_hits = 0
    skill_set_hits = 0
    mode_hits = 0
    full_route_hits = 0

    for case in cases:
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
            result = router({"user_input": case["prompt"]})
            decision = result["router_decision"]
            if not isinstance(decision, RouterDecision):
                decision = RouterDecision.model_validate(decision)

            actual_skills = list(decision.skills)
            actual_mode = decision.execution_mode

            ordered_skill_match = actual_skills == expected_skills
            skill_set_match = set(actual_skills) == set(expected_skills)
            mode_match = actual_mode == expected_mode
            full_route_match = ordered_skill_match and mode_match

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
                    "error": None,
                }
            )
        except Exception as exc:  # evaluation should record provider failures
            row.update(
                {
                    "actual_skills": None,
                    "actual_mode": None,
                    "ordered_skill_match": False,
                    "skill_set_match": False,
                    "mode_match": False,
                    "full_route_match": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        rows.append(row)

    total = len(cases)
    divisor = total or 1
    return {
        "total_cases": total,
        "ordered_skill_accuracy": ordered_skill_hits / divisor,
        "skill_set_accuracy": skill_set_hits / divisor,
        "execution_mode_accuracy": mode_hits / divisor,
        "full_route_accuracy": full_route_hits / divisor,
        "cases": rows,
    }


def print_report(report: dict[str, Any]) -> None:
    """Print a concise human-readable report."""

    for row in report["cases"]:
        status = "PASS" if row["full_route_match"] else "FAIL"
        actual = (
            f"{row['actual_skills']} / {row['actual_mode']}"
            if row["actual_skills"] is not None
            else row["error"]
        )
        print(
            f"{status:4} {row['id']}: expected "
            f"{row['expected_skills']} / {row['expected_mode']} -> {actual}"
        )

    print()
    print(f"Cases: {report['total_cases']}")
    print(f"Ordered skill accuracy: {report['ordered_skill_accuracy']:.1%}")
    print(f"Skill-set accuracy:      {report['skill_set_accuracy']:.1%}")
    print(f"Execution-mode accuracy: {report['execution_mode_accuracy']:.1%}")
    print(f"Full-route accuracy:     {report['full_route_accuracy']:.1%}")


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
    args = parser.parse_args()

    cases = load_cases(args.cases)
    report = evaluate_cases(cases)
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
