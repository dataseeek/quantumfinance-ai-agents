from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Date, JSON, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Ticker(Base):
    __tablename__ = "tickers"
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sector: Mapped[str] = mapped_column(String(60))
    cnpj: Mapped[Optional[str]] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("tickers.symbol"), index=True)
    source: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20))
    impact_score: Mapped[Optional[float]] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CvmFiling(Base):
    __tablename__ = "cvm_filings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("tickers.symbol"), index=True)
    cnpj: Mapped[str] = mapped_column(String(20))
    doc_type: Mapped[str] = mapped_column(String(20))  # IPE / ITR / DFP
    category: Mapped[Optional[str]] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(Text)
    link: Mapped[Optional[str]] = mapped_column(String(500))
    filed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/ok/error
    ticker: Mapped[Optional[str]] = mapped_column(String(10), ForeignKey("tickers.symbol"))
    crew_name: Mapped[Optional[str]] = mapped_column(String(60))
    raw_output: Mapped[Optional[str]] = mapped_column(Text)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("tickers.symbol"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    recommendation: Mapped[str] = mapped_column(String(15))
    close_price: Mapped[Optional[float]] = mapped_column(Float)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agent_runs.id"))


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    title: Mapped[Optional[str]] = mapped_column(String(200))
    model_used: Mapped[Optional[str]] = mapped_column(String(120))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user/assistant/tool/system
    content: Mapped[str] = mapped_column(Text)
    agent_name: Mapped[Optional[str]] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    role: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str] = mapped_column(Text)
    backstory: Mapped[str] = mapped_column(Text)
    tool_names: Mapped[list] = mapped_column(JSON, default=list)
    max_iter: Mapped[int] = mapped_column(Integer, default=4)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Crew(Base):
    __tablename__ = "crews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    agent_ids: Mapped[list] = mapped_column(JSON, default=list)
    process_type: Mapped[str] = mapped_column(String(20), default="sequential")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    cash_balance: Mapped[float] = mapped_column(Float, default=100000.0)
    initial_balance: Mapped[float] = mapped_column(Float, default=100000.0)
    # Risk profile: conservative / moderate / aggressive
    risk_profile: Mapped[Optional[str]] = mapped_column(String(20), default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("tickers.symbol"))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, ForeignKey("portfolios.id"), index=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("tickers.symbol"))
    side: Mapped[str] = mapped_column(String(4))  # BUY / SELL
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="executed")
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
