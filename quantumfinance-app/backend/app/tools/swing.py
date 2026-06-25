"""Swing trade plan: stop, target, R/R, holding, confluence (deterministic, no LLM)."""
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

from app.tools.prices import fetch_ohlcv
from app.tools.fibonacci import fib_levels


def swing_plan(ticker: str, rec: str) -> dict:
    """For the given ticker and current recommendation, returns a swing trade plan."""
    df = fetch_ohlcv(ticker, "6mo")
    if df.empty:
        return {"ticker": ticker, "error": "no data"}
    close = df["Close"]
    high = df["High"]; low = df["Low"]
    if isinstance(close, pd.DataFrame): close = close.iloc[:, 0]
    if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]
    if isinstance(low, pd.DataFrame): low = low.iloc[:, 0]

    price = float(close.iloc[-1])
    fib = fib_levels(close)
    below = [(l, v) for l, v in fib.items() if v < price]
    above = [(l, v) for l, v in fib.items() if v > price]
    sup_lbl, sup_v = (max(below, key=lambda x: x[1]) if below else (None, None))
    res_lbl, res_v = (min(above, key=lambda x: x[1]) if above else (None, None))

    if len(close) < 30:
        return {"ticker": ticker, "error": f"insufficient data ({len(close)} rows)"}
    atr = float(AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1])
    atr_pct = atr / price * 100

    rsi = float(RSIIndicator(close, 14).rsi().iloc[-1])
    macd_obj = MACD(close)
    macd_bull = float(macd_obj.macd().iloc[-1]) > float(macd_obj.macd_signal().iloc[-1])
    sma20 = float(SMAIndicator(close, 20).sma_indicator().iloc[-1])
    bb = BollingerBands(close, 20, 2)
    bb_l = float(bb.bollinger_lband().iloc[-1])
    bb_h = float(bb.bollinger_hband().iloc[-1])

    if rec == "COMPRAR":
        stop, target = sup_v, res_v
        risk = price - stop if stop else None
        reward = target - price if target else None
    elif rec == "VENDER":
        stop, target = res_v, sup_v
        risk = stop - price if stop else None
        reward = price - target if target else None
    else:
        stop = target = risk = reward = None

    rr = reward / risk if risk and reward and risk > 0 else None
    if atr_pct < 1.5:
        hold = "10-15 dias"
    elif atr_pct < 2.5:
        hold = "7-10 dias"
    else:
        hold = "3-7 dias"

    sigs_buy = sum([
        rsi < 35, macd_bull, price > sma20,
        abs(price - sup_v) / price < 0.02 if sup_v else False,
        price < bb_l * 1.02,
    ])
    sigs_sell = sum([
        rsi > 65, not macd_bull, price < sma20,
        abs(price - res_v) / price < 0.02 if res_v else False,
        price > bb_h * 0.98,
    ])

    approved = (
        (rec == "COMPRAR" and sigs_buy >= 3)
        or (rec == "VENDER" and sigs_sell >= 3)
        or rec == "AGUARDAR"
    )

    return {
        "ticker": ticker, "rec": rec, "price": price,
        "support": {"label": sup_lbl, "value": sup_v},
        "resistance": {"label": res_lbl, "value": res_v},
        "stop": stop, "target": target,
        "risk_reward": rr, "atr_pct": atr_pct,
        "holding": hold,
        "signals": {"buy": sigs_buy, "sell": sigs_sell},
        "approved": approved,
    }
