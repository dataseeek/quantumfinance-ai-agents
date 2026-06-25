"""Seed inicial: 4 tickers, 4 agentes system, 2 crews, 3 portfolios por perfil de risco."""
from sqlalchemy import text

from app.db.base import SessionLocal, engine
from app.db import models


SEED_TICKERS = [
    {"symbol": "VALE3", "name": "Vale S.A.", "sector": "Mineração", "cnpj": "33592510000154"},
    {"symbol": "PETR4", "name": "Petrobras", "sector": "Energia", "cnpj": "33000167000101"},
    {"symbol": "BBAS3", "name": "Banco do Brasil", "sector": "Financeiro", "cnpj": "00000000000191"},
    {"symbol": "ITUB4", "name": "Itaú Unibanco", "sector": "Financeiro", "cnpj": "60872504000123"},
]

SEED_AGENTS = [
    {
        "name": "news_analyst",
        "role": "Analista Sênior de Notícias Financeiras",
        "goal": "Pesquisar notícias recentes sobre {ticker} e classificar o sentimento de mercado como Positivo, Negativo ou Neutro com justificativa.",
        "backstory": (
            "Veterano da Faria Lima. Lê InfoMoney e Valor Econômico todo dia antes do pregão. "
            "Foca em eventos que efetivamente movem preço — guidance, M&A, regulação, commodities — e ignora ruído."
        ),
        "tool_names": ["search_news"],
        "max_iter": 4,
        "is_system": True,
    },
    {
        "name": "technical_analyst",
        "role": "Analista Técnico Quantitativo",
        "goal": "Calcular e interpretar indicadores técnicos (RSI, MACD, SMA, EMA, Bollinger) para {ticker} e classificar a postura técnica.",
        "backstory": (
            "Quant com 10 anos de buy-side. Combina análise gráfica clássica com leitura de momentum. "
            "Procura confluência entre indicadores antes de cravar postura Bullish, Bearish ou Neutra."
        ),
        "tool_names": ["get_price_data", "calculate_indicators"],
        "max_iter": 5,
        "is_system": True,
    },
    {
        "name": "investment_strategist",
        "role": "Estrategista-Chefe de Investimentos",
        "goal": "Sintetizar análise de notícias e análise técnica em uma recomendação COMPRAR, VENDER ou AGUARDAR para {ticker}, com Chain-of-Thought explícito.",
        "backstory": (
            "20 anos no buy-side, ex-PM de fundo long-only. Sabe quando os sinais técnicos e o "
            "noticiário se confirmam — e quando se contradizem. Nunca cita um sem o outro."
        ),
        "tool_names": ["generate_recommendation"],
        "max_iter": 4,
        "is_system": True,
    },
    {
        "name": "cvm_ri_analyst",
        "role": "Analista de Relações com Investidores (CVM)",
        "goal": "Extrair contexto regulatório e fundamentalista de {ticker} a partir de fatos relevantes, comunicados ao mercado e demonstrações trimestrais.",
        "backstory": (
            "Auditor sênior com formação na CVM. Lê IPE, ITR e DFP todo dia. Identifica sinais "
            "fundamentalistas (crescimento de receita, eventos materiais) que o mercado ainda não precificou."
        ),
        "tool_names": ["get_cvm_filings", "get_quarterly_summary"],
        "max_iter": 4,
        "is_system": True,
    },
]

SEED_CREWS = [
    {"name": "Investment Crew", "agent_names": ["news_analyst", "technical_analyst", "investment_strategist"]},
    {"name": "Deep Research Crew", "agent_names": ["news_analyst", "technical_analyst", "cvm_ri_analyst", "investment_strategist"]},
]

DEFAULT_SETTINGS = {
    "news_ingest_cron":   {"cron": "0 */4 * * 1-5", "enabled": True},
    "crew_run_cron":      {"cron": "30 9 * * 1-5",  "enabled": True},
    "cvm_ingest_cron":    {"cron": "0 6 * * 0",     "enabled": True},
    "llm_model":          {"value": "openrouter/openai/gpt-4o-mini"},
    "default_crew":       {"value": "Investment Crew"},
}


SEED_PORTFOLIOS = [
    {
        "name": "Conservador",
        "risk_profile": "conservative",
        "cash_balance": 100000.0,
        "initial_balance": 100000.0,
        "description": (
            "Aceita apenas AGUARDAR e COMPRAR de alta confluência. "
            "Tamanho típico de posição: 1% do capital. Foco em preservação."
        ),
    },
    {
        "name": "Moderado",
        "risk_profile": "moderate",
        "cash_balance": 100000.0,
        "initial_balance": 100000.0,
        "description": (
            "Aceita todas as recomendações (COMPRAR/VENDER/AGUARDAR). "
            "Tamanho típico de posição: 5% do capital. Balanço risco-retorno."
        ),
    },
    {
        "name": "Agressivo",
        "risk_profile": "aggressive",
        "cash_balance": 100000.0,
        "initial_balance": 100000.0,
        "description": (
            "Aceita todas as recomendações e usa alavancagem implícita. "
            "Tamanho típico de posição: 15% do capital. Foco em retorno."
        ),
    },
]


def _ensure_portfolio_columns() -> None:
    """SQLite-friendly migration: add risk_profile + description if missing."""
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(portfolios)"))}
        if "risk_profile" not in cols:
            conn.execute(text("ALTER TABLE portfolios ADD COLUMN risk_profile VARCHAR(20)"))
        if "description" not in cols:
            conn.execute(text("ALTER TABLE portfolios ADD COLUMN description TEXT"))


def seed_all() -> None:
    db = SessionLocal()
    try:
        # Tickers
        for t in SEED_TICKERS:
            if not db.get(models.Ticker, t["symbol"]):
                db.add(models.Ticker(**t))
        db.commit()

        # Agents
        name_to_id: dict[str, int] = {}
        for a in SEED_AGENTS:
            existing = db.query(models.Agent).filter_by(name=a["name"]).first()
            if existing:
                name_to_id[a["name"]] = existing.id
            else:
                agent = models.Agent(**a)
                db.add(agent); db.flush()
                name_to_id[a["name"]] = agent.id
        db.commit()

        # Crews
        for c in SEED_CREWS:
            existing = db.query(models.Crew).filter_by(name=c["name"]).first()
            agent_ids = [name_to_id[n] for n in c["agent_names"] if n in name_to_id]
            if existing:
                existing.agent_ids = agent_ids
            else:
                db.add(models.Crew(name=c["name"], agent_ids=agent_ids, process_type="sequential"))
        db.commit()

        # Portfolios por perfil de risco — migração + seed idempotente
        _ensure_portfolio_columns()
        # Backfill: Default (legado) vira Moderado
        default = db.query(models.Portfolio).filter_by(name="Default").first()
        if default and not default.risk_profile:
            default.name = "Moderado"
            default.risk_profile = "moderate"
            default.description = SEED_PORTFOLIOS[1]["description"]
            db.commit()  # commit the rename so the lookup below sees it
        # Seed novos perfis se ainda não existem
        for p in SEED_PORTFOLIOS:
            existing = db.query(models.Portfolio).filter(
                (models.Portfolio.name == p["name"])
                | (models.Portfolio.risk_profile == p["risk_profile"])
            ).first()
            if existing:
                if not existing.risk_profile:
                    existing.risk_profile = p["risk_profile"]
                if not existing.description:
                    existing.description = p["description"]
            else:
                db.add(models.Portfolio(**p))
        db.commit()

        # Settings
        for k, v in DEFAULT_SETTINGS.items():
            if not db.get(models.Setting, k):
                db.add(models.Setting(key=k, value=v))
        db.commit()

        print(f"Seed OK: {len(SEED_TICKERS)} tickers, {len(SEED_AGENTS)} agents, {len(SEED_CREWS)} crews.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
