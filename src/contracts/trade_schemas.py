"""Contratos y esquemas Pydantic v2 para órdenes, propuestas de trading y validaciones de riesgo."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TradeProposalDraft(BaseModel):
    """Borrador de propuesta de trading generado por el Analista de Mercado."""

    ticker: str = Field(..., description="Símbolo bursátil (ej. NVDA, AAPL, SPY)", min_length=1, max_length=10)
    side: Literal["BUY", "SELL"] = Field(..., description="Dirección de la operación: BUY (Long) o SELL (Short)")
    order_type: Literal["market", "limit"] = Field(default="market", description="Tipo de orden")
    limit_price: float | None = Field(default=None, description="Precio límite si order_type es limit", gt=0)
    suggested_entry_price: float = Field(..., description="Precio estimado de entrada al momento del análisis", gt=0)
    suggested_stop_loss: float = Field(..., description="Precio de Stop-Loss sugerido", gt=0)
    suggested_take_profit: float = Field(..., description="Precio de Take-Profit sugerido", gt=0)
    time_horizon: Literal["INTRADAY", "SWING"] = Field(default="SWING", description="Horizonte temporal")
    thesis_summary: str = Field(..., description="Resumen conciso de la tesis fundamental/técnica")
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Fecha y hora de generación de la propuesta",
    )

    @model_validator(mode="after")
    def validate_sl_tp_levels(self) -> "TradeProposalDraft":
        """Valida la coherencia de los niveles de SL y TP según el lado de la orden."""
        entry = self.limit_price if (self.order_type == "limit" and self.limit_price) else self.suggested_entry_price

        if self.side == "BUY":
            if self.suggested_stop_loss >= entry:
                raise ValueError(
                    "Para una compra (BUY), el Stop-Loss debe ser estrictamente menor que el precio de entrada."
                )
            if self.suggested_take_profit <= entry:
                raise ValueError(
                    "Para una compra (BUY), el Take-Profit debe ser estrictamente mayor que el precio de entrada."
                )
        elif self.side == "SELL":
            if self.suggested_stop_loss <= entry:
                raise ValueError(
                    "Para una venta corta (SELL), el Stop-Loss debe ser estrictamente mayor que el precio de entrada."
                )
            if self.suggested_take_profit >= entry:
                raise ValueError(
                    "Para una venta corta (SELL), el Take-Profit debe ser estrictamente menor que el precio de entrada."
                )
        return self


class RiskCheckResult(BaseModel):
    """Resultado de la evaluación del motor determinista de riesgo."""

    is_approved: bool = Field(..., description="Indica si la propuesta cumple el 100% de las reglas duras")
    adjusted_qty: int = Field(
        default=0, description="Cantidad de acciones autorizada tras dimensionamiento de riesgo", ge=0
    )
    max_risk_amount_usd: float = Field(default=0.0, description="Pérdida máxima estimada en USD hasta el SL")
    risk_percentage_equity: float = Field(default=0.0, description="Porcentaje real del equity arriesgado")
    position_value_usd: float = Field(default=0.0, description="Valor nominal total de la posición")
    position_percentage_equity: float = Field(default=0.0, description="Porcentaje de concentración respecto al equity")
    rejection_reasons: list[str] = Field(default_factory=list, description="Lista de motivos de rechazo si aplica")
    evaluation_timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ValidatedTradeProposal(BaseModel):
    """Propuesta de trade validada y lista para revisión humana (HITL)."""

    proposal_id: str = Field(..., description="Identificador único de la propuesta")
    draft: TradeProposalDraft
    risk_evaluation: RiskCheckResult
    status: Literal["PENDING_APPROVAL", "APPROVED", "REJECTED", "EXPIRED", "EXECUTED"] = Field(
        default="PENDING_APPROVAL",
        description="Estado de la propuesta en el ciclo de vida",
    )
    human_verdict_reason: str | None = Field(default=None, description="Comentario o motivo de la decisión humana")


class OrderExecutionReceipt(BaseModel):
    """Comprobante de ejecución emitido tras interactuar con Alpaca Paper Trading."""

    success: bool
    broker_order_id: str | None = None
    client_order_id: str
    ticker: str
    side: str
    qty: int
    order_type: str
    status: str  # e.g., "accepted", "filled", "rejected", "held"
    submitted_at_utc: str
    error_message: str | None = None
    provenance: str = "Alpaca Paper Trading API"
