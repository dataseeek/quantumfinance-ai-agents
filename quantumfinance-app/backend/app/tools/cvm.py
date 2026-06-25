"""CVM Dados Abertos integration: IPE (fatos relevantes) + ITR (trimestrais)."""
import csv
import io
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
from crewai.tools import tool

from app.db.base import SessionLocal
from app.db.models import CvmFiling, Ticker


CACHE_DIR = Path("data/cvm_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CVM_BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
RELEVANT_CATEGORIES = {
    "Fato Relevante", "Comunicado ao Mercado", "Aviso aos Acionistas",
    "Aviso aos Debenturistas", "Press-release",
}


def _ticker_to_cnpj(ticker: str) -> str | None:
    db = SessionLocal()
    try:
        t = db.get(Ticker, ticker.upper().replace(".SA", ""))
        return t.cnpj if t else None
    finally:
        db.close()


def _download_zip(doc_type: str, year: int) -> Path | None:
    """Baixa um ZIP da CVM e cacheia localmente."""
    fname = f"{doc_type.lower()}_cia_aberta_{year}.zip"
    cache = CACHE_DIR / fname
    if cache.exists() and cache.stat().st_size > 0:
        return cache
    url = f"{CVM_BASE}/{doc_type.upper()}/DADOS/{fname}"
    try:
        r = httpx.get(url, timeout=60.0, follow_redirects=True)
        r.raise_for_status()
        cache.write_bytes(r.content)
        return cache
    except Exception as e:
        return None


def _read_csv_from_zip(zip_path: Path, csv_name: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if name == csv_name or name.endswith("/" + csv_name):
                with z.open(name) as f:
                    return pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    return pd.DataFrame()


def fetch_ipe_filings(ticker: str, days: int = 90) -> list[dict]:
    """Returns list of dicts with category/title/date/link for the given ticker."""
    cnpj = _ticker_to_cnpj(ticker)
    if not cnpj:
        return []
    cnpj_norm = cnpj.zfill(14)
    # Normalize to "00.000.000/0000-00" format used by CVM
    cnpj_fmt = f"{cnpj_norm[:2]}.{cnpj_norm[2:5]}.{cnpj_norm[5:8]}/{cnpj_norm[8:12]}-{cnpj_norm[12:14]}"

    cutoff = datetime.now() - timedelta(days=days)
    year = datetime.now().year
    results: list[dict] = []
    for y in (year, year - 1):
        zip_path = _download_zip("IPE", y)
        if not zip_path:
            continue
        csv_name = f"ipe_cia_aberta_{y}.csv"
        df = _read_csv_from_zip(zip_path, csv_name)
        if df.empty:
            continue
        # Filter by CNPJ — CSV stores formatted CNPJs (00.000.000/0001-00),
        # so normalize both sides to digits-only before comparing.
        cnpj_col = next((c for c in df.columns if "CNPJ" in c.upper()), None)
        if not cnpj_col:
            continue
        cnpj_normalized = df[cnpj_col].fillna("").str.replace(r"\D", "", regex=True)
        df_t = df[cnpj_normalized.str.startswith(cnpj_norm[:8])]
        for _, row in df_t.iterrows():
            cat = str(row.get("Categoria", ""))
            if cat not in RELEVANT_CATEGORIES:
                continue
            date_str = str(row.get("Data_Entrega", "") or row.get("Data_Referencia", ""))
            try:
                filed_at = datetime.fromisoformat(date_str.split("T")[0])
            except Exception:
                filed_at = None
            if filed_at and filed_at < cutoff:
                continue
            results.append({
                "category": cat,
                "title": str(row.get("Assunto", "") or row.get("Tipo", "")),
                "filed_at": filed_at,
                "link": str(row.get("Link_Download", "")),
                "cnpj": cnpj_fmt,
            })
    results.sort(key=lambda x: x["filed_at"] or datetime.min, reverse=True)
    return results[:30]


@tool("Get CVM Filings")
def get_cvm_filings(ticker: str, days: int = 90) -> str:
    """Busca fatos relevantes e comunicados ao mercado registrados na CVM (IPE) para uma ação.

    Argumentos:
        ticker: símbolo da ação (VALE3, PETR4, BBAS3, ITUB4).
        days: dias retroativos a considerar (default 90).

    Retorna:
        Texto com as categorias, datas, títulos e links dos comunicados oficiais à CVM.
        Use isso como contexto regulatório/fundamentalista oficial — complementa news RSS.
    """
    items = fetch_ipe_filings(ticker, days)
    if not items:
        return f"Nenhum fato relevante ou comunicado CVM encontrado para {ticker} nos últimos {days} dias."
    ticker_u = ticker.upper().replace(".SA", "")
    # Persist
    db = SessionLocal()
    try:
        for it in items:
            db.add(CvmFiling(
                ticker=ticker_u, cnpj=it["cnpj"], doc_type="IPE",
                category=it["category"], title=it["title"],
                link=it["link"], filed_at=it["filed_at"],
            ))
        db.commit()
    finally:
        db.close()

    lines = [f"Encontrados {len(items)} comunicados CVM para {ticker_u}:"]
    for it in items[:15]:
        date_str = it["filed_at"].strftime("%Y-%m-%d") if it["filed_at"] else "—"
        lines.append(f"- [{it['category']} | {date_str}] {it['title']}")
    return "\n".join(lines)


@tool("Get Quarterly Summary")
def get_quarterly_summary(ticker: str, last_n: int = 4) -> str:
    """Extrai resumo das últimas N trimestrais (ITR) da CVM para uma ação.

    Argumentos:
        ticker: símbolo da ação.
        last_n: número de trimestres a retornar (default 4).

    Retorna:
        Texto com receita líquida e lucro líquido das últimas N trimestrais + crescimento YoY.
        Use para contexto fundamentalista.
    """
    cnpj = _ticker_to_cnpj(ticker)
    if not cnpj:
        return f"Ticker {ticker} não tem CNPJ cadastrado."
    cnpj_norm = cnpj.zfill(14)
    year = datetime.now().year
    rows: list[dict] = []
    for y in (year, year - 1, year - 2):
        zip_path = _download_zip("ITR", y)
        if not zip_path:
            continue
        # ITR has multiple CSVs; the DRE (income statement) consolidated is what we want
        try:
            with zipfile.ZipFile(zip_path) as z:
                for name in z.namelist():
                    if "DRE_con" in name and name.endswith(".csv"):
                        with z.open(name) as f:
                            df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
                        cnpj_col = next((c for c in df.columns if "CNPJ" in c.upper()), None)
                        if not cnpj_col:
                            continue
                        cnpj_norm_col = df[cnpj_col].fillna("").str.replace(r"\D", "", regex=True)
                        df_t = df[cnpj_norm_col.str.startswith(cnpj_norm[:8])]
                        for _, r in df_t.iterrows():
                            desc = str(r.get("DS_CONTA", ""))
                            value = r.get("VL_CONTA", "0")
                            ref = str(r.get("DT_REFER", ""))
                            try:
                                v = float(str(value).replace(",", "."))
                            except Exception:
                                v = 0.0
                            if "Receita" in desc and "Líquida" in desc:
                                rows.append({"date": ref, "metric": "receita_liquida", "value": v})
                            elif "Lucro" in desc and "Líquido" in desc and "Período" in desc:
                                rows.append({"date": ref, "metric": "lucro_liquido", "value": v})
        except Exception:
            continue
    if not rows:
        return f"Sem dados ITR (trimestrais) encontrados para {ticker}."
    # Pivot
    df = pd.DataFrame(rows).drop_duplicates(["date", "metric"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    pivot = df.pivot_table(index="date", columns="metric", values="value", aggfunc="first").sort_index().tail(last_n)
    lines = [f"Últimas {len(pivot)} trimestrais (ITR) — {ticker}:"]
    for d, row in pivot.iterrows():
        rec = row.get("receita_liquida", 0); luc = row.get("lucro_liquido", 0)
        lines.append(f"- {d.strftime('%Y-%m-%d')}: Receita R$ {rec/1e6:,.1f}mi | Lucro R$ {luc/1e6:,.1f}mi")
    return "\n".join(lines)
