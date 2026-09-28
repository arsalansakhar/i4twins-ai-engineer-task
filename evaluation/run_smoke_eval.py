"""Run end-to-end smoke cases through the compiled LangGraph."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Protocol

from app.graph import build_graph
from app.state import RouterDecision

DEFAULT_CASES = Path(__file__).with_name("smoke_cases.json")
_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")


class InvokableGraph(Protocol):
    def invoke(self, state: dict[str, str]) -> dict[str, Any]: ...


def load_cases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Smoke-case file must contain a JSON list.")
    return data


def select_cases(
    cases: list[dict[str, Any]],
    case_ids: list[str] | None,
) -> list[dict[str, Any]]:
    """Select named cases so a rate-limited live run can resume cheaply."""

    if not case_ids:
        return cases

    requested = set(case_ids)
    selected = [case for case in cases if str(case["id"]) in requested]
    found = {str(case["id"]) for case in selected}
    missing = requested - found
    if missing:
        raise ValueError(
            "Unknown smoke case id(s): " + ", ".join(sorted(missing))
        )
    return selected


def _classify_error(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "ratelimit" in text or "rate limit" in text or "429" in text:
        return "rate_limit"
    if "validationerror" in text or "json_invalid" in text:
        return "model_output_validation"
    return "provider_or_runtime"


def _invoke_with_retry(
    graph: InvokableGraph,
    prompt: str,
    *,
    max_retries: int,
    retry_backoff_seconds: float,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return graph.invoke({"user_input": prompt})
        except Exception as exc:
            if _classify_error(exc) != "rate_limit" or attempt >= max_retries:
                raise
            attempt += 1
            wait_seconds = retry_backoff_seconds * attempt
            print(
                f"  rate limited; retrying full case in {wait_seconds:.1f}s "
                f"(retry {attempt}/{max_retries})"
            )
            time.sleep(wait_seconds)


def _check_output(response: str, checks: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []

    if checks.get("non_empty") and not response.strip():
        failures.append("response is empty")

    if checks.get("contains_persian") and not _PERSIAN_RE.search(response):
        failures.append("response does not contain Persian text")

    if checks.get("contains_ascii_letter") and not _ASCII_LETTER_RE.search(response):
        failures.append("response does not contain an ASCII letter")

    for expected in checks.get("contains_all", []):
        if str(expected) not in response:
            failures.append(f"missing required text: {expected!r}")

    max_chars = checks.get("max_chars")
    if max_chars is not None and len(response) > int(max_chars):
        failures.append(
            f"response length {len(response)} exceeds max_chars={int(max_chars)}"
        )

    return not failures, failures


def run_smoke_cases(
    cases: list[dict[str, Any]],
    *,
    graph: InvokableGraph | None = None,
    delay_seconds: float = 6.0,
    max_retries: int = 1,
    retry_backoff_seconds: float = 15.0,
) -> dict[str, Any]:
    """Run full graph cases and apply transparent, deliberately basic checks.

    The checks verify graph wiring, route preservation, deterministic calculator
    behavior, output language cues, and response shape. They are not a substitute
    for human review of summarization or translation quality.
    """

    graph = graph or build_graph()
    rows: list[dict[str, Any]] = []
    automated_passes = 0
    errors = 0

    for index, case in enumerate(cases):
        row: dict[str, Any] = {
            "id": case["id"],
            "prompt": case["prompt"],
            "expected_skills": list(case["expected_skills"]),
            "expected_mode": str(case["expected_mode"]),
        }

        try:
            result = _invoke_with_retry(
                graph,
                str(case["prompt"]),
                max_retries=max_retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )
            decision = result["router_decision"]
            if not isinstance(decision, RouterDecision):
                decision = RouterDecision.model_validate(decision)

            response = result.get("final_response")
            if not isinstance(response, str):
                raise TypeError("Graph did not return a text final_response.")

            route_match = (
                list(decision.skills) == row["expected_skills"]
                and decision.execution_mode == row["expected_mode"]
            )
            output_match, output_failures = _check_output(
                response,
                dict(case.get("checks", {})),
            )
            automated_pass = route_match and output_match
            automated_passes += int(automated_pass)

            row.update(
                {
                    "actual_skills": list(decision.skills),
                    "actual_mode": decision.execution_mode,
                    "route_match": route_match,
                    "output_checks_pass": output_match,
                    "output_check_failures": output_failures,
                    "automated_pass": automated_pass,
                    "final_response": response,
                    "error_kind": None,
                    "error": None,
                }
            )
        except Exception as exc:
            errors += 1
            row.update(
                {
                    "actual_skills": None,
                    "actual_mode": None,
                    "route_match": None,
                    "output_checks_pass": None,
                    "output_check_failures": [],
                    "automated_pass": False,
                    "final_response": None,
                    "error_kind": _classify_error(exc),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        rows.append(row)
        if delay_seconds > 0 and index < len(cases) - 1:
            time.sleep(delay_seconds)

    return {
        "total_cases": len(cases),
        "automated_passes": automated_passes,
        "errors": errors,
        "all_automated_checks_pass": automated_passes == len(cases),
        "manual_review_required": True,
        "cases": rows,
    }


def print_report(report: dict[str, Any]) -> None:
    for row in report["cases"]:
        if row["error"] is not None:
            print(f"ERROR {row['id']}: {row['error_kind']}: {row['error']}")
            continue

        status = "PASS" if row["automated_pass"] else "FAIL"
        print(
            f"{status:5} {row['id']}: "
            f"{row['actual_skills']} / {row['actual_mode']}"
        )
        if row["output_check_failures"]:
            for failure in row["output_check_failures"]:
                print(f"      check: {failure}")
        print("      response:")
        for line in row["final_response"].splitlines() or [""]:
            print(f"        {line}")

    print()
    print(
        f"Automated smoke checks: {report['automated_passes']}/"
        f"{report['total_cases']}"
    )
    print(f"Runtime/provider errors: {report['errors']}")
    print(
        "Manual review required: inspect the printed generative responses for "
        "semantic quality and faithfulness."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Run only this smoke case ID; repeat the option to select multiple cases.",
    )
    parser.add_argument("--delay-seconds", type=float, default=6.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--retry-backoff-seconds", type=float, default=15.0)
    args = parser.parse_args()

    cases = select_cases(load_cases(args.cases), args.case_ids)
    report = run_smoke_cases(
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
