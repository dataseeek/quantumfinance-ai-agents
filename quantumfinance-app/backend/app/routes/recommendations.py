"""Recommendations: latest + history + run on-demand."""
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.crew import run_crew_for_ticker
from app.db.base import SessionLocal
from app.db.models import Recommendation
from app.tools.swing import swing_plan


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RunRequest(BaseModel):
    ticker: str
    crew_id: int | None = None


@router.get("")
def latest_recommendations(limit: int = Query(50, le=500)):
    db = SessionLocal()
    try:
        items = (db.query(Recommendation)
                   .order_by(Recommendation.date.desc()).limit(limit).all())
        return [
            {"id": r.id, "ticker": r.ticker, "date": r.date.isoformat(),
             "recommendation": r.recommendation, "reasoning": r.reasoning}
            for r in items
        ]
    finally:
        db.close()


@router.get("/{ticker}/latest")
def latest_for_ticker(ticker: str):
    db = SessionLocal()
    try:
        r = (db.query(Recommendation).filter_by(ticker=ticker.upper())
               .order_by(Recommendation.date.desc()).first())
        if not r:
            return None
        return {"id": r.id, "ticker": r.ticker, "date": r.date.isoformat(),
                "recommendation": r.recommendation, "reasoning": r.reasoning}
    finally:
        db.close()


@router.post("/run")
async def run_now(req: RunRequest):
    result = await run_crew_for_ticker(req.ticker.upper(), crew_id=req.crew_id)
    return result


@router.get("/{ticker}/swing-plan")
def swing_for_ticker(ticker: str):
    # Use most recent recommendation as the basis
    db = SessionLocal()
    try:
        r = (db.query(Recommendation).filter_by(ticker=ticker.upper())
               .order_by(Recommendation.date.desc()).first())
        rec = r.recommendation if r else "AGUARDAR"
    finally:
        db.close()
    return swing_plan(ticker.upper(), rec)
