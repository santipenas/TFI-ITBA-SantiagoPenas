"""Componente de interfaz para la compuerta de aprobación Human-in-the-Loop (HITL)."""

import streamlit as st


def render_hitl_card(interrupt_data: dict, on_verdict_callback):
    """Renderiza la tarjeta interactiva de orden pendiente con botones de Aprobar y Rechazar.

    Args:
        interrupt_data: Diccionario con la orden propuesta expuesta por LangGraph interrupt().
        on_verdict_callback: Función a ejecutar con el veredicto del usuario ("APPROVE" o "REJECT").
    """
    ticker = interrupt_data.get("ticker", "N/A")
    side = interrupt_data.get("side", "BUY")
    qty = interrupt_data.get("qty", 0)
    entry = interrupt_data.get("entry_price", 0.0)
    sl = interrupt_data.get("stop_loss", 0.0)
    tp = interrupt_data.get("take_profit", 0.0)
    risk_usd = interrupt_data.get("risk_usd", 0.0)
    risk_pct = interrupt_data.get("risk_pct", 0.0)
    pos_val = interrupt_data.get("position_value_usd", 0.0)

    st.warning("⚠️ **ACCIÓN REQUERIDA (Human-in-the-Loop)**: Se ha generado una propuesta de orden pendiente de tu autorización.")

    with st.container(border=True):
        st.subheader(f"📝 Propuesta de Operación: {side} {qty} {ticker}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Entrada Estimada", f"${entry:,.2f}")
        col2.metric("Stop-Loss (Protección)", f"${sl:,.2f}")
        col3.metric("Take-Profit (Objetivo)", f"${tp:,.2f}")

        col4, col5 = st.columns(2)
        col4.write(f"**Riesgo Máximo en USD**: `${risk_usd:,.2f}` ({risk_pct:.2f}% del capital)")
        col5.write(f"**Valor Total de la Posición**: `${pos_val:,.2f} USD`")

        st.info("🔒 **Entorno de Destino**: Alpaca Markets Paper Trading (Simulación Sandbox). Ningún fondo real está en riesgo.")

        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("✅ APROBAR Y ENVIAR AL BROKER", type="primary", use_container_width=True):
            on_verdict_callback("APPROVE")

        if btn_col2.button("❌ RECHAZAR Y CANCELAR ORDEN", type="secondary", use_container_width=True):
            on_verdict_callback("REJECT")
