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
    """Obtiene ratios financieros clave de una compañía (P/E, deuda, márgenes, crecimiento, DCF).

    Consulta prioritariamente la API de Financial Modeling Prep (FMP Stable API). Si la clave de FMP
    no está disponible o se excede la cuota, realiza una degradación elegante a yfinance.

    Args:
        ticker: Símbolo bursátil de la empresa (ej. AAPL, MSFT, GOOGL).

    Returns:
        FundamentalRatios con métricas de solvencia, valuación y proyecciones, o ToolErrorObservation.
    """
    clean_ticker = ticker.strip().upper()

    # Intento 1: Financial Modeling Prep (FMP Stable API)
    if settings.fmp_api_key:
        try:
            # 1. Ratios TTM principales
            ratios_url = f"https://financialmodelingprep.com/stable/ratios-ttm?symbol={clean_ticker}&apikey={settings.fmp_api_key}"
            response = requests.get(ratios_url, timeout=7)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    ratios = data[0]

                    # 2. Consultas complementarias en FMP (Profile, Growth, Target Consensus, DCF)
                    profile: dict = {}
                    try:
                        p_resp = requests.get(
                            f"https://financialmodelingprep.com/stable/profile?symbol={clean_ticker}&apikey={settings.fmp_api_key}",
                            timeout=5,
                        )
                        if p_resp.status_code == 200 and isinstance(p_resp.json(), list) and len(p_resp.json()) > 0:
                            profile = p_resp.json()[0]
                    except Exception:
                        pass

                    growth: dict = {}
                    try:
                        g_resp = requests.get(
                            f"https://financialmodelingprep.com/stable/financial-growth?symbol={clean_ticker}&apikey={settings.fmp_api_key}",
                            timeout=5,
                        )
                        if g_resp.status_code == 200 and isinstance(g_resp.json(), list) and len(g_resp.json()) > 0:
                            growth = g_resp.json()[0]
                    except Exception:
                        pass

                    target: dict = {}
                    try:
                        t_resp = requests.get(
                            f"https://financialmodelingprep.com/stable/price-target-consensus?symbol={clean_ticker}&apikey={settings.fmp_api_key}",
                            timeout=5,
                        )
                        if t_resp.status_code == 200 and isinstance(t_resp.json(), list) and len(t_resp.json()) > 0:
                            target = t_resp.json()[0]
                    except Exception:
                        pass

                    dcf: dict = {}
                    try:
                        d_resp = requests.get(
                            f"https://financialmodelingprep.com/stable/discounted-cash-flow?symbol={clean_ticker}&apikey={settings.fmp_api_key}",
                            timeout=5,
                        )
                        if d_resp.status_code == 200 and isinstance(d_resp.json(), list) and len(d_resp.json()) > 0:
                            dcf = d_resp.json()[0]
                    except Exception:
                        pass

                    return FundamentalRatios(
                        ticker=clean_ticker,
                        company_name=profile.get("companyName"),
                        sector=profile.get("sector"),
                        industry=profile.get("industry"),
                        market_cap=profile.get("marketCap"),
                        pe_ratio=(
                            ratios.get("priceToEarningsRatioTTM")
                            or ratios.get("priceEarningsRatioTTM")
                            or ratios.get("peRatioTTM")
                        ),
                        forward_pe=ratios.get("forwardPriceToEarningsGrowthRatioTTM"),
                        price_to_book=ratios.get("priceToBookRatioTTM") or ratios.get("priceBookValueRatioTTM"),
                        debt_to_equity=ratios.get("debtToEquityRatioTTM") or ratios.get("debtEquityRatioTTM"),
                        profit_margins=ratios.get("netProfitMarginTTM"),
                        operating_margins=ratios.get("operatingProfitMarginTTM"),
                        revenue_growth_yoy=growth.get("revenueGrowth"),
                        beta=profile.get("beta"),
                        target_consensus_price=target.get("targetConsensus"),
                        dcf_fair_value=dcf.get("dcf"),
                        provenance=DataProvenance(
                            source_name="Financial Modeling Prep (FMP Stable API)",
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
            company_name=info.get("shortName") or info.get("longName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            price_to_book=info.get("priceToBook"),
            debt_to_equity=info.get("debtToEquity"),
            profit_margins=info.get("profitMargins"),
            operating_margins=info.get("operatingMargins"),
            revenue_growth_yoy=info.get("revenueGrowth"),
            beta=info.get("beta"),
            target_consensus_price=info.get("targetMeanPrice"),
            dcf_fair_value=None,
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
