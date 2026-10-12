"""Modelos de datos generales, observaciones de herramientas y trazabilidad de proveniencia."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DataProvenance(BaseModel):
    """Metadatos de auditoría y calidad de los datos obtenidos."""

    source_name: str = Field(..., description="Nombre del servicio de origen (yfinance, FMP, Tavily, Alpaca)")
    data_quality: Literal["LIVE", "DELAYED_15M", "CACHED", "STALE", "SIMULATED"] = Field(
        default="LIVE",
        description="Calidad o retraso del dato obtenido",
    )
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Fecha y hora de captura del dato",
    )
    currency: str = Field(default="USD", description="Moneda de cotización")


class TechnicalIndicators(BaseModel):
    """Conjunto de indicadores técnicos calculados localmente sobre un activo."""

    current_price: float
    rsi_14: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    atr_14: float | None = None
    trend_bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    daily_change_pct: float | None = None


class TechnicalSummaryOutput(BaseModel):
    """Resultado del análisis técnico retornado por la herramienta."""

    ticker: str
    provenance: DataProvenance
    indicators: TechnicalIndicators


class FundamentalRatios(BaseModel):
    """Ratios financieros y fundamentales clave de una empresa."""

    ticker: str
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    debt_to_equity: float | None = None
    profit_margins: float | None = None
    revenue_growth_yoy: float | None = None
    provenance: DataProvenance


class NewsArticle(BaseModel):
    """Artículo de noticia financiera o catalizador de mercado."""

    title: str
    url: str
    published_date: str | None = None
    snippet: str


class FinancialNewsOutput(BaseModel):
    """Conjunto de noticias y catalizadores encontrados."""

    query: str
    articles: list[NewsArticle]
    provenance: DataProvenance


class PositionItem(BaseModel):
    """Detalle de una posición abierta en la cartera."""

    symbol: str
    qty: float
    side: Literal["long", "short"]
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float


class AccountSummary(BaseModel):
    """Resumen de la cuenta de trading (Alpaca Paper)."""

    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    open_positions: list[PositionItem]
    is_trading_blocked: bool = False
    provenance: DataProvenance


class ToolErrorObservation(BaseModel):
    """Observación estructurada ante fallos controlados en herramientas."""

    status: Literal["error"] = "error"
    code: str
    message: str
    retryable: bool = False
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
