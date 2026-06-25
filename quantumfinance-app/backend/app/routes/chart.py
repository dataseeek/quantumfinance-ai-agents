"""Chart: OHLCV + indicators for a single ticker."""
from fastapi import APIRouter, HTTPException
import pandas as pd

from app.tools.prices import fetch_ohlcv
from app.tools.indicators import compute_indicators


router = APIRouter(prefix="/api/chart", tags=["chart"])


@router.get("/{ticker}")
def chart_data(ticker: str, period: str = "6mo"):
    df = fetch_ohlcv(ticker, period)
    if df.empty:
        raise HTTPException(404, f"No data for {ticker}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    high = df["High"]
    if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]
    low = df["Low"]
    if isinstance(low, pd.DataFrame): low = low.iloc[:, 0]
    open_ = df["Open"]
    if isinstance(open_, pd.DataFrame): open_ = open_.iloc[:, 0]
    vol = df["Volume"]
    if isinstance(vol, pd.DataFrame): vol = vol.iloc[:, 0]
    ohlc = [
        {
            "time": d.strftime("%Y-%m-%d"),
            "open": float(open_.loc[d]),
            "high": float(high.loc[d]),
            "low": float(low.loc[d]),
            "close": float(close.loc[d]),
            "volume": float(vol.loc[d]) if not pd.isna(vol.loc[d]) else 0.0,
        }
        for d in df.index
    ]
    ind = compute_indicators(close)
    return {"ticker": ticker.upper(), "period": period, "ohlc": ohlc, "indicators": ind}
