"""Tests unitarios para los contratos y esquemas Pydantic v2."""

import pytest
from pydantic import ValidationError
from src.contracts.trade_schemas import TradeProposalDraft, RiskCheckResult, ValidatedTradeProposal


def test_valid_long_trade_proposal_draft():
    """Verifica que un borrador de compra con SL menor al precio y TP mayor sea válido."""
    draft = TradeProposalDraft(
        ticker="NVDA",
        side="BUY",
        order_type="market",
        suggested_entry_price=120.0,
        suggested_stop_loss=115.0,
        suggested_take_profit=130.0,
        thesis_summary="Tendencia alcista confirmada y RSI rebotando en 50.",
    )
    assert draft.ticker == "NVDA"
    assert draft.side == "BUY"
    assert draft.suggested_stop_loss < draft.suggested_entry_price < draft.suggested_take_profit


def test_invalid_long_trade_proposal_sl_too_high():
    """Debe fallar si en una compra el Stop-Loss es superior o igual a la entrada."""
    with pytest.raises(ValidationError):
        TradeProposalDraft(
            ticker="NVDA",
            side="BUY",
            suggested_entry_price=120.0,
            suggested_stop_loss=125.0,  # Inválido para Long
            suggested_take_profit=130.0,
            thesis_summary="Error intencional en SL.",
        )


def test_valid_short_trade_proposal_draft():
    """Verifica que un borrador de venta corta con SL superior al precio y TP inferior sea válido."""
    draft = TradeProposalDraft(
        ticker="TSLA",
        side="SELL",
        order_type="market",
        suggested_entry_price=200.0,
        suggested_stop_loss=210.0,
        suggested_take_profit=180.0,
        thesis_summary="Ruptura de soporte relevante y cruce bajista de SMA 20 y 50.",
    )
    assert draft.side == "SELL"
    assert draft.suggested_take_profit < draft.suggested_entry_price < draft.suggested_stop_loss


def test_validated_trade_proposal_wrapper():
    """Verifica el contenedor de propuesta validada para la etapa de HITL."""
    draft = TradeProposalDraft(
        ticker="AAPL",
        side="BUY",
        suggested_entry_price=220.0,
        suggested_stop_loss=215.0,
        suggested_take_profit=230.0,
        thesis_summary="Setup alcista.",
    )
    risk_res = RiskCheckResult(
        is_approved=True,
        adjusted_qty=10,
        max_risk_amount_usd=50.0,
        risk_percentage_equity=0.5,
        position_value_usd=2200.0,
        position_percentage_equity=8.8,
    )
    proposal = ValidatedTradeProposal(
        proposal_id="prop-001",
        draft=draft,
        risk_evaluation=risk_res,
        status="PENDING_APPROVAL",
    )
    assert proposal.status == "PENDING_APPROVAL"
    assert proposal.risk_evaluation.adjusted_qty == 10
