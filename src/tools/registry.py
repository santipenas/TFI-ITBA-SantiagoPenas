"""Registro centralizado de herramientas para los agentes de LangGraph."""

from langchain_core.tools import tool

from src.tools.market_data import get_stock_technical_summary
from src.tools.fundamentals import get_company_fundamentals
from src.tools.news import get_financial_news
from src.tools.alpaca_broker import get_account_and_positions


@tool
def tool_stock_technical_summary(ticker: str, timeframe: str = "1d", period_days: int = 250) -> str:
    """Calcula medias móviles (SMA 20, 50, 200), RSI (14), ATR (14) y sesgo direccional de un ticker.

    Úsalo cuando necesites analizar el gráfico, tendencia o momentum de una acción o ETF.
    """
    res = get_stock_technical_summary(ticker=ticker, timeframe=timeframe, period_days=period_days)
    return res.model_dump_json()


@tool
def tool_company_fundamentals(ticker: str) -> str:
    """Obtiene ratios financieros clave (P/E, deuda sobre patrimonio, márgenes y market cap) de una empresa.

    Úsalo para evaluar la solvencia y valuación fundamental del negocio antes de tomar una decisión de inversión.
    """
    res = get_company_fundamentals(ticker=ticker)
    return res.model_dump_json()


@tool
def tool_financial_news(query: str, max_results: int = 4) -> str:
    """Busca noticias financieras recientes, catalizadores, anuncios de resultados o eventos corporativos.

    Úsalo para verificar eventos actuales, rumores o razones detrás de movimientos bruscos de precio.
    """
    res = get_financial_news(query=query, max_results=max_results)
    return res.model_dump_json()


@tool
def tool_account_and_positions() -> str:
    """Consulta el saldo de capital (equity), efectivo disponible (cash) y las posiciones abiertas en Alpaca Paper Trading.

    Úsalo para verificar la exposición actual de la cartera y el capital disponible para operar.
    """
    res = get_account_and_positions()
    return res.model_dump_json()


# Colecciones de herramientas autorizadas según el agente
ANALYST_TOOLS = [
    tool_stock_technical_summary,
    tool_company_fundamentals,
    tool_financial_news,
]

RISK_GATE_TOOLS = [
    tool_account_and_positions,
]

ALL_TOOLS = [
    tool_stock_technical_summary,
    tool_company_fundamentals,
    tool_financial_news,
    tool_account_and_positions,
]
