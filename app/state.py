"""Shared LangGraph state and structured routing models."""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field, model_validator

SkillName = Literal["summarizer", "translator", "calculator", "general_chat"]
ExecutionMode = Literal["single", "sequential", "parallel"]


class RouterDecision(BaseModel):
    """Validated output produced by the routing LLM."""

    skills: list[SkillName] = Field(
        min_length=1,
        max_length=2,
        description=(
            "One or two relevant skills. If there is one skill, execution_mode must "
            "be single. If there are two skills, keep dependency order when sequential."
        ),
    )
    execution_mode: ExecutionMode = Field(
        description=(
            "Use single only with exactly one skill. Use sequential or parallel only "
            "with exactly two skills; sequential for dependent operations and parallel "
            "for independent operations."
        )
    )

    @model_validator(mode="after")
    def validate_mode_matches_skill_count(self) -> "RouterDecision":
        if len(self.skills) == 1 and self.execution_mode != "single":
            raise ValueError("A one-skill decision must use execution_mode='single'.")
        if len(self.skills) == 2 and self.execution_mode == "single":
            raise ValueError("A two-skill decision must be sequential or parallel.")
        if len(set(self.skills)) != len(self.skills):
            raise ValueError("The same skill cannot be selected twice.")
        return self


class AgentState(TypedDict, total=False):
    """Minimal state shared by graph nodes."""

    user_input: str
    router_decision: RouterDecision
    final_response: str
