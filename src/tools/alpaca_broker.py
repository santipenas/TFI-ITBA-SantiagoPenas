"""Herramienta de consulta de estado de cuenta y posiciones en Alpaca Paper Trading."""

from datetime import UTC, datetime

from alpaca.trading.client import TradingClient

from src.config import settings
from src.contracts.models import (
    AccountSummary,
    DataProvenance,
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


def get_account_and_positions() -> AccountSummary | ToolErrorObservation:
    """Consulta el saldo, liquidez y posiciones abiertas en Alpaca Paper Trading."""
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
