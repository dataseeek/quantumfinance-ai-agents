"""Backtest: agent (MACD-cross heuristic) vs buy-and-hold."""
from fastapi import APIRouter, Query

from app.db.base import SessionLocal
from app.db.models import Ticker
from app.tools.backtest import backtest


router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/{ticker}")
def backtest_one(
    ticker: str,
    period: str = Query("6mo", pattern="^(1mo|3mo|6mo|1y|2y)$"),
    initial_cash: float = Query(10000.0, gt=0),
):
    return backtest(ticker.upper(), period=period, initial_cash=initial_cash)


@router.get("")
def backtest_all(
    period: str = Query("6mo", pattern="^(1mo|3mo|6mo|1y|2y)$"),
    initial_cash: float = Query(10000.0, gt=0),
):
    """Compact summary across all active tickers (no per-day curve)."""
    db = SessionLocal()
    try:
        symbols = [t.symbol for t in db.query(Ticker).filter_by(active=True).all()]
    finally:
        db.close()
    out = []
    for s in symbols:
        r = backtest(s, period=period, initial_cash=initial_cash)
        r.pop("curve", None)
        out.append(r)
    return out
