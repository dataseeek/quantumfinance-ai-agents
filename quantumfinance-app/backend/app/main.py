"""FastAPI entry: mounts REST + WS, runs DB migrations on startup."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.base import Base, engine
from app.db.seed import seed_all
from app.routes import tickers, chart, news, recommendations, cvm, portfolio, agents, settings as settings_route, scheduler as scheduler_route, chat_sessions, backtest as backtest_route, hit_rate as hit_rate_route
from app.ws.chat import router as chat_router
from app.scheduler import manager as scheduler_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (Alembic in prod, but for local SQLite this is OK)
    Base.metadata.create_all(bind=engine)
    seed_all()
    scheduler_manager.start()
    yield
    scheduler_manager.stop()


app = FastAPI(title="QuantumFinance AI Agent Home Broker", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickers.router)
app.include_router(chart.router)
app.include_router(news.router)
app.include_router(recommendations.router)
app.include_router(cvm.router)
app.include_router(portfolio.router)
app.include_router(agents.router)
app.include_router(agents.crew_router)
app.include_router(settings_route.router)
app.include_router(scheduler_route.router)
app.include_router(chat_sessions.router)
app.include_router(chat_router)
app.include_router(backtest_route.router)
app.include_router(hit_rate_route.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
