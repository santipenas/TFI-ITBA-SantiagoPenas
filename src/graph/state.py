"""Definición del estado global del grafo de agentes (LangGraph AgentState)."""

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from src.contracts.trade_schemas import (
    OrderExecutionReceipt,
    TradeProposalDraft,
    ValidatedTradeProposal,
)


class AgentState(BaseModel):
    """Estado tipado que fluye a través de los nodos del StateGraph."""

    # Historial de conversación con acumulador nativo de LangGraph
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)

    # Contexto activo del análisis
    current_ticker: str | None = Field(default=None, description="Símbolo del activo en análisis")
    analysis_summary: str | None = Field(default=None, description="Síntesis del análisis de mercado")

    # Propuestas y flujo de gobernanza
    trade_proposal: TradeProposalDraft | None = Field(default=None, description="Borrador generado por el analista")
    validated_proposal: ValidatedTradeProposal | None = Field(default=None, description="Propuesta auditada por riesgo")
    order_receipt: OrderExecutionReceipt | None = Field(
        default=None, description="Comprobante de orden ejecutada en Alpaca"
    )

    # Preferencias del usuario y metadatos de sesión
    user_profile: dict[str, Any] = Field(
        default_factory=lambda: {"risk_profile": "MODERATE", "watchlist": ["AAPL", "NVDA", "MSFT", "SPY"]},
        description="Perfil de riesgo y preferencias del usuario",
    )

    # Control de flujo y enrutamiento
    next_step: str = Field(default="supervisor", description="Siguiente nodo a ejecutar")
