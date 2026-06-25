"""Deterministic backtest: agent (heuristic proxy) vs buy-and-hold.

The agent strategy is the MACD-cross heuristic documented in `final_state.html` §7:
- COMPRAR if MACD > signal AND histogram > 0 AND RSI < 65 (avoid chasing overbought)
- VENDER if MACD < signal AND histogram < 0 AND RSI > 35 (avoid panic at oversold)
- otherwise AGUARDAR (hold current position)

We use a heuristic proxy rather than the live LLM because reprocessing ~120 days
× N tickers with the LLM would cost hundreds of API calls per backtest request.
The heuristic captures the same signal logic the strategist agent relies on.
"""
from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD

from app.tools.prices import fetch_ohlcv


def _to_series(x) -> pd.Series:
    return x.iloc[:, 0] if isinstance(x, pd.DataFrame) else x


def _signal(rsi: float, macd: float, sig: float, hist: float) -> str:
    if macd > sig and hist > 0 and rsi < 65:
        return "COMPRAR"
    if macd < sig and hist < 0 and rsi > 35:
        return "VENDER"
    return "AGUARDAR"


def backtest(ticker: str, period: str = "6mo", initial_cash: float = 10_000.0) -> dict:
    """Run a deterministic agent-vs-B&H backtest over `period` for `ticker`.

    Returns the daily equity curve, daily signals, and summary metrics.
    """
    df = fetch_ohlcv(ticker, period)
    if df.empty:
        return {"ticker": ticker, "error": "no data"}

    close = _to_series(df["Close"]).astype(float)
    if len(close) < 35:
        return {"ticker": ticker, "error": f"insufficient data ({len(close)} rows)"}

    rsi = RSIIndicator(close, 14).rsi()
    macd_obj = MACD(close)
    macd = macd_obj.macd()
    sig = macd_obj.macd_signal()
    hist = macd_obj.macd_diff()

    start_idx = max(rsi.first_valid_index(), macd.first_valid_index(), sig.first_valid_index())
    px = close.loc[start_idx:]
    rsi_a = rsi.loc[start_idx:]
    macd_a = macd.loc[start_idx:]
    sig_a = sig.loc[start_idx:]
    hist_a = hist.loc[start_idx:]

    # Buy-and-hold baseline: invest fully at the first close, hold forever.
    bh_shares = initial_cash / float(px.iloc[0])

    # Agent: starts in cash, follows daily signal.
    cash = initial_cash
    shares = 0.0

    curve: list[dict] = []
    n_buys = 0; n_sells = 0; n_holds = 0
    for ts, p in px.items():
        action = _signal(
            float(rsi_a.loc[ts]),
            float(macd_a.loc[ts]),
            float(sig_a.loc[ts]),
            float(hist_a.loc[ts]),
        )
        if action == "COMPRAR" and cash > 0:
            shares = cash / p
            cash = 0.0
            n_buys += 1
        elif action == "VENDER" and shares > 0:
            cash = shares * p
            shares = 0.0
            n_sells += 1
        else:
            n_holds += 1
        equity_agent = cash + shares * p
        equity_bh = bh_shares * p
        curve.append({
            "date": ts.strftime("%Y-%m-%d"),
            "price": round(float(p), 4),
            "signal": action,
            "agent_equity": round(equity_agent, 2),
            "bh_equity": round(equity_bh, 2),
        })

    first_p = float(px.iloc[0])
    last_p = float(px.iloc[-1])
    agent_final = curve[-1]["agent_equity"]
    bh_final = curve[-1]["bh_equity"]

    def pct(x: float, base: float) -> float:
        return (x / base - 1.0) * 100.0

    return {
        "ticker": ticker.upper().replace(".SA", ""),
        "period": period,
        "initial_cash": initial_cash,
        "start_date": curve[0]["date"],
        "end_date": curve[-1]["date"],
        "days": len(curve),
        "first_price": round(first_p, 4),
        "last_price": round(last_p, 4),
        "agent_return_pct": round(pct(agent_final, initial_cash), 4),
        "bh_return_pct": round(pct(bh_final, initial_cash), 4),
        "delta_pp": round(pct(agent_final, initial_cash) - pct(bh_final, initial_cash), 4),
        "n_buys": n_buys,
        "n_sells": n_sells,
        "n_holds": n_holds,
        "final_position": "shares" if shares > 0 else "cash",
        "curve": curve,
    }
