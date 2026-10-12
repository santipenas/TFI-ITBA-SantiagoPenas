"""Herramienta de análisis técnico y precios de mercado usando yfinance y pandas-ta localmente."""

from datetime import datetime, timezone
import pandas as pd
import pandas_ta as ta
import yfinance as yf

from src.contracts.models import (
    DataProvenance,
    TechnicalIndicators,
    TechnicalSummaryOutput,
    ToolErrorObservation,
)
from src.utils.logger import get_logger

logger = get_logger("tools.market_data")


def get_stock_technical_summary(
    ticker: str,
    timeframe: str = "1d",
    period_days: int = 250,
) -> TechnicalSummaryOutput | ToolErrorObservation:
    """Calcula indicadores técnicos clave en local sobre velas históricas de un activo.

    Args:
        ticker: Símbolo bursátil estadounidense (ej. AAPL, NVDA, SPY).
        timeframe: Intervalo de las velas ('1d', '1h', '15m').
        period_days: Días calendario hacia atrás a descargar (mínimo 30, sugerido 250).

    Returns:
        TechnicalSummaryOutput con medias móviles, RSI, ATR y sesgo direccional,
        o ToolErrorObservation en caso de fallo.
    """
    clean_ticker = ticker.strip().upper()
    try:
        # Descarga de datos mediante yfinance
        df = yf.download(
            tickers=clean_ticker,
            period=f"{period_days}d",
            interval=timeframe,
            progress=False,
            auto_adjust=True,
        )

        if df is None or df.empty or len(df) < 20:
            logger.warning("Datos insuficientes descargados para %s", clean_ticker)
            return ToolErrorObservation(
                code="INSUFFICIENT_DATA",
                message=f"No se obtuvieron suficientes velas históricas para el activo '{clean_ticker}'.",
                retryable=False,
            )

        # Aplanado de MultiIndex en caso de que yfinance devuelva columnas anidadas
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Asegurar nombres de columnas en minúsculas estándar
        df.columns = [col.lower() for col in df.columns]

        close = df["close"]
        high = df["high"]
        low = df["low"]

        current_price = float(close.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(close) > 1 else current_price
        daily_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        # Cálculo local de indicadores con pandas-ta
        # 1. Medias Móviles Simples
        sma_20_series = ta.sma(close, length=20)
        sma_50_series = ta.sma(close, length=50) if len(df) >= 50 else None
        sma_200_series = ta.sma(close, length=200) if len(df) >= 200 else None

        sma_20 = float(sma_20_series.iloc[-1]) if sma_20_series is not None and not pd.isna(sma_20_series.iloc[-1]) else None
        sma_50 = float(sma_50_series.iloc[-1]) if sma_50_series is not None and not pd.isna(sma_50_series.iloc[-1]) else None
        sma_200 = float(sma_200_series.iloc[-1]) if sma_200_series is not None and not pd.isna(sma_200_series.iloc[-1]) else None

        # 2. RSI (14)
        rsi_series = ta.rsi(close, length=14)
        rsi_14 = float(rsi_series.iloc[-1]) if rsi_series is not None and not pd.isna(rsi_series.iloc[-1]) else None

        # 3. ATR (14)
        atr_series = ta.atr(high, low, close, length=14)
        atr_14 = float(atr_series.iloc[-1]) if atr_series is not None and not pd.isna(atr_series.iloc[-1]) else None

        # Determinación de Sesgo Direccional según Skill SOP
        trend_bias = "NEUTRAL"
        if sma_20 and sma_50 and sma_200:
            if current_price > sma_20 > sma_50 > sma_200:
                trend_bias = "BULLISH"
            elif current_price < sma_20 < sma_50 < sma_200:
                trend_bias = "BEARISH"
        elif sma_20 and sma_50:
            if current_price > sma_20 > sma_50:
                trend_bias = "BULLISH"
            elif current_price < sma_20 < sma_50:
                trend_bias = "BEARISH"

        indicators = TechnicalIndicators(
            current_price=round(current_price, 2),
            rsi_14=round(rsi_14, 2) if rsi_14 is not None else None,
            sma_20=round(sma_20, 2) if sma_20 is not None else None,
            sma_50=round(sma_50, 2) if sma_50 is not None else None,
            sma_200=round(sma_200, 2) if sma_200 is not None else None,
            atr_14=round(atr_14, 2) if atr_14 is not None else None,
            trend_bias=trend_bias,
            daily_change_pct=daily_change_pct,
        )

        provenance = DataProvenance(
            source_name="yfinance + pandas-ta (local)",
            data_quality="LIVE",
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            currency="USD",
        )

        return TechnicalSummaryOutput(
            ticker=clean_ticker,
            provenance=provenance,
            indicators=indicators,
        )

    except Exception as exc:
        logger.error("Error al procesar análisis técnico de %s: %s", clean_ticker, exc)
        return ToolErrorObservation(
            code="TECHNICAL_ANALYSIS_ERROR",
            message=f"Error inesperado al calcular indicadores para '{clean_ticker}': {str(exc)}",
            retryable=True,
        )


def get_historical_candles(
    ticker: str,
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """Descarga un DataFrame de velas OHLCV para renderizado de gráficos en la UI."""
    clean_ticker = ticker.strip().upper()
    df = yf.download(
        tickers=clean_ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df
