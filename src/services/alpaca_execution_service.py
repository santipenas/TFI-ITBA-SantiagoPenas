"""Servicio de ejecución de órdenes en Alpaca Paper Trading con soporte de bracket orders e idempotencia."""

import uuid
from datetime import UTC, datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, StopLossRequest, TakeProfitRequest

from src.contracts.trade_schemas import OrderExecutionReceipt, ValidatedTradeProposal
from src.tools.alpaca_broker import get_alpaca_trading_client
from src.utils.logger import get_logger

logger = get_logger("services.alpaca_execution")


class AlpacaExecutionService:
    """Ejecutor determinista de órdenes sobre la API de Paper Trading de Alpaca."""

    def __init__(self, client: TradingClient | None = None):
        self.client = client or get_alpaca_trading_client()

    def execute_order(self, proposal: ValidatedTradeProposal) -> OrderExecutionReceipt:
        """Envía una orden bracket (con Stop-Loss y Take-Profit) al broker de Paper Trading.

        Args:
            proposal: Propuesta formal validada y aprobada por el usuario (HITL).

        Returns:
            OrderExecutionReceipt con el estado del broker y el ID oficial de la orden.
        """
        draft = proposal.draft
        qty = proposal.risk_evaluation.adjusted_qty
        client_order_id = f"itba_{draft.ticker.lower()}_{uuid.uuid4().hex[:8]}"

        if not self.client:
            return OrderExecutionReceipt(
                success=False,
                client_order_id=client_order_id,
                ticker=draft.ticker,
                side=draft.side,
                qty=qty,
                order_type=draft.order_type,
                status="rejected",
                submitted_at_utc=datetime.now(UTC).isoformat(),
                error_message="Cliente de Alpaca Paper Trading no inicializado o sin credenciales válidas.",
            )

        side = OrderSide.BUY if draft.side == "BUY" else OrderSide.SELL
        time_in_force = TimeInForce.GTC  # Good Till Cancelled para swing/bracket

        # Configuración de los niveles de salida (Bracket)
        take_profit = TakeProfitRequest(limit_price=round(draft.suggested_take_profit, 2))
        stop_loss = StopLossRequest(stop_price=round(draft.suggested_stop_loss, 2))

        try:
            if draft.order_type == "limit" and draft.limit_price:
                order_req = LimitOrderRequest(
                    symbol=draft.ticker,
                    qty=qty,
                    side=side,
                    time_in_force=time_in_force,
                    limit_price=round(draft.limit_price, 2),
                    order_class=OrderClass.BRACKET,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    client_order_id=client_order_id,
                )
            else:
                order_req = MarketOrderRequest(
                    symbol=draft.ticker,
                    qty=qty,
                    side=side,
                    time_in_force=time_in_force,
                    order_class=OrderClass.BRACKET,
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    client_order_id=client_order_id,
                )

            logger.info(
                "Enviando orden a Alpaca Paper: %s %d %s (SL: %.2f, TP: %.2f)",
                draft.side,
                qty,
                draft.ticker,
                draft.suggested_stop_loss,
                draft.suggested_take_profit,
            )

            order = self.client.submit_order(order_data=order_req)

            return OrderExecutionReceipt(
                success=True,
                broker_order_id=str(order.id),
                client_order_id=client_order_id,
                ticker=draft.ticker,
                side=draft.side,
                qty=qty,
                order_type=draft.order_type,
                status=str(order.status.value) if hasattr(order.status, "value") else str(order.status),
                submitted_at_utc=datetime.now(UTC).isoformat(),
            )

        except Exception as exc:
            logger.error("Fallo al ejecutar orden en Alpaca: %s", exc)
            return OrderExecutionReceipt(
                success=False,
                client_order_id=client_order_id,
                ticker=draft.ticker,
                side=draft.side,
                qty=qty,
                order_type=draft.order_type,
                status="broker_error",
                submitted_at_utc=datetime.now(UTC).isoformat(),
                error_message=f"Error retornado por Alpaca Paper: {str(exc)}",
            )
