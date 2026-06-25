"""Compute technical indicators (RSI, MACD, SMA, EMA, Bollinger) via ta."""
import pandas as pd
from crewai.tools import tool
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands

from app.tools.prices import fetch_ohlcv


def compute_indicators(close: pd.Series) -> dict:
    """Returns dict with latest values for RSI, MACD, SMA/EMA(20), Bollinger(20,2)."""
    rsi = float(RSIIndicator(close, window=14).rsi().iloc[-1])
    macd_obj = MACD(close)
    macd_line = float(macd_obj.macd().iloc[-1])
    macd_sig = float(macd_obj.macd_signal().iloc[-1])
    macd_hist = float(macd_obj.macd_diff().iloc[-1])
    sma20 = float(SMAIndicator(close, window=20).sma_indicator().iloc[-1])
    ema20 = float(EMAIndicator(close, window=20).ema_indicator().iloc[-1])
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_h = float(bb.bollinger_hband().iloc[-1])
    bb_l = float(bb.bollinger_lband().iloc[-1])
    return {
        "rsi": rsi, "macd": macd_line, "macd_signal": macd_sig, "macd_hist": macd_hist,
        "sma20": sma20, "ema20": ema20, "bb_upper": bb_h, "bb_lower": bb_l,
        "last_close": float(close.iloc[-1]),
    }


@tool("Calculate Technical Indicators")
def calculate_indicators(ticker: str, period: str = "6mo") -> str:
    """Calcula indicadores técnicos clássicos para uma ação da B3.

    Indicadores: RSI(14), MACD(12,26,9), SMA(20), EMA(20), Bandas de Bollinger(20, 2).

    Argumentos:
        ticker: símbolo da ação (VALE3, PETR4, BBAS3, ITUB4).
        period: janela temporal (default '6mo').

    Retorna:
        Texto com valores recentes dos indicadores + interpretação Bullish/Bearish/Neutra.
    """
    df = fetch_ohlcv(ticker, period)
    if df.empty:
        return f"Sem dados para {ticker}."
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    ind = compute_indicators(close)
    rsi_sig = "sobrecomprado (>70)" if ind["rsi"] > 70 else "sobrevendido (<30)" if ind["rsi"] < 30 else "neutro"
    macd_dir = "BULLISH (MACD > sinal)" if ind["macd"] > ind["macd_signal"] else "BEARISH (MACD < sinal)"
    last = ind["last_close"]
    if last > ind["bb_upper"] * 0.98:
        bb_pos = "próximo da banda SUPERIOR"
    elif last < ind["bb_lower"] * 1.02:
        bb_pos = "próximo da banda INFERIOR"
    else:
        bb_pos = "dentro da faixa central"
    trend = "BULLISH" if last > ind["sma20"] else "BEARISH"
    return (
        f"Ticker: {ticker}\n"
        f"RSI(14): {ind['rsi']:.2f} — {rsi_sig}\n"
        f"MACD: {ind['macd']:.4f} | signal: {ind['macd_signal']:.4f} | hist: {ind['macd_hist']:+.4f} — {macd_dir}\n"
        f"SMA(20): {ind['sma20']:.2f} | EMA(20): {ind['ema20']:.2f} | preço: {last:.2f} — tendência {trend}\n"
        f"Bollinger sup: {ind['bb_upper']:.2f} | inf: {ind['bb_lower']:.2f} — preço {bb_pos}"
    )
