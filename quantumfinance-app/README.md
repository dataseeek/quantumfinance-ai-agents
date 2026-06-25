# QuantumFinance AI Agent Home Broker

Aplicação web multi-agente para análise e simulação de Swing Trade nas ações da B3 (VALE3, PETR4, BBAS3, ITUB4), com:

- **3 agentes CrewAI** (News, Technical, Investment Strategist) + 1 agente CVM RI Analyst
- **Home broker simulado** com candlestick chart (TradingView Lightweight Charts), watchlist e order entry (paper trading)
- **News feed** via RSS InfoMoney + Valor
- **CVM RI** via portal Dados Abertos (IPE — fatos relevantes + comunicados ao mercado)
- **Chat WebSocket** para conversar com o crew ou agentes individuais
- **Gestão de agentes** (CRUD) — crie agentes custom via UI
- **Scheduler** (APScheduler embutido) para ingestão automática de news/CVM e run diário do crew

Stack: FastAPI + SQLAlchemy + SQLite · React + Vite + TanStack Query + Tailwind v4 · CrewAI + OpenRouter

## Pré-requisitos

- Python 3.10+
- Node 20+
- Chave OpenRouter (https://openrouter.ai/keys)

## Quick start (local, sem Docker)

### Backend

```bash
cd backend
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # preencha OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

Backend sobe em http://localhost:8000 · docs OpenAPI em http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

Frontend sobe em http://localhost:5173 · proxy `/api/*` → http://localhost:8000

## Quick start (Docker Compose)

```bash
cp backend/.env.example backend/.env       # preencher OPENROUTER_API_KEY
docker compose up -d
```

- App: http://localhost:3000
- API: http://localhost:8000

## Estrutura

```
quantumfinance-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # pydantic-settings
│   │   ├── db/                  # SQLAlchemy models + seed
│   │   ├── tools/               # 6 tools CrewAI (news, prices, indicators, recommendation, fib, swing, cvm)
│   │   ├── agents/              # LLM factory, agent builder, crew assembly
│   │   ├── routes/              # REST endpoints
│   │   ├── ws/                  # Chat WebSocket
│   │   └── scheduler/           # APScheduler jobs
│   ├── data/                    # SQLite DB + CVM cache
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/               # Dashboard, News, CVM, Chat, Portfolio, Agents, Settings
    │   ├── components/          # CandlestickChart, RecPill
    │   ├── api.ts               # SDK
    │   └── App.tsx
    ├── package.json
    └── Dockerfile
```

## API principal

| Endpoint | Função |
|---|---|
| `GET  /api/health` | Health check |
| `GET  /api/tickers` | Watchlist + quotes |
| `GET  /api/chart/{ticker}` | OHLCV + indicadores |
| `GET  /api/news/{ticker}` | Feed paginado |
| `POST /api/news/{ticker}/ingest` | Ingere RSS agora |
| `GET  /api/cvm/{ticker}/filings` | Fatos relevantes CVM |
| `GET  /api/recommendations` | Recomendações recentes |
| `POST /api/recommendations/run` | Dispara crew (body: `{ticker, crew_id?}`) |
| `GET  /api/recommendations/{ticker}/swing-plan` | Plano de Swing |
| `GET  /api/portfolios` | Portfolios + posições + P&L |
| `POST /api/portfolios/{id}/orders` | Paper order (BUY/SELL) |
| `GET  /api/agents` | List agentes |
| `POST /api/agents` | Cria agente custom |
| `GET  /api/crews` | List crews |
| `GET  /api/scheduler/jobs` | Jobs ativos |
| `POST /api/scheduler/run/{id}` | Dispara job manualmente |
| `WS   /api/chat` | Chat streaming com agentes |
| `GET/PUT /api/settings/{key}` | KV store de settings |

OpenAPI completo: http://localhost:8000/docs

## Schedulers (APScheduler)

Embutidos no FastAPI, configuráveis via UI ou tabela `settings`:

| Job | Cron default | Ação |
|---|---|---|
| `news` | `0 */4 * * 1-5` | Ingere RSS InfoMoney + Valor a cada 4h, seg-sex |
| `crew` | `30 9 * * 1-5` | Roda Investment Crew para os 4 tickers, 09:30 BRT seg-sex |
| `cvm` | `0 6 * * 0` | Ingere IPE da CVM aos domingos 06:00 |

Mudanças via Settings → "Reload schedulers" — não precisa reiniciar.

## CVM Dados Abertos

A integração CVM lê IPE (Informações Periódicas e Eventuais) diretamente do portal de Dados Abertos:

- Base: `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/`
- Sem chave de API
- Categorias filtradas: Fato Relevante, Comunicado ao Mercado, Aviso aos Acionistas
- Cache local em `backend/data/cvm_cache/`
- CNPJs mapeados no seed (VALE3, PETR4, BBAS3, ITUB4)

## LLM via OpenRouter

Default: `openrouter/openai/gpt-4o-mini` (~$0.001 por crew run).

Para usar modelo free, edite Settings → llm_model:
- `openrouter/google/gemma-4-31b-it:free`
- `openrouter/qwen/qwen3-next-80b-a3b-instruct:free`

> Note: modelos free têm rate limits agressivos — para delivery acadêmico, gpt-4o-mini é mais confiável.

## Roadmap

- [ ] Alertas Telegram/email
- [ ] Multi-user auth
- [ ] PostgreSQL para prod
- [ ] Caddy + HTTPS para cloud
- [ ] Heatmap de hit-rate ao longo do tempo
- [ ] Position sizing automático (Kelly)
- [ ] Walk-forward backtest

## Autor

**Ricardo Frasson** · MBA Data Science & AI · FIAP · 2026
