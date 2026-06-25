"""CRUD para agentes e crews."""
from crewai import Task, Crew, Process
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.builder import build_agent
from app.db.base import SessionLocal
from app.db.models import Agent as AgentModel, Crew as CrewModel
from app.tools import TOOL_REGISTRY


router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str
    tool_names: list[str] = []
    max_iter: int = 4


class CrewCreate(BaseModel):
    name: str
    agent_ids: list[int]
    process_type: str = "sequential"


@router.get("")
def list_agents():
    db = SessionLocal()
    try:
        return [
            {"id": a.id, "name": a.name, "role": a.role, "goal": a.goal,
             "backstory": a.backstory, "tool_names": a.tool_names,
             "max_iter": a.max_iter, "is_system": a.is_system}
            for a in db.query(AgentModel).all()
        ]
    finally:
        db.close()


@router.get("/tools")
def list_tools():
    return list(TOOL_REGISTRY.keys())


@router.post("")
def create_agent(req: AgentCreate):
    db = SessionLocal()
    try:
        if db.query(AgentModel).filter_by(name=req.name).first():
            raise HTTPException(400, f"Agent '{req.name}' already exists")
        for tn in req.tool_names:
            if tn not in TOOL_REGISTRY:
                raise HTTPException(400, f"Unknown tool '{tn}'")
        a = AgentModel(**req.model_dump(), is_system=False)
        db.add(a); db.commit(); db.refresh(a)
        return {"id": a.id, "name": a.name}
    finally:
        db.close()


@router.put("/{agent_id}")
def update_agent(agent_id: int, req: AgentCreate):
    db = SessionLocal()
    try:
        a = db.get(AgentModel, agent_id)
        if not a:
            raise HTTPException(404, "Not found")
        if a.is_system:
            raise HTTPException(403, "System agents are read-only")
        for k, v in req.model_dump().items():
            setattr(a, k, v)
        db.commit()
        return {"id": a.id, "name": a.name}
    finally:
        db.close()


@router.delete("/{agent_id}")
def delete_agent(agent_id: int):
    db = SessionLocal()
    try:
        a = db.get(AgentModel, agent_id)
        if not a:
            raise HTTPException(404, "Not found")
        if a.is_system:
            raise HTTPException(403, "System agents cannot be deleted")
        db.delete(a); db.commit()
        return {"ok": True}
    finally:
        db.close()


class TestRequest(BaseModel):
    ticker: str = "PETR4"


@router.post("/{agent_id}/test")
async def test_agent(agent_id: int, req: TestRequest):
    """Roda o agente isolado contra um ticker. Sanity check pré-deploy."""
    db = SessionLocal()
    try:
        a = db.get(AgentModel, agent_id)
        if not a:
            raise HTTPException(404, "Not found")
        agent = build_agent(a)
        # Build a minimal task that asks the agent to do its job for this ticker
        task = Task(
            description=f"Execute seu papel ({a.role}) para o ticker {req.ticker.upper()}. Retorne um resumo conciso.",
            expected_output="Resumo em 2-3 frases mencionando dados que você coletou.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        try:
            result = await crew.kickoff_async(inputs={"ticker": req.ticker.upper()})
            raw = result.raw if hasattr(result, "raw") else str(result)
            return {"agent": a.name, "ticker": req.ticker.upper(), "output": raw}
        except Exception as e:
            return {"agent": a.name, "ticker": req.ticker.upper(), "error": str(e)}
    finally:
        db.close()


# Crews

crew_router = APIRouter(prefix="/api/crews", tags=["crews"])


@crew_router.get("")
def list_crews():
    db = SessionLocal()
    try:
        return [
            {"id": c.id, "name": c.name, "agent_ids": c.agent_ids,
             "process_type": c.process_type}
            for c in db.query(CrewModel).all()
        ]
    finally:
        db.close()


@crew_router.post("")
def create_crew(req: CrewCreate):
    db = SessionLocal()
    try:
        if db.query(CrewModel).filter_by(name=req.name).first():
            raise HTTPException(400, "Crew already exists")
        c = CrewModel(**req.model_dump())
        db.add(c); db.commit(); db.refresh(c)
        return {"id": c.id, "name": c.name}
    finally:
        db.close()
