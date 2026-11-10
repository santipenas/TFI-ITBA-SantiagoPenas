"""Tests unitarios para las herramientas financieras y brokers con mocks."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.contracts.models import (
    AccountSummary,
    FinancialNewsOutput,
    FundamentalRatios,
    TechnicalSummaryOutput,
    ToolErrorObservation,
)
from src.tools.alpaca_broker import get_account_and_positions
from src.tools.fundamentals import get_company_fundamentals
from src.tools.market_data import get_stock_technical_summary
from src.tools.news import get_financial_news


def test_get_stock_technical_summary_insufficient_data():
    """Debe retornar ToolErrorObservation si yfinance no descarga suficientes velas."""
    with patch("yfinance.download", return_value=pd.DataFrame()):
        res = get_stock_technical_summary("INVALIDTICKER")
        assert isinstance(res, ToolErrorObservation)
        assert res.code == "INSUFFICIENT_DATA"


def test_get_stock_technical_summary_success():
    """Verifica el cálculo de SMA y RSI con un DataFrame mock."""
    # Generar 60 días de velas sintéticas crecientes (tendencia alcista)
    dates = pd.date_range("2026-01-01", periods=60)
    prices = [100.0 + i for i in range(60)]
    mock_df = pd.DataFrame(
        {
            "Open": prices,
            "High": [p + 2.0 for p in prices],
            "Low": [p - 2.0 for p in prices],
            "Close": prices,
            "Volume": [1000000] * 60,
        },
        index=dates,
    )

    with patch("yfinance.download", return_value=mock_df):
        res = get_stock_technical_summary("AAPL")
        assert isinstance(res, TechnicalSummaryOutput)
        assert res.ticker == "AAPL"
        assert res.indicators.current_price == 159.0
        assert res.indicators.trend_bias == "BULLISH"
        assert res.indicators.sma_20 is not None


def test_get_company_fundamentals_fmp_success():
    """Verifica la respuesta de fundamentales con FMP mockeado."""
    mock_ratios = [{"priceEarningsRatioTTM": 28.5, "debtEquityRatioTTM": 0.8, "netProfitMarginTTM": 0.25}]
    mock_metrics = [{"marketCap": 2500000000000, "peRatioTTM": 28.5}]

    with patch("requests.get") as mock_get, patch("src.config.settings.fmp_api_key", "mock_key"):
        # Primer llamado: ratios, Segundo llamado: key-metrics
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = mock_ratios

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = mock_metrics

        mock_get.side_effect = [mock_resp1, mock_resp2]

        res = get_company_fundamentals("AAPL")
        assert isinstance(res, FundamentalRatios)
        assert res.ticker == "AAPL"
        assert res.pe_ratio == 28.5
        assert res.debt_to_equity == 0.8


def test_get_financial_news_missing_key():
    """Debe retornar ToolErrorObservation si falta la clave de Tavily."""
    with patch("src.config.settings.tavily_api_key", None):
        res = get_financial_news("NVDA")
        assert isinstance(res, ToolErrorObservation)
        assert res.code == "TAVILY_KEY_MISSING"


def test_get_financial_news_success():
    """Verifica el parseo de artículos de noticias con Tavily mockeado."""
    mock_tavily_resp = {
        "results": [
            {
                "title": "Nvidia Reports Record Earnings",
                "url": "https://example.com/nvda",
                "published_date": "2026-10-10",
                "content": "Nvidia exceeded expectations driven by strong AI demand across data centers.",
            }
        ]
    }

    with (
        patch("src.config.settings.tavily_api_key", "mock_tavily_key"),
        patch("src.tools.news.TavilyClient") as mock_client_cls,
    ):
        mock_instance = MagicMock()
        mock_instance.search.return_value = mock_tavily_resp
        mock_client_cls.return_value = mock_instance

        res = get_financial_news("NVDA")
        assert isinstance(res, FinancialNewsOutput)
        assert len(res.articles) == 1
        assert res.articles[0].title == "Nvidia Reports Record Earnings"


def test_get_account_and_positions_mocked():
    """Verifica la consulta de cuenta en Alpaca Paper con cliente mock."""
    mock_acc = MagicMock()
    mock_acc.equity = "100000.00"
    mock_acc.cash = "85000.00"
    mock_acc.buying_power = "170000.00"
    mock_acc.portfolio_value = "100000.00"
    mock_acc.trading_blocked = False

    mock_pos = MagicMock()
    mock_pos.symbol = "AAPL"
    mock_pos.qty = "10"
    mock_pos.side.value = "long"
    mock_pos.avg_entry_price = "220.00"
    mock_pos.current_price = "225.00"
    mock_pos.unrealized_pl = "50.00"
    mock_pos.unrealized_plpc = "0.0227"

    with patch("src.tools.alpaca_broker.get_alpaca_trading_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get_account.return_value = mock_acc
        mock_client.get_all_positions.return_value = [mock_pos]
        mock_get_client.return_value = mock_client

        res = get_account_and_positions()
        assert isinstance(res, AccountSummary)
        assert res.equity == 100000.0
        assert res.cash == 85000.0
        assert len(res.open_positions) == 1
        assert res.open_positions[0].symbol == "AAPL"


def test_get_account_and_positions_with_orders():
    """Verifica el parseo de órdenes pendientes y bracket legs."""
    mock_acc = MagicMock()
    mock_acc.equity = "100000.00"
    mock_acc.cash = "85000.00"
    mock_acc.buying_power = "170000.00"
    mock_acc.portfolio_value = "100000.00"
    mock_acc.trading_blocked = False

    mock_leg_sl = MagicMock()
    mock_leg_sl.order_type.value = "stop"
    mock_leg_sl.stop_price = "115.00"

    mock_leg_tp = MagicMock()
    mock_leg_tp.order_type.value = "limit"
    mock_leg_tp.limit_price = "130.00"

    mock_order = MagicMock()
    mock_order.id = "ord-123"
    mock_order.client_order_id = "itba_nvda_123"
    mock_order.symbol = "NVDA"
    mock_order.qty = "50"
    mock_order.side.value = "buy"
    mock_order.order_type.value = "market"
    mock_order.status.value = "accepted"
    mock_order.submitted_at = None
    mock_order.filled_at = None
    mock_order.filled_avg_price = None
    mock_order.limit_price = None
    mock_order.legs = [mock_leg_sl, mock_leg_tp]

    with patch("src.tools.alpaca_broker.get_alpaca_trading_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get_account.return_value = mock_acc
        mock_client.get_all_positions.return_value = []
        mock_client.get_orders.side_effect = [[mock_order], [mock_order]]
        mock_get_client.return_value = mock_client

        res = get_account_and_positions()
        assert isinstance(res, AccountSummary)
        assert len(res.open_orders) == 1
        assert res.open_orders[0].symbol == "NVDA"
        assert res.open_orders[0].stop_loss_price == 115.0
        assert res.open_orders[0].take_profit_price == 130.0
