"""Hit-rate evaluation: compare each Recommendation against the actual price move N trading days later.

Regras (mesmas documentadas em `final_state.html` §5):
- COMPRAR  acerta se o preço subiu  > 0.5% em D+N
- VENDER   acerta se o preço caiu   > 0.5% em D+N
- AGUARDAR acerta se ficou lateral  (|move| < 1.0%) em D+N
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from app.db.base import SessionLocal
from app.db.models import Recommendation
from app.tools.prices import fetch_ohlcv


THRESHOLD_BUY = 0.005    # +0.5%
THRESHOLD_SELL = -0.005  # -0.5%
HOLD_BAND = 0.01         # |move| < 1.0%


def _evaluate(rec: str, move: float) -> str | None:
    rec = (rec or "").upper()
    if rec == "COMPRAR":
        return "hit" if move > THRESHOLD_BUY else "miss"
    if rec == "VENDER":
        return "hit" if move < THRESHOLD_SELL else "miss"
    if rec == "AGUARDAR":
        return "hit" if abs(move) < HOLD_BAND else "miss"
    return None


def _close_series(ticker: str) -> pd.Series | None:
    df = fetch_ohlcv(ticker, "1y")
    if df.empty:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.astype(float)


def compute_hit_rate(horizon_days: int = 3, since_days: int | None = None) -> dict:
    """Score every Recommendation row against the actual D+horizon close.

    Returns aggregate hit-rate + per-ticker + per-recommendation breakdowns
    + the last 100 evaluated rows for the UI.
    """
    db = SessionLocal()
    try:
        q = db.query(Recommendation).order_by(Recommendation.date.asc())
        if since_days:
            cutoff = datetime.utcnow() - timedelta(days=since_days)
            q = q.filter(Recommendation.date >= cutoff)
        recs = q.all()
    finally:
        db.close()

    prices_cache: dict[str, pd.Series | None] = {}

    def get_close(ticker: str) -> pd.Series | None:
        if ticker not in prices_cache:
            prices_cache[ticker] = _close_series(ticker)
        return prices_cache[ticker]

    evaluated: list[dict] = []
    pending = 0
    skipped = 0

    for r in recs:
        close = get_close(r.ticker)
        if close is None or close.empty:
            skipped += 1
            continue

        # Find the trading bar at/after the rec date
        rec_ts = pd.Timestamp(r.date.date())
        idx = close.index
        pos_arr = idx.get_indexer([rec_ts], method="backfill")
        entry_pos = int(pos_arr[0]) if len(pos_arr) and pos_arr[0] >= 0 else -1
        if entry_pos < 0:
            skipped += 1
            continue
        exit_pos = entry_pos + horizon_days
        if exit_pos >= len(close):
            pending += 1
            continue

        entry = float(close.iloc[entry_pos])
        exit_ = float(close.iloc[exit_pos])
        move = (exit_ - entry) / entry if entry else 0.0
        result = _evaluate(r.recommendation, move)
        if result is None:
            skipped += 1
            continue

        evaluated.append({
            "id": r.id,
            "ticker": r.ticker,
            "rec_date": r.date.isoformat(),
            "entry_date": idx[entry_pos].strftime("%Y-%m-%d"),
            "exit_date": idx[exit_pos].strftime("%Y-%m-%d"),
            "recommendation": r.recommendation,
            "entry_price": round(entry, 4),
            "exit_price": round(exit_, 4),
            "move_pct": round(move * 100, 4),
            "result": result,
        })

    total = len(evaluated)
    hits = sum(1 for e in evaluated if e["result"] == "hit")

    # Breakdowns
    by_ticker: dict[str, dict] = {}
    for e in evaluated:
        t = e["ticker"]
        bt = by_ticker.setdefault(t, {"total": 0, "hits": 0})
        bt["total"] += 1
        if e["result"] == "hit":
            bt["hits"] += 1
    for t, bt in by_ticker.items():
        bt["hit_rate_pct"] = round(bt["hits"] / bt["total"] * 100, 2) if bt["total"] else 0.0
        bt["misses"] = bt["total"] - bt["hits"]

    by_rec: dict[str, dict] = {}
    for e in evaluated:
        rec = e["recommendation"]
        br = by_rec.setdefault(rec, {"total": 0, "hits": 0})
        br["total"] += 1
        if e["result"] == "hit":
            br["hits"] += 1
    for rec, br in by_rec.items():
        br["hit_rate_pct"] = round(br["hits"] / br["total"] * 100, 2) if br["total"] else 0.0
        br["misses"] = br["total"] - br["hits"]

    return {
        "horizon_days": horizon_days,
        "since_days": since_days,
        "total_recommendations": len(recs),
        "total_evaluated": total,
        "pending": pending,
        "skipped": skipped,
        "hits": hits,
        "misses": total - hits,
        "hit_rate_pct": round(hits / total * 100, 2) if total else 0.0,
        "by_ticker": by_ticker,
        "by_recommendation": by_rec,
        "details": evaluated[-100:],
    }
