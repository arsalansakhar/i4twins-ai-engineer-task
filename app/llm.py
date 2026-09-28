"""LLM configuration for an OpenAI-compatible free-tier provider."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    """Create the routing/skill model from environment configuration.

    The final submission must use a free-tier model with no more than 35B
    parameters. The concrete model is intentionally configured through the
    environment so it can be changed without touching application code.
    """

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")
    if not model:
        raise RuntimeError("LLM_MODEL is not set.")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    )
