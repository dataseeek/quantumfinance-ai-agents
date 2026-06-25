"""Hit-rate / acurácia das recomendações vs preço real."""
from fastapi import APIRouter, Query

from app.tools.hit_rate import compute_hit_rate


router = APIRouter(prefix="/api/hit-rate", tags=["hit-rate"])


@router.get("")
def get_hit_rate(
    horizon_days: int = Query(3, ge=1, le=60, description="Janela em dias de pregão para avaliar D+N"),
    since_days: int | None = Query(None, ge=1, le=365, description="Restringe à janela recente (em dias corridos)"),
):
    """Calcula a acurácia das recomendações comparando com o preço real D+N.

    Regras:
    - COMPRAR acerta se o preço subiu > 0.5%
    - VENDER acerta se o preço caiu > 0.5%
    - AGUARDAR acerta se ficou lateral (|move| < 1%)
    """
    return compute_hit_rate(horizon_days=horizon_days, since_days=since_days)
