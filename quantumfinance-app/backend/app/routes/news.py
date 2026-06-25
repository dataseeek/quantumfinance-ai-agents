"""News feed endpoint."""
from fastapi import APIRouter, Query

from app.db.base import SessionLocal
from app.db.models import NewsItem
from app.tools.news import search_news


router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/{ticker}")
def list_news(ticker: str, limit: int = Query(20, le=100)):
    db = SessionLocal()
    try:
        items = (db.query(NewsItem)
                   .filter(NewsItem.ticker == ticker.upper())
                   .order_by(NewsItem.published_at.desc().nulls_last(), NewsItem.fetched_at.desc())
                   .limit(limit).all())
        return [
            {"id": n.id, "source": n.source, "title": n.title, "url": n.url,
             "published_at": n.published_at.isoformat() if n.published_at else None,
             "sentiment": n.sentiment}
            for n in items
        ]
    finally:
        db.close()


@router.post("/{ticker}/ingest")
def ingest_now(ticker: str):
    raw = search_news.run(ticker=ticker.upper())
    # Count items after ingest
    db = SessionLocal()
    try:
        count = db.query(NewsItem).filter_by(ticker=ticker.upper()).count()
        return {"ticker": ticker.upper(), "total_in_db": count, "preview": raw[:500]}
    finally:
        db.close()
