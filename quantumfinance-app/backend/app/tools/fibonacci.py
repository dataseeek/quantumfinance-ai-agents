"""Fibonacci retracement levels (helper, not a CrewAI tool)."""
import pandas as pd


def fib_levels(close: pd.Series, lookback: int = 60) -> dict[str, float]:
    """Níveis de retração de Fibonacci entre swing high e swing low dos últimos `lookback` pregões."""
    recent = close.tail(lookback)
    hi, lo = float(recent.max()), float(recent.min())
    d = hi - lo
    return {
        "0%": lo,
        "23.6%": lo + 0.236 * d,
        "38.2%": lo + 0.382 * d,
        "50%": lo + 0.5 * d,
        "61.8%": lo + 0.618 * d,
        "78.6%": lo + 0.786 * d,
        "100%": hi,
    }


def nearest_fib(price: float, levels: dict[str, float]) -> tuple[str, float, float]:
    """Returns (label, level_value, pct_off_price) for the nearest level."""
    lbl, dist = min(((l, abs(price - v)) for l, v in levels.items()), key=lambda x: x[1])
    return lbl, levels[lbl], dist / price * 100
