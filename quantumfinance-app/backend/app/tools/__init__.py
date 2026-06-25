"""All CrewAI tools, importable by name from the agent builder."""
from app.tools.news import search_news
from app.tools.prices import get_price_data
from app.tools.indicators import calculate_indicators
from app.tools.recommendation import generate_recommendation
from app.tools.cvm import get_cvm_filings, get_quarterly_summary

TOOL_REGISTRY = {
    "search_news": search_news,
    "get_price_data": get_price_data,
    "calculate_indicators": calculate_indicators,
    "generate_recommendation": generate_recommendation,
    "get_cvm_filings": get_cvm_filings,
    "get_quarterly_summary": get_quarterly_summary,
}
