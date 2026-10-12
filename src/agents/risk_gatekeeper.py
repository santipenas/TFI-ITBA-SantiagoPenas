"""Agente de Control de Riesgo, Gobernanza y Compuerta Human-in-the-Loop (HITL)."""

from datetime import datetime, timezone
import uuid
from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from src.contracts.models import AccountSummary, DataProvenance, ToolErrorObservation
from src.contracts.trade_schemas import ValidatedTradeProposal
from src.graph.state import AgentState
from src.services.alpaca_execution_service import AlpacaExecutionService
from src.services.risk_policy_service import RiskPolicyService
from src.tools.alpaca_broker import get_account_and_positions
from src.utils.logger import get_logger

logger = get_logger("agents.risk_gatekeeper")


def risk_gatekeeper_node(state: AgentState) -> dict:
    """Nodo de gobernanza: valida reglas duras de riesgo y activa la pausa HITL antes de ejecutar."""
    draft = state.trade_proposal
    if not draft:
        logger.info("No hay propuesta de trade pendiente para evaluar en RiskGate.")
        return {"next_step": "respond"}

    logger.info("Iniciando auditoría de riesgo para propuesta: %s %s", draft.side, draft.ticker)

    # 1. Obtener estado de cuenta real desde Alpaca Paper
    account_obs = get_account_and_positions()
    if isinstance(account_obs, ToolErrorObservation):
        # Fallback de seguridad: Si no hay conexión al broker, no se puede autorizar la orden
        msg = f"⚠️ **Operación Detenida por Riesgo**: No se pudo verificar el saldo de la cuenta con Alpaca Paper ({account_obs.message}). Ninguna orden puede autorizarse sin verificación de capital."
        return {
            "messages": [AIMessage(content=msg)],
            "trade_proposal": None,
            "next_step": "respond",
        }

    account: AccountSummary = account_obs
    risk_profile = state.user_profile.get("risk_profile", "MODERATE")

    # 2. Evaluación con el Motor Determinista de Riesgo (RiskPolicyService)
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

    # 3. Construcción de Propuesta Validada
    proposal = ValidatedTradeProposal(
        proposal_id=f"prop_{draft.ticker.lower()}_{uuid.uuid4().hex[:6]}",
        draft=draft,
        risk_evaluation=risk_result,
        status="PENDING_APPROVAL",
    )

    logger.info("Propuesta aprobada por reglas de riesgo. Activando pausa HITL (interrupt)...")

    # 4. COMPUERTA HUMAN-IN-THE-LOOP (HITL) - Pausa del Grafo
    # interrupt() pausa la ejecución de LangGraph y expone el payload a la UI
    human_response = interrupt({
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
    })

    # Al reanudarse el hilo, procesamos la decisión humana:
    action = human_response.get("action", "REJECT").upper() if isinstance(human_response, dict) else "REJECT"
    logger.info("Respuesta humana recibida tras interrupción HITL: %s", action)

    if action == "APPROVE":
        proposal.status = "APPROVED"
        # 5. Ejecución en Alpaca Paper Trading
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
        # El usuario canceló o rechazó la operación
        proposal.status = "REJECTED"
        proposal.human_verdict_reason = human_response.get("reason", "Cancelado por el usuario en interfaz") if isinstance(human_response, dict) else "Cancelado por el usuario"
        msg = f"🛑 **Orden Cancelada por el Usuario**: La operación para {draft.ticker} fue desestimada manualmente. No se envió ninguna orden a Alpaca."
        return {
            "messages": [AIMessage(content=msg)],
            "validated_proposal": proposal,
            "trade_proposal": None,
            "next_step": "respond",
        }
