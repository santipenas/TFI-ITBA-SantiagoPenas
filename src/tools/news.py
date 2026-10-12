"""Herramienta de búsqueda de noticias financieras y catalizadores mediante Tavily Search."""

from datetime import UTC, datetime

from tavily import TavilyClient

from src.config import settings
from src.contracts.models import (
    DataProvenance,
    FinancialNewsOutput,
    NewsArticle,
    ToolErrorObservation,
)
from src.utils.logger import get_logger

logger = get_logger("tools.news")


def get_financial_news(
    query: str,
    max_results: int = 4,
) -> FinancialNewsOutput | ToolErrorObservation:
    """Busca noticias financieras recientes, catalizadores o reportes de earnings.

    Args:
        query: Consulta de búsqueda contextual (ej. 'NVDA earnings guidance', 'AAPL revenue').
        max_results: Cantidad máxima de artículos a incluir (por defecto 4, máximo 8).

    Returns:
        FinancialNewsOutput con artículos y resúmenes limpios, o ToolErrorObservation.
    """
    if not settings.tavily_api_key:
        logger.warning("Tavily API Key no configurada.")
        return ToolErrorObservation(
            code="TAVILY_KEY_MISSING",
            message="No se configuró la clave de API para Tavily. Búsqueda de noticias desactivada.",
            retryable=False,
        )

    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        # Búsqueda optimizada para noticias y contexto financiero
        response = client.search(
            query=query,
            search_depth="advanced",
            topic="news",
            max_results=min(max_results, 8),
        )

        results = response.get("results", [])
        articles: list[NewsArticle] = []

        for item in results:
            articles.append(
                NewsArticle(
                    title=item.get("title", "Sin título"),
                    url=item.get("url", ""),
                    published_date=item.get("published_date"),
                    snippet=item.get("content", "")[:350],  # Acotado para no sobrecargar contexto
                )
            )

        provenance = DataProvenance(
            source_name="Tavily Search API",
            data_quality="LIVE",
            timestamp_utc=datetime.now(UTC).isoformat(),
        )

        return FinancialNewsOutput(
            query=query,
            articles=articles,
            provenance=provenance,
        )

    except Exception as exc:
        logger.error("Error en búsqueda de noticias con Tavily: %s", exc)
        return ToolErrorObservation(
            code="NEWS_SEARCH_ERROR",
            message=f"Error al consultar noticias con Tavily: {str(exc)}",
            retryable=True,
        )
