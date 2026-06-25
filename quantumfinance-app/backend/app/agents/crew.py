"""Crew assembly + kickoff for a given ticker."""
import json
from datetime import date, datetime

from crewai import Crew, Process, Task

from app.agents.builder import build_agents_by_ids
from app.db.base import SessionLocal
from app.db.models import Crew as CrewModel, AgentRun, Recommendation


def _make_tasks_for(agents) -> list[Task]:
    """Standard 3-task pipeline for an Investment Crew (or 4-task with CVM RI Analyst)."""
    role_to_agent = {a.role: a for a in agents}
    tasks: list[Task] = []

    # Find each agent by role keyword
    news = next((a for a in agents if "Notícias" in a.role), None)
    tech = next((a for a in agents if "Técnico" in a.role), None)
    cvm = next((a for a in agents if "CVM" in a.role or "Relações" in a.role), None)
    strat = next((a for a in agents if "Estrategista" in a.role), None)

    if news:
        tasks.append(Task(
            description="Use Search Financial News para {ticker}. Classifique sentimento Positivo/Negativo/Neutro.",
            expected_output="Sentimento + bullets dos eventos-chave.",
            agent=news,
        ))
    if tech:
        tasks.append(Task(
            description="Use Get Stock Price Data e Calculate Technical Indicators para {ticker}. Postura Bullish/Bearish/Neutra.",
            expected_output="Tabela + postura técnica.",
            agent=tech,
        ))
    if cvm:
        tasks.append(Task(
            description="Use Get CVM Filings e Get Quarterly Summary para {ticker}. Resuma contexto regulatório e fundamentalista.",
            expected_output="Lista de fatos relevantes + resumo trimestral.",
            agent=cvm,
        ))
    if strat:
        context = [t for t in tasks if t.agent != strat]
        tasks.append(Task(
            description=(
                "Considerando análises anteriores de {ticker}, decida COMPRAR/VENDER/AGUARDAR. "
                "CoT em 4 passos: (1) notícias, (2) técnico, (3) CVM/fundamentos se disponíveis, (4) decisão. "
                "Depois chame Generate Final Recommendation com a recomendação e reasoning completo."
            ),
            expected_output="JSON da tool Generate Final Recommendation.",
            agent=strat,
            context=context,
        ))
    return tasks


def get_default_crew_id() -> int | None:
    db = SessionLocal()
    try:
        c = db.query(CrewModel).filter_by(name="Investment Crew").first()
        return c.id if c else None
    finally:
        db.close()


async def run_crew_for_ticker(ticker: str, crew_id: int | None = None) -> dict:
    """Runs the configured crew for a given ticker and returns the parsed final JSON.

    Transactions are kept short: the long LLM call happens outside any DB session,
    so concurrent requests do not contend on SQLite's single-writer lock.
    """
    if crew_id is None:
        crew_id = get_default_crew_id()
    if crew_id is None:
        return {"error": "no crew configured"}

    # Tx 1: read crew config, create the AgentRun row, commit, release the lock.
    db = SessionLocal()
    try:
        crew_row = db.get(CrewModel, crew_id)
        if not crew_row:
            return {"error": "crew not found"}
        run = AgentRun(ticker=ticker, crew_name=crew_row.name)
        db.add(run); db.commit(); db.refresh(run)
        run_id = run.id
        agent_ids = list(crew_row.agent_ids)
    finally:
        db.close()

    # Build crew + run the LLM call OUTSIDE any DB session.
    agents = build_agents_by_ids(agent_ids)
    tasks = _make_tasks_for(agents)
    crew = Crew(agents=agents, tasks=tasks, process=Process.sequential, verbose=False)

    try:
        result = await crew.kickoff_async(inputs={"ticker": ticker.upper()})
        raw = result.raw if hasattr(result, "raw") else str(result)
    except Exception as e:
        # Tx 2a: record error and bail.
        db = SessionLocal()
        try:
            r = db.get(AgentRun, run_id)
            if r:
                r.status = "error"; r.raw_output = str(e); db.commit()
        finally:
            db.close()
        return {"error": str(e)}

    # Parse JSON
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```")[1]
        if s.startswith("json"):
            s = s[4:]
    try:
        parsed = json.loads(s)
    except Exception:
        parsed = {"ticker": ticker.upper(), "date": date.today().isoformat(),
                  "recommendation": "AGUARDAR", "reasoning": raw}

    rec_value = (parsed.get("recommendation") or "AGUARDAR").upper().strip()
    if rec_value not in ("COMPRAR", "VENDER", "AGUARDAR"):
        rec_value = "AGUARDAR"
    ticker_u = (parsed.get("ticker") or ticker).upper().replace(".SA", "")

    # Tx 2b: persist result.
    db = SessionLocal()
    try:
        r = db.get(AgentRun, run_id)
        if r:
            r.status = "ok"; r.raw_output = raw
        rec_row = Recommendation(
            ticker=ticker_u,
            date=datetime.utcnow(),
            recommendation=rec_value,
            reasoning=parsed.get("reasoning") or "",
            run_id=run_id,
        )
        db.add(rec_row); db.commit(); db.refresh(rec_row)
        parsed["run_id"] = run_id
        parsed["id"] = rec_row.id
    finally:
        db.close()
    return parsed
