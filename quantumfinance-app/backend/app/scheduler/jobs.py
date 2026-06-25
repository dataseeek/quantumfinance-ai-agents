"""Scheduled jobs: ingest news, run crew daily, ingest CVM."""
import asyncio

from app.agents.crew import run_crew_for_ticker
from app.db.base import SessionLocal
from app.db.models import Ticker
from app.tools.news import search_news
from app.tools.cvm import fetch_ipe_filings


def ingest_news_job():
    db = SessionLocal()
    try:
        for t in db.query(Ticker).filter_by(active=True).all():
            try:
                search_news.run(ticker=t.symbol)
            except Exception as e:
                print(f"news ingest failed for {t.symbol}: {e}")
    finally:
        db.close()


def ingest_cvm_job():
    db = SessionLocal()
    try:
        for t in db.query(Ticker).filter_by(active=True).all():
            try:
                fetch_ipe_filings(t.symbol, days=30)
            except Exception as e:
                print(f"cvm ingest failed for {t.symbol}: {e}")
    finally:
        db.close()


def run_crew_job():
    """Daily crew run for all active tickers."""
    db = SessionLocal()
    try:
        tickers = [t.symbol for t in db.query(Ticker).filter_by(active=True).all()]
    finally:
        db.close()

    async def _go():
        for sym in tickers:
            try:
                await run_crew_for_ticker(sym)
            except Exception as e:
                print(f"crew run failed for {sym}: {e}")

    asyncio.run(_go())
