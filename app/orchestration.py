"""Execution strategy for requests routed to exactly two skills."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.state import AgentState, SkillName

SkillNode = Callable[[AgentState], dict[str, str]]


def _run_skill(node: SkillNode, user_input: str) -> str:
    """Execute one skill node and return its text response."""

    result = node({"user_input": user_input})
    response = result.get("final_response")
    if not isinstance(response, str):
        raise TypeError("Skill node did not return a text final_response.")
    return response


def _build_sequential_handoff(
    *,
    original_request: str,
    first_skill: SkillName,
    second_skill: SkillName,
    intermediate_result: str,
) -> str:
    """Build the second skill's input while preserving dependency semantics."""

    if second_skill == "calculator":
        # The calculator uses deterministic token extraction, so feeding only the
        # previous result avoids accidentally combining numbers from instructions.
        return intermediate_result

    return (
        "Original user request:\n"
        f"{original_request}\n\n"
        f"The previous skill ({first_skill}) produced this intermediate result:\n"
        f"{intermediate_result}\n\n"
        f"Perform only the {second_skill} step of the original request. "
        "Use the intermediate result as the content to process, while preserving "
        "relevant target-language, style, or length constraints from the original request."
    )


def _format_parallel_results(results: list[tuple[SkillName, str]]) -> str:
    """Combine independent skill outputs in router-selected order."""

    return "\n\n".join(
        f"[{skill}]\n{response}"
        for skill, response in results
    )


def make_multi_skill_node(skill_nodes: dict[SkillName, SkillNode]):
    """Return an orchestrator for validated two-skill router decisions.

    Sequential mode pipes the first skill's output into the second skill.
    Parallel mode executes both skills concurrently on the original request and
    combines their outputs in the router-selected order.
    """

    def multi_skill_node(state: AgentState) -> dict[str, str]:
        decision = state["router_decision"]
        skills = decision.skills

        if len(skills) != 2:
            raise ValueError("Multi-skill orchestration requires exactly two skills.")

        first_skill, second_skill = skills
        try:
            first_node = skill_nodes[first_skill]
            second_node = skill_nodes[second_skill]
        except KeyError as exc:
            raise ValueError(f"Unsupported routed skill: {exc.args[0]}") from exc

        if decision.execution_mode == "sequential":
            first_response = _run_skill(first_node, state["user_input"])
            handoff_input = _build_sequential_handoff(
                original_request=state["user_input"],
                first_skill=first_skill,
                second_skill=second_skill,
                intermediate_result=first_response,
            )
            second_response = _run_skill(second_node, handoff_input)
            return {"final_response": second_response}

        if decision.execution_mode == "parallel":
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {
                    first_skill: executor.submit(
                        _run_skill, first_node, state["user_input"]
                    ),
                    second_skill: executor.submit(
                        _run_skill, second_node, state["user_input"]
                    ),
                }
                ordered_results = [
                    (skill, futures[skill].result())
                    for skill in skills
                ]
            return {"final_response": _format_parallel_results(ordered_results)}

        raise ValueError(
            "Two-skill orchestration requires execution_mode='sequential' or 'parallel'."
        )

    return multi_skill_node
