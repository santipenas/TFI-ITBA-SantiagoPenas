"""Agente de Control de Riesgo, Gobernanza y Compuerta Human-in-the-Loop (HITL)."""

import uuid

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from src.contracts.models import AccountSummary, ToolErrorObservation
from src.contracts.trade_schemas import ValidatedTradeProposal
from src.graph.state import AgentState
from src.services.alpaca_execution_service import AlpacaExecutionService
from src.services.risk_policy_service import RiskPolicyService
from src.tools.alpaca_broker import get_account_and_positions
from src.utils.logger import get_logger

logger = get_logger("agents.risk_gatekeeper")


def risk_gatekeeper_node(state: AgentState) -> dict:
    """Nodo de gobernanza: valida reglas duras de riesgo, informa sobre la cartera y activa HITL."""
    draft = state.trade_proposal

    # Caso A: Consulta informativa sobre el saldo o cartera (sin propuesta activa)
    if not draft:
        logger.info("Consulta informativa de cartera en RiskGate (sin propuesta de trade activa).")
        account_obs = get_account_and_positions()
        if isinstance(account_obs, ToolErrorObservation):
            msg = f"⚠️ No se pudo conectar con Alpaca Paper Trading: {account_obs.message}"
        else:
            acc: AccountSummary = account_obs
            pos_text = "_Sin posiciones abiertas actualmente._"
            if acc.open_positions:
                pos_lines = [
                    f"- **{p.symbol}**: {p.qty} acciones ({p.side.upper()}) a ${p.current_price:.2f} (P/L no realizado: ${p.unrealized_pl:,.2f})"
                    for p in acc.open_positions
                ]
                pos_text = "\n".join(pos_lines)

            # Formateo de Órdenes Pendientes
            orders_text = "_Sin órdenes pendientes actualmente._"
            if acc.open_orders:
                ord_lines = []
                for o in acc.open_orders:
                    sl_str = f" | SL: ${o.stop_loss_price:.2f}" if o.stop_loss_price else ""
                    tp_str = f" | TP: ${o.take_profit_price:.2f}" if o.take_profit_price else ""
                    status_badge = "⏳ EN ESPERA (ACCEPTED)" if o.status.lower() in ["accepted", "new", "held"] else f"`{o.status.upper()}`"
                    ord_lines.append(
                        f"- **{o.symbol}**: {o.qty} acciones **{o.side.upper()}** ({o.order_type.upper()}) – {status_badge}{sl_str}{tp_str}"
                    )
                orders_text = "\n".join(ord_lines)

            # Formateo de Historial Reciente (últimas 5 órdenes)
            hist_text = "_Sin historial reciente de operaciones._"
            if acc.recent_orders:
                hist_lines = []
                for o in acc.recent_orders[:5]:
                    date_str = o.submitted_at[:16].replace("T", " ") if o.submitted_at else "Reciente"
                    price_str = f" a ${o.filled_avg_price:.2f}" if o.filled_avg_price else ""
                    hist_lines.append(
                        f"- `{date_str}`: **{o.side.upper()} {o.qty} {o.symbol}**{price_str} – Estado: `{o.status.upper()}`"
                    )
                hist_text = "\n".join(hist_lines)

            msg = (
                f"💼 **Estado Actual de tu Cartera (Alpaca Paper Trading)**:\n\n"
                f"- **Capital Total (Equity)**: `${acc.equity:,.2f} USD`\n"
                f"- **Efectivo Disponible (Cash)**: `${acc.cash:,.2f} USD`\n"
                f"- **Poder de Compra**: `${acc.buying_power:,.2f} USD`\n\n"
                f"📌 **Posiciones Abiertas**:\n{pos_text}\n\n"
                f"⏳ **Órdenes Pendientes / Activas**:\n{orders_text}\n\n"
                f"📜 **Historial de Operaciones Recientes**:\n{hist_text}"
            )
        return {
            "messages": [AIMessage(content=msg)],
            "next_step": "respond",
        }

    # Caso B: Auditoría de riesgo previa a ejecución de orden
    logger.info("Iniciando auditoría de riesgo para propuesta: %s %s", draft.side, draft.ticker)

    account_obs = get_account_and_positions()
    if isinstance(account_obs, ToolErrorObservation):
        msg = f"⚠️ **Operación Detenida por Riesgo**: No se pudo verificar el saldo de la cuenta con Alpaca Paper ({account_obs.message}). Ninguna orden puede autorizarse sin verificación de capital."
        return {
            "messages": [AIMessage(content=msg)],
            "trade_proposal": None,
            "next_step": "respond",
        }

    account: AccountSummary = account_obs
    risk_profile = state.user_profile.get("risk_profile", "MODERATE")

    # Evaluación con el Motor Determinista de Riesgo (RiskPolicyService)
    risk_service = RiskPolicyService()
    risk_result = risk_service.evaluate_proposal(draft, account, risk_profile=risk_profile)

    if not risk_result.is_approved:
        logger.warning("Propuesta rechazada por políticas de riesgo: %s", risk_result.rejection_reasons)
        rejection_bullets = "\n".join([f"- {r}" for r in risk_result.rejection_reasons])
        msg = (
            f"❌ **Propuesta Rechazada por el Gestor de Riesgo**:\n"
            f"El trade sugerido para **{draft.ticker}** incumple las normas de control de capital:\n"
            f"{rejection_bullets}\n\n"
            f"*La orden ha sido cancelada sin llegar al broker.*"
        )
        return {
            "messages": [AIMessage(content=msg)],
            "trade_proposal": None,
            "next_step": "respond",
        }

    # Construcción de Propuesta Validada
    proposal = ValidatedTradeProposal(
        proposal_id=f"prop_{draft.ticker.lower()}_{uuid.uuid4().hex[:6]}",
        draft=draft,
        risk_evaluation=risk_result,
        status="PENDING_APPROVAL",
    )

    logger.info("Propuesta aprobada por reglas de riesgo. Activando pausa HITL (interrupt)...")

    # COMPUERTA HUMAN-IN-THE-LOOP (HITL) - Pausa del Grafo
    human_response = interrupt(
        {
            "type": "ORDER_CONFIRMATION_REQUIRED",
            "proposal_id": proposal.proposal_id,
            "ticker": draft.ticker,
            "side": draft.side,
            "qty": risk_result.adjusted_qty,
            "entry_price": draft.suggested_entry_price,
            "stop_loss": draft.suggested_stop_loss,
            "take_profit": draft.suggested_take_profit,
            "risk_usd": risk_result.max_risk_amount_usd,
            "risk_pct": risk_result.risk_percentage_equity,
            "position_value_usd": risk_result.position_value_usd,
            "account_equity": account.equity,
            "environment": "Alpaca Paper Trading (Sandbox)",
        }
    )

    action = human_response.get("action", "REJECT").upper() if isinstance(human_response, dict) else "REJECT"
    logger.info("Respuesta humana recibida tras interrupción HITL: %s", action)

    if action == "APPROVE":
        proposal.status = "APPROVED"
        exec_service = AlpacaExecutionService()
        receipt = exec_service.execute_order(proposal)

        if receipt.success:
            msg = (
                f"✅ **Orden Ejecutada Exitosamente en Alpaca Paper Trading**:\n\n"
                f"- **Activo**: {receipt.ticker}\n"
                f"- **Operación**: {receipt.side} ({receipt.order_type.upper()})\n"
                f"- **Cantidad**: {receipt.qty} acciones\n"
                f"- **ID de Broker (Alpaca)**: `{receipt.broker_order_id}`\n"
                f"- **ID de Cliente**: `{receipt.client_order_id}`\n"
                f"- **Estado**: `{receipt.status.upper()}`\n"
                f"- **Hora UTC**: {receipt.submitted_at_utc}\n\n"
                f"*Niveles activos en broker: Stop-Loss en ${draft.suggested_stop_loss:.2f} | Take-Profit en ${draft.suggested_take_profit:.2f}*"
            )
        else:
            msg = (
                f"⚠️ **Error al Enviar Orden al Broker**:\n"
                f"{receipt.error_message}\n"
                f"*(Verifique si el mercado está abierto o si las credenciales de Alpaca tienen permisos de trading)*"
            )

        return {
            "messages": [AIMessage(content=msg)],
            "validated_proposal": proposal,
            "order_receipt": receipt,
            "trade_proposal": None,
            "next_step": "respond",
        }

    else:
        proposal.status = "REJECTED"
        proposal.human_verdict_reason = (
            human_response.get("reason", "Cancelado por el usuario en interfaz")
            if isinstance(human_response, dict)
            else "Cancelado por el usuario"
        )
        msg = f"🛑 **Orden Cancelada por el Usuario**: La operación para {draft.ticker} fue desestimada manualmente. No se envió ninguna orden a Alpaca."
        return {
            "messages": [AIMessage(content=msg)],
            "validated_proposal": proposal,
            "trade_proposal": None,
            "next_step": "respond",
        }
