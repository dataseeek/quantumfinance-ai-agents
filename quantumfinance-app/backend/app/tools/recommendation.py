"""Generate the final BUY/SELL/HOLD recommendation in structured JSON."""
import json
from datetime import date

from crewai.tools import tool

from app.db.base import SessionLocal
from app.db.models import Recommendation


@tool("Generate Final Recommendation")
def generate_recommendation(ticker: str, recommendation: str, reasoning: str) -> str:
    """Formata a recomendação final de investimento como JSON estruturado e persiste no DB.

    Argumentos:
        ticker: símbolo da ação (VALE3, PETR4, BBAS3, ITUB4).
        recommendation: deve ser exatamente uma destas opções: COMPRAR, VENDER, AGUARDAR.
        reasoning: justificativa Chain-of-Thought completa citando análise de notícias E indicadores técnicos.

    Retorna:
        String JSON com a recomendação no schema {ticker, date, recommendation, reasoning}.
    """
    rec = recommendation.upper().strip()
    if rec not in ("COMPRAR", "VENDER", "AGUARDAR"):
        return f"Erro: recomendação '{recommendation}' inválida. Use COMPRAR, VENDER ou AGUARDAR."
    ticker_u = ticker.upper().replace(".SA", "")
    obj = {"ticker": ticker_u, "date": date.today().isoformat(), "recommendation": rec, "reasoning": reasoning}
    db = SessionLocal()
    try:
        db.add(Recommendation(ticker=ticker_u, recommendation=rec, reasoning=reasoning))
        db.commit()
    finally:
        db.close()
    return json.dumps(obj, ensure_ascii=False, indent=2)
