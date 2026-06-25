"""Get historical OHLCV prices via yfinance, with TTL cache to avoid flicker."""
import time
import threading

import pandas as pd
import yfinance as yf
from crewai.tools import tool


_CACHE_TTL_SEC = 300
_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
_cache_lock = threading.Lock()


def _yf_ticker(t: str) -> str:
    return t if t.endswith(".SA") else f"{t}.SA"


def _is_healthy(df: pd.DataFrame, period: str) -> bool:
    """Reject truncated/incomplete responses from yfinance."""
    if df.empty:
        return False
    expected_min = {"3mo": 40, "6mo": 80, "1y": 180, "2y": 360}.get(period, 20)
    return len(df) >= expected_min


def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Helper compartilhado: retorna DataFrame OHLCV. Cache 5min para estabilidade."""
    key = (ticker.upper(), period)
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL_SEC:
            return hit[1]
    yft = _yf_ticker(ticker.upper())
    df = yf.download(yft, period=period, progress=False, auto_adjust=True)
    if not _is_healthy(df, period):
        with _cache_lock:
            stale = _cache.get(key)
        if stale:
            return stale[1]
        return df
    with _cache_lock:
        _cache[key] = (now, df)
    return df


@tool("Get Stock Price Data")
def get_price_data(ticker: str, period: str = "6mo") -> str:
    """Busca dados históricos de preços OHLCV de uma ação da B3 via yfinance.

    Argumentos:
        ticker: símbolo da ação (VALE3, PETR4, BBAS3, ITUB4).
        period: janela temporal (default '6mo'; aceita '3mo', '6mo', '1y', '2y').

    Retorna:
        Texto com último fechamento, range do período, retorno acumulado
        e os 5 últimos fechamentos diários.
    """
    df = fetch_ohlcv(ticker, period)
    if df.empty:
        return f"Sem dados de preço para {ticker}."
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    last_close = float(close.iloc[-1])
    last_date = df.index[-1].strftime("%Y-%m-%d")
    high = float(close.max()); low = float(close.min()); avg = float(close.mean())
    pct = float((close.iloc[-1] / close.iloc[0] - 1) * 100)
    recent = close.tail(5)
    recent_str = ", ".join(f"{d.strftime('%Y-%m-%d')}=R${float(v):.2f}" for d, v in recent.items())
    return (
        f"Ticker: {ticker} (período={period})\n"
        f"Último fechamento ({last_date}): R$ {last_close:.2f}\n"
        f"Range do período: R$ {low:.2f} — R$ {high:.2f} (média R$ {avg:.2f})\n"
        f"Retorno acumulado: {pct:+.2f}%\n"
        f"Últimos 5 fechamentos: {recent_str}"
    )
