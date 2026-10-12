"""Herramienta de análisis fundamental usando Financial Modeling Prep (FMP) y fallback a yfinance."""

from datetime import UTC, datetime

import requests
import yfinance as yf

from src.config import settings
from src.contracts.models import (
    DataProvenance,
    FundamentalRatios,
    ToolErrorObservation,
)
from src.utils.logger import get_logger

logger = get_logger("tools.fundamentals")


def get_company_fundamentals(ticker: str) -> FundamentalRatios | ToolErrorObservation:
    """Obtiene ratios financieros clave de una compañía (P/E, deuda, márgenes, crecimiento).

    Consulta prioritariamente la API de Financial Modeling Prep (FMP). Si la clave de FMP
    no está disponible o se excede la cuota, realiza una degradación elegante a yfinance.

    Args:
        ticker: Símbolo bursátil de la empresa (ej. AAPL, MSFT, GOOGL).

    Returns:
        FundamentalRatios con métricas de solvencia y valuación, o ToolErrorObservation.
    """
    clean_ticker = ticker.strip().upper()

    # Intento 1: Financial Modeling Prep (FMP)
    if settings.fmp_api_key:
        try:
            url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{clean_ticker}?apikey={settings.fmp_api_key}"
            response = requests.get(url, timeout=8)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    ratios = data[0]

                    # Consulta complementaria de métricas clave (Market Cap y PE)
                    metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{clean_ticker}?apikey={settings.fmp_api_key}"
                    metrics_resp = requests.get(metrics_url, timeout=8)
                    metrics_data = metrics_resp.json() if metrics_resp.status_code == 200 else []
                    metric_item = metrics_data[0] if (isinstance(metrics_data, list) and len(metrics_data) > 0) else {}

                    return FundamentalRatios(
                        ticker=clean_ticker,
                        market_cap=metric_item.get("marketCap"),
                        pe_ratio=metric_item.get("peRatioTTM") or ratios.get("priceEarningsRatioTTM"),
                        forward_pe=None,
                        price_to_book=ratios.get("priceToBookRatioTTM"),
                        debt_to_equity=ratios.get("debtEquityRatioTTM"),
                        profit_margins=ratios.get("netProfitMarginTTM"),
                        revenue_growth_yoy=None,
                        provenance=DataProvenance(
                            source_name="Financial Modeling Prep (FMP)",
                            data_quality="LIVE",
                            timestamp_utc=datetime.now(UTC).isoformat(),
                        ),
                    )
            elif response.status_code == 429:
                logger.warning("FMP rate limit alcanzado. Utilizando fallback a yfinance.")
            else:
                logger.warning("FMP respondió con status %s para %s", response.status_code, clean_ticker)
        except Exception as exc:
            logger.warning("Fallo en consulta a FMP (%s). Pasando a fallback yfinance.", exc)

    # Intento 2 (Fallback): yfinance Info
    try:
        yf_ticker = yf.Ticker(clean_ticker)
        info = yf_ticker.info or {}

        if not info or "trailingPE" not in info and "marketCap" not in info:
            return ToolErrorObservation(
                code="FUNDAMENTALS_NOT_FOUND",
                message=f"No se encontraron datos fundamentales para el activo '{clean_ticker}'.",
                retryable=False,
            )

        return FundamentalRatios(
            ticker=clean_ticker,
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            price_to_book=info.get("priceToBook"),
            debt_to_equity=info.get("debtToEquity"),
            profit_margins=info.get("profitMargins"),
            revenue_growth_yoy=info.get("revenueGrowth"),
            provenance=DataProvenance(
                source_name="Yahoo Finance (Fallback)",
                data_quality="DELAYED_15M",
                timestamp_utc=datetime.now(UTC).isoformat(),
            ),
        )

    except Exception as exc:
        logger.error("Error al obtener fundamentales de %s: %s", clean_ticker, exc)
        return ToolErrorObservation(
            code="FUNDAMENTALS_FETCH_ERROR",
            message=f"Error inesperado al recuperar fundamentales de '{clean_ticker}': {str(exc)}",
            retryable=True,
        )
