"""Calculator node placeholder for Milestone 1.

The real implementation will use a safe computational tool and will not rely
on the LLM to guess arithmetic results.
"""

from app.state import AgentState


def calculator_node(state: AgentState) -> dict[str, str]:
    return {"final_response": "[Milestone 1] Calculator implementation pending."}
