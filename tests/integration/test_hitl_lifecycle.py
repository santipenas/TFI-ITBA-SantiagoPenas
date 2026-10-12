"""Tests de integración para el ciclo de vida Human-in-the-Loop (HITL) en LangGraph."""

from unittest.mock import patch
from langgraph.checkpoint.memory import MemorySaver

from src.contracts.models import AccountSummary, DataProvenance
from src.contracts.trade_schemas import OrderExecutionReceipt, TradeProposalDraft
from src.graph.workflow import create_financial_graph


def _mock_account() -> AccountSummary:
    from datetime import datetime, timezone
    return AccountSummary(
        equity=50000.0,
        cash=40000.0,
        buying_power=100000.0,
        portfolio_value=50000.0,
        open_positions=[],
        is_trading_blocked=False,
        provenance=DataProvenance(
            source_name="Mock Alpaca",
            data_quality="LIVE",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        ),
    )


def test_hitl_pause_and_approve_lifecycle():
    """Verifica que el grafo pause en la compuerta HITL y ejecute la orden tras la aprobación humana."""
    checkpointer = MemorySaver()

    draft = TradeProposalDraft(
        ticker="AAPL",
        side="BUY",
        suggested_entry_price=100.0,
        suggested_stop_loss=95.0,
        suggested_take_profit=115.0,  # R/B = 3.0 (supera el 1.5 requerido)
        thesis_summary="Setup técnico favorable.",
    )

    initial_state = {
        "messages": [],
        "current_ticker": "AAPL",
        "trade_proposal": draft,
        "next_step": "supervisor",
    }

    config = {"configurable": {"thread_id": "test_thread_approve"}}

    # Parcheamos las referencias en workflow para aislar completamente el flujo de estados
    with patch("src.graph.workflow.supervisor_node", return_value={"next_step": "analyst", "current_ticker": "AAPL"}), \
         patch("src.graph.workflow.market_analyst_node", return_value={"trade_proposal": draft, "next_step": "risk_gate"}), \
         patch("src.agents.risk_gatekeeper.get_account_and_positions", return_value=_mock_account()), \
         patch("src.services.alpaca_execution_service.AlpacaExecutionService.execute_order") as mock_exec:

        graph = create_financial_graph(checkpointer=checkpointer)

        mock_exec.return_value = OrderExecutionReceipt(
            success=True,
            broker_order_id="mock_broker_order_123",
            client_order_id="itba_aapl_123",
            ticker="AAPL",
            side="BUY",
            qty=50,
            order_type="market",
            status="accepted",
            submitted_at_utc="2026-10-12T12:00:00Z",
        )

        # 1. Iniciar ejecución: Debe avanzar hasta risk_gate y PAUSAR en interrupt()
        res = graph.invoke(initial_state, config=config)

        # Verificar que el grafo está en pausa con la interrupción activa
        state_snapshot = graph.get_state(config)
        assert len(state_snapshot.tasks) > 0
        interrupt_value = state_snapshot.tasks[0].interrupts[0].value
        assert interrupt_value["type"] == "ORDER_CONFIRMATION_REQUIRED"
        assert interrupt_value["ticker"] == "AAPL"

        # 2. Reanudar con aprobación del usuario
        from langgraph.types import Command
        res_approved = graph.invoke(
            Command(resume={"action": "APPROVE"}),
            config=config,
        )

        # 3. Comprobar que la orden fue ejecutada y la respuesta final contiene el ID
        assert mock_exec.called
        assert res_approved["validated_proposal"].status == "APPROVED"
        assert res_approved["order_receipt"].broker_order_id == "mock_broker_order_123"


def test_hitl_pause_and_reject_lifecycle():
    """Verifica que el grafo pause en HITL y cancele la orden sin llamar al broker si el usuario rechaza."""
    checkpointer = MemorySaver()

    draft = TradeProposalDraft(
        ticker="NVDA",
        side="BUY",
        suggested_entry_price=100.0,
        suggested_stop_loss=95.0,
        suggested_take_profit=115.0,
        thesis_summary="Setup alcista.",
    )

    initial_state = {
        "messages": [],
        "current_ticker": "NVDA",
        "trade_proposal": draft,
        "next_step": "supervisor",
    }

    config = {"configurable": {"thread_id": "test_thread_reject"}}

    with patch("src.graph.workflow.supervisor_node", return_value={"next_step": "analyst", "current_ticker": "NVDA"}), \
         patch("src.graph.workflow.market_analyst_node", return_value={"trade_proposal": draft, "next_step": "risk_gate"}), \
         patch("src.agents.risk_gatekeeper.get_account_and_positions", return_value=_mock_account()), \
         patch("src.services.alpaca_execution_service.AlpacaExecutionService.execute_order") as mock_exec:

        graph = create_financial_graph(checkpointer=checkpointer)

        # 1. Iniciar ejecución hasta la pausa
        graph.invoke(initial_state, config=config)

        # Verificar que efectivamente está pausado en interrupt()
        state_snapshot = graph.get_state(config)
        assert len(state_snapshot.tasks) > 0
        assert state_snapshot.tasks[0].interrupts[0].value["ticker"] == "NVDA"

        # 2. Reanudar con rechazo del usuario
        from langgraph.types import Command
        res_rejected = graph.invoke(
            Command(resume={"action": "REJECT", "reason": "No me convence la volatilidad del activo"}),
            config=config,
        )

        # 3. Comprobar que NO se llamó al ejecutor de Alpaca y el estado quedó en REJECTED
        assert not mock_exec.called
        assert res_rejected["validated_proposal"].status == "REJECTED"
        assert "Cancelada por el Usuario" in res_rejected["messages"][-1].content
