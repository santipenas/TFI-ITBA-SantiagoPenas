"""Tests unitarios para el motor determinista de riesgo (RiskPolicyService)."""

from datetime import datetime, timezone
from src.contracts.models import AccountSummary, DataProvenance
from src.contracts.trade_schemas import TradeProposalDraft
from src.services.risk_policy_service import RiskPolicyService


def _create_mock_account(equity: float = 100000.0, cash: float = 80000.0, blocked: bool = False) -> AccountSummary:
    return AccountSummary(
        equity=equity,
        cash=cash,
        buying_power=equity * 2,
        portfolio_value=equity,
        open_positions=[],
        is_trading_blocked=blocked,
        provenance=DataProvenance(
            source_name="Mock Account",
            data_quality="LIVE",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        ),
    )


def test_risk_policy_approves_valid_trade():
    """Una orden con SL adecuado y buen ratio R/B debe ser aprobada y dimensionada."""
    service = RiskPolicyService()
    account = _create_mock_account(equity=50000.0, cash=40000.0)
    
    # 2% de 50,000 = 1,000 USD riesgo máximo
    # Entrada = 100, SL = 95 -> Distancia = 5 USD
    # Cantidad calculada = 1000 / 5 = 200 acciones
    # Valor posición = 200 * 100 = 20,000 USD (40% de 50k -> excede el 10% max)
    # Exposición máxima 10% de 50,000 = 5,000 USD -> Ajusta a 50 acciones (5,000 USD)
    draft = TradeProposalDraft(
        ticker="AAPL",
        side="BUY",
        suggested_entry_price=100.0,
        suggested_stop_loss=95.0,
        suggested_take_profit=115.0,  # TP distancia = 15 -> R/B = 3.0
        thesis_summary="Setup sólido.",
    )

    result = service.evaluate_proposal(draft, account, risk_profile="MODERATE")
    assert result.is_approved is True
    assert result.adjusted_qty == 50  # Limitado por el 10% de concentración
    assert result.position_value_usd == 5000.0
    assert result.position_percentage_equity == 10.0


def test_risk_policy_rejects_sl_too_close():
    """Debe rechazar la orden si la distancia al Stop-Loss es menor al 0.5%."""
    service = RiskPolicyService(min_sl_distance_pct=0.005)
    account = _create_mock_account()

    # Entrada = 100.0, SL = 99.8 -> Distancia = 0.2% (< 0.5%)
    draft = TradeProposalDraft(
        ticker="MSFT",
        side="BUY",
        suggested_entry_price=100.0,
        suggested_stop_loss=99.8,
        suggested_take_profit=110.0,
        thesis_summary="Stop demasiado ajustado.",
    )

    result = service.evaluate_proposal(draft, account)
    assert result.is_approved is False
    assert any("menor al mínimo de seguridad" in r for r in result.rejection_reasons)


def test_risk_policy_rejects_low_risk_reward_ratio():
    """Debe rechazar la orden si el ratio R/B es inferior a 1.5:1."""
    service = RiskPolicyService(min_risk_reward_ratio=1.5)
    account = _create_mock_account()

    # Entrada = 100.0, SL = 90.0 (distancia = 10), TP = 105.0 (distancia = 5) -> R/B = 0.5
    draft = TradeProposalDraft(
        ticker="NVDA",
        side="BUY",
        suggested_entry_price=100.0,
        suggested_stop_loss=90.0,
        suggested_take_profit=105.0,
        thesis_summary="Ratio pobre.",
    )

    result = service.evaluate_proposal(draft, account)
    assert result.is_approved is False
    assert any("Riesgo/Beneficio" in r for r in result.rejection_reasons)


def test_risk_policy_rejects_blocked_account():
    """Debe rechazar cualquier orden si la cuenta del broker está bloqueada."""
    service = RiskPolicyService()
    account = _create_mock_account(blocked=True)

    draft = TradeProposalDraft(
        ticker="SPY",
        side="BUY",
        suggested_entry_price=500.0,
        suggested_stop_loss=490.0,
        suggested_take_profit=520.0,
        thesis_summary="Cuenta bloqueada.",
    )

    result = service.evaluate_proposal(draft, account)
    assert result.is_approved is False
    assert any("bloqueada" in r for r in result.rejection_reasons)
