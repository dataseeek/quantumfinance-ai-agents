"""Tickers: watchlist with live quote + change %."""
from fastapi import APIRouter
import yfinance as yf
import pandas as pd

from app.db.base import SessionLocal
from app.db.models import Ticker


router = APIRouter(prefix="/api/tickers", tags=["tickers"])


@router.get("")
def list_tickers():
    db = SessionLocal()
    try:
        tickers = db.query(Ticker).filter_by(active=True).all()
        result = []
        for t in tickers:
            try:
                df = yf.download(f"{t.symbol}.SA", period="5d", progress=False, auto_adjust=True)
                close = df["Close"]
                if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
                last = float(close.iloc[-1]) if len(close) else None
                prev = float(close.iloc[-2]) if len(close) > 1 else last
                change_pct = ((last / prev) - 1) * 100 if last and prev else None
                vol = float(df["Volume"].iloc[-1]) if "Volume" in df and len(df) else None
                if isinstance(vol, pd.Series): vol = float(vol.iloc[-1])
            except Exception:
                last = prev = change_pct = vol = None
            result.append({
                "symbol": t.symbol, "name": t.name, "sector": t.sector,
                "last": last, "prev_close": prev, "change_pct": change_pct, "volume": vol,
            })
        return result
    finally:
        db.close()
