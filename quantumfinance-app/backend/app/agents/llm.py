"""LLM factory: returns a CrewAI LLM instance routed via OpenRouter."""
from crewai import LLM

from app.config import settings


def make_llm(model: str | None = None, temperature: float = 0.3) -> LLM:
    return LLM(
        model=model or settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )
