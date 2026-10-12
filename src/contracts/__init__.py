"""Contratos de datos, modelos tipados y esquemas de validación del sistema."""

from src.contracts.models import (
    AccountSummary,
    DataProvenance,
    FinancialNewsOutput,
    FundamentalRatios,
    NewsArticle,
    PositionItem,
    TechnicalIndicators,
    TechnicalSummaryOutput,
    ToolErrorObservation,
)
from src.contracts.trade_schemas import (
    OrderExecutionReceipt,
    RiskCheckResult,
    TradeProposalDraft,
    ValidatedTradeProposal,
)

__all__ = [
    "DataProvenance",
    "TechnicalIndicators",
    "TechnicalSummaryOutput",
    "FundamentalRatios",
    "NewsArticle",
    "FinancialNewsOutput",
    "AccountSummary",
    "PositionItem",
    "ToolErrorObservation",
    "TradeProposalDraft",
    "RiskCheckResult",
    "ValidatedTradeProposal",
    "OrderExecutionReceipt",
]
