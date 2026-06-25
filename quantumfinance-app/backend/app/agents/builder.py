"""Instancia agentes CrewAI a partir das definições do DB."""
from crewai import Agent

from app.agents.llm import make_llm
from app.db.base import SessionLocal
from app.db.models import Agent as AgentModel
from app.tools import TOOL_REGISTRY


def build_agent(agent_row: AgentModel, llm=None) -> Agent:
    tools = [TOOL_REGISTRY[name] for name in (agent_row.tool_names or []) if name in TOOL_REGISTRY]
    return Agent(
        role=agent_row.role,
        goal=agent_row.goal,
        backstory=agent_row.backstory,
        tools=tools,
        llm=llm or make_llm(),
        verbose=False,
        allow_delegation=False,
        max_iter=agent_row.max_iter,
    )


def build_agents_by_ids(agent_ids: list[int]) -> list[Agent]:
    db = SessionLocal()
    try:
        rows = db.query(AgentModel).filter(AgentModel.id.in_(agent_ids)).all()
        # Preserve order
        rows_by_id = {r.id: r for r in rows}
        ordered = [rows_by_id[i] for i in agent_ids if i in rows_by_id]
        llm = make_llm()
        return [build_agent(r, llm) for r in ordered]
    finally:
        db.close()


def build_agent_by_name(name: str) -> Agent | None:
    db = SessionLocal()
    try:
        row = db.query(AgentModel).filter_by(name=name).first()
        return build_agent(row) if row else None
    finally:
        db.close()
