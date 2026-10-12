"""Componente de visualización de gráficos interactivos de velas japonesas y medias móviles con Plotly."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Crea una figura interactiva de Plotly con velas japonesas, SMAs (20, 50, 200) y RSI en panel inferior."""
    if df.empty or len(df) < 14:
        fig = go.Figure()
        fig.add_annotation(text="Datos insuficientes para graficar", showarrow=False)
        return fig

    # Asegurar que el índice temporal sea una columna o esté normalizado
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Subplots: 1 para velas y medias móviles (75%), 2 para RSI (25%)
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=(f"Acción del Precio y Tendencia: {ticker}", "RSI (14)"),
    )

    # 1. Velas Japonesas
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Precio",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )

    # 2. Medias Móviles
    if len(df) >= 20:
        sma_20 = df["close"].rolling(20).mean()
        fig.add_trace(
            go.Scatter(x=df.index, y=sma_20, line=dict(color="#29b6f6", width=1.5), name="SMA 20"),
            row=1,
            col=1,
        )
    if len(df) >= 50:
        sma_50 = df["close"].rolling(50).mean()
        fig.add_trace(
            go.Scatter(x=df.index, y=sma_50, line=dict(color="#ffa726", width=1.5), name="SMA 50"),
            row=1,
            col=1,
        )
    if len(df) >= 200:
        sma_200 = df["close"].rolling(200).mean()
        fig.add_trace(
            go.Scatter(x=df.index, y=sma_200, line=dict(color="#ab47bc", width=1.5), name="SMA 200"),
            row=1,
            col=1,
        )

    # 3. RSI
    # Cálculo directo de RSI para el gráfico
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    fig.add_trace(
        go.Scatter(x=df.index, y=rsi, line=dict(color="#ab47bc", width=1.5), name="RSI 14"),
        row=2,
        col=1,
    )

    # Líneas de referencia para sobrecompra (70) y sobreventa (30)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=550,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig
