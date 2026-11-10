"""Herramienta de consulta de estado de cuenta, posiciones y órdenes en Alpaca Paper Trading."""

from datetime import UTC, datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from src.config import settings
from src.contracts.models import (
    AccountSummary,
    DataProvenance,
    OrderItem,
    PositionItem,
    ToolErrorObservation,
)
from src.utils.logger import get_logger

logger = get_logger("tools.alpaca_broker")


def get_alpaca_trading_client() -> TradingClient | None:
    """Instancia y retorna el cliente de Trading de Alpaca en modo Paper Trading."""
    if not settings.alpaca_api_key or not settings.alpaca_secret_key:
        logger.warning("Credenciales de Alpaca Paper Trading no configuradas.")
        return None
    return TradingClient(
        api_key=settings.alpaca_api_key,
        secret_key=settings.alpaca_secret_key,
        paper=True,
    )


def _parse_alpaca_order(o) -> OrderItem:
    """Convierte un objeto Order de Alpaca a nuestro contrato OrderItem."""
    side_str = "buy" if (hasattr(o.side, "value") and o.side.value.lower() == "buy") or "buy" in str(o.side).lower() else "sell"
    status_str = o.status.value if hasattr(o.status, "value") else str(o.status)
    order_type_str = o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type)

    sl_price = None
    tp_price = None
    if getattr(o, "legs", None):
        for leg in o.legs:
            leg_type = leg.order_type.value if hasattr(leg.order_type, "value") else str(leg.order_type)
            if "stop" in leg_type.lower() and getattr(leg, "stop_price", None) is not None:
                sl_price = float(leg.stop_price)
            elif "limit" in leg_type.lower() and getattr(leg, "limit_price", None) is not None:
                tp_price = float(leg.limit_price)

    return OrderItem(
        id=str(o.id),
        client_order_id=getattr(o, "client_order_id", None),
        symbol=str(o.symbol),
        qty=float(o.qty),
        side=side_str,
        order_type=order_type_str,
        status=status_str,
        submitted_at=o.submitted_at.isoformat() if getattr(o, "submitted_at", None) else None,
        filled_at=o.filled_at.isoformat() if getattr(o, "filled_at", None) else None,
        filled_avg_price=float(o.filled_avg_price) if getattr(o, "filled_avg_price", None) is not None else None,
        limit_price=float(o.limit_price) if getattr(o, "limit_price", None) is not None else None,
        stop_loss_price=sl_price,
        take_profit_price=tp_price,
    )


def get_account_and_positions() -> AccountSummary | ToolErrorObservation:
    """Consulta el saldo, liquidez, posiciones abiertas y órdenes en Alpaca Paper Trading."""
    client = get_alpaca_trading_client()
    if not client:
        return ToolErrorObservation(
            code="ALPACA_CREDENTIALS_MISSING",
            message="No se configuraron las claves ALPACA_API_KEY y ALPACA_SECRET_KEY.",
            retryable=False,
        )

    try:
        acc = client.get_account()
        positions = client.get_all_positions()

        open_positions: list[PositionItem] = []
        for pos in positions:
            open_positions.append(
                PositionItem(
                    symbol=pos.symbol,
                    qty=float(pos.qty),
                    side="long" if pos.side.value == "long" else "short",
                    avg_entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price) if pos.current_price else float(pos.avg_entry_price),
                    unrealized_pl=float(pos.unrealized_pl) if pos.unrealized_pl else 0.0,
                    unrealized_plpc=float(pos.unrealized_plpc) if pos.unrealized_plpc else 0.0,
                )
            )

        # Consulta de Órdenes Pendientes (Open / Accepted)
        open_orders: list[OrderItem] = []
        try:
            raw_open = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=20, nested=True))
            if isinstance(raw_open, list):
                open_orders = [_parse_alpaca_order(o) for o in raw_open]
        except Exception as err:
            logger.warning("No se pudieron recuperar las órdenes abiertas de Alpaca: %s", err)

        # Consulta de Historial de Órdenes Recientes (All)
        recent_orders: list[OrderItem] = []
        try:
            raw_recent = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.ALL, limit=20, nested=True))
            if isinstance(raw_recent, list):
                recent_orders = [_parse_alpaca_order(o) for o in raw_recent]
        except Exception as err:
            logger.warning("No se pudo recuperar el historial de órdenes de Alpaca: %s", err)

        provenance = DataProvenance(
            source_name="Alpaca Paper Trading API",
            data_quality="LIVE",
            timestamp_utc=datetime.now(UTC).isoformat(),
        )

        return AccountSummary(
            equity=float(acc.equity),
            cash=float(acc.cash),
            buying_power=float(acc.buying_power),
            portfolio_value=float(acc.portfolio_value),
            open_positions=open_positions,
            open_orders=open_orders,
            recent_orders=recent_orders,
            is_trading_blocked=bool(acc.trading_blocked),
            provenance=provenance,
        )

    except Exception as exc:
        logger.error("Error al consultar cuenta en Alpaca Paper: %s", exc)
        return ToolErrorObservation(
            code="ALPACA_ACCOUNT_FETCH_ERROR",
            message=f"Error al conectar con Alpaca Paper: {str(exc)}",
            retryable=True,
        )
