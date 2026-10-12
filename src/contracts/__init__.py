"""Contratos de datos, modelos tipados y esquemas de validación del sistema."""

from src.contracts.models import (
    DataProvenance,
    TechnicalIndicators,
    TechnicalSummaryOutput,
    FundamentalRatios,
    NewsArticle,
    FinancialNewsOutput,
    AccountSummary,
    PositionItem,
    ToolErrorObservation,
)
from src.contracts.trade_schemas import (
    TradeProposalDraft,
    RiskCheckResult,
    ValidatedTradeProposal,
    OrderExecutionReceipt,
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
