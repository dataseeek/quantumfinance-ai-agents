"""Search recent financial news via RSS (Google News per-ticker + InfoMoney + Valor)."""
from datetime import datetime, timedelta
from urllib.parse import quote_plus

import feedparser
from crewai.tools import tool

from app.db.base import SessionLocal
from app.db.models import NewsItem


GENERAL_FEEDS = {
    "InfoMoney": "https://www.infomoney.com.br/feed/",
    "Valor Mercados": "https://valor.globo.com/rss/financas/",
}

COMPANY_KEYWORDS = {
    "VALE3": ["vale", "mineração", "minério", "ferro"],
    "PETR4": ["petrobras", "petróleo", "óleo", "petr4"],
    "BBAS3": ["banco do brasil", "bbas3", "bb "],
    "ITUB4": ["itaú", "itau", "itub4", "itaubanco"],
}

# Per-ticker Google News query — gives high-recall, already filtered to the company.
GOOGLE_NEWS_QUERIES = {
    "VALE3": '"VALE3" OR "Vale S.A." OR "Vale mineração"',
    "PETR4": '"PETR4" OR "Petrobras"',
    "BBAS3": '"BBAS3" OR "Banco do Brasil"',
    "ITUB4": '"ITUB4" OR "Itaú Unibanco" OR "Itaubanco"',
}


def _google_news_url(query: str) -> str:
    return (
        f"https://news.google.com/rss/search?q={quote_plus(query)}"
        f"&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )


@tool("Search Financial News")
def search_news(ticker: str) -> str:
    """Pesquisa notícias financeiras recentes dos últimos 7 dias sobre uma ação da B3.

    Fontes: Google News (consulta por ticker — alta cobertura) + InfoMoney + Valor.
    Dedup por URL. Persiste em tbNews.

    Argumento:
        ticker: símbolo da ação (VALE3, PETR4, BBAS3 ou ITUB4).

    Retorna:
        Texto com até 15 manchetes recentes — fonte, título e data —
        para que o agente possa analisar o sentimento de mercado.
    """
    ticker_u = ticker.upper().replace(".SA", "")
    keywords = COMPANY_KEYWORDS.get(ticker_u, [ticker_u.lower()])
    cutoff = datetime.now() - timedelta(days=7)

    # Build the list of feeds to query for this ticker.
    feeds: list[tuple[str, str, bool]] = []  # (source_label, url, trust_relevance)
    gn_query = GOOGLE_NEWS_QUERIES.get(ticker_u)
    if gn_query:
        feeds.append((f"Google News · {ticker_u}", _google_news_url(gn_query), True))
    for src, url in GENERAL_FEEDS.items():
        feeds.append((src, url, False))

    items: list[dict] = []
    db = SessionLocal()
    try:
        for source, url, trust_relevance in feeds:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue
            for entry in feed.entries[:60]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                # Google News already filters to the query; general feeds need keyword check.
                if not trust_relevance:
                    text = (title + " " + summary).lower()
                    if not any(kw in text for kw in keywords):
                        continue
                pub_struct = entry.get("published_parsed") or entry.get("updated_parsed")
                pub_date = datetime(*pub_struct[:6]) if pub_struct else None
                if pub_date and pub_date < cutoff:
                    continue
                url_item = entry.get("link", "")
                if not url_item:
                    continue
                # Dedup by URL across this run too
                if any(it["url"] == url_item for it in items):
                    continue
                items.append({"source": source, "title": title, "url": url_item, "published_at": pub_date})
                # Persist (dedup by URL)
                exists = db.query(NewsItem).filter_by(url=url_item).first()
                if not exists:
                    db.add(NewsItem(
                        ticker=ticker_u, source=source, title=title, url=url_item,
                        published_at=pub_date,
                    ))
        db.commit()
    finally:
        db.close()

    if not items:
        return f"Nenhuma notícia encontrada para {ticker_u} nos últimos 7 dias."
    lines = [f"Encontradas {len(items)} notícias para {ticker_u}:"]
    for n in items[:15]:
        date_str = n["published_at"].strftime("%Y-%m-%d") if n["published_at"] else "—"
        lines.append(f"- [{n['source']} | {date_str}] {n['title']}")
    return "\n".join(lines)
