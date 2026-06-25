"""CVM filings endpoint."""
from fastapi import APIRouter

from app.db.base import SessionLocal
from app.db.models import CvmFiling
from app.tools.cvm import fetch_ipe_filings


router = APIRouter(prefix="/api/cvm", tags=["cvm"])


@router.get("/{ticker}/filings")
def list_filings(ticker: str, days: int = 90, refresh: bool = False):
    ticker_u = ticker.upper().replace(".SA", "")
    db = SessionLocal()
    try:
        if refresh:
            items = fetch_ipe_filings(ticker_u, days)
            for it in items:
                db.add(CvmFiling(
                    ticker=ticker_u, cnpj=it["cnpj"], doc_type="IPE",
                    category=it["category"], title=it["title"],
                    link=it["link"], filed_at=it["filed_at"],
                ))
            db.commit()
        items = (db.query(CvmFiling).filter_by(ticker=ticker_u)
                   .order_by(CvmFiling.filed_at.desc().nulls_last()).limit(50).all())
        return [
            {"id": f.id, "category": f.category, "title": f.title,
             "filed_at": f.filed_at.isoformat() if f.filed_at else None,
             "link": f.link, "doc_type": f.doc_type}
            for f in items
        ]
    finally:
        db.close()
