"""Componente lateral de Streamlit para el estado de cartera en Alpaca y configuración de perfil."""

import pandas as pd
import streamlit as st

from src.contracts.models import AccountSummary, ToolErrorObservation
from src.memory.user_profile_store import UserProfileStore
from src.tools.alpaca_broker import get_account_and_positions


def render_portfolio_sidebar():
    """Renderiza el estado sincronizado de Alpaca Paper Trading y las preferencias del usuario."""
    st.sidebar.title("💼 Cartera y Perfil")

    profile_store = UserProfileStore()
    user_profile = profile_store.get_profile("default_user")

    # 1. Configuración de Perfil de Riesgo
    st.sidebar.subheader("⚙️ Parámetros de Inversión")
    risk_options = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
    current_idx = risk_options.index(user_profile.get("risk_profile", "MODERATE"))

    selected_risk = st.sidebar.selectbox(
        "Perfil de Riesgo",
        options=risk_options,
        index=current_idx,
        help="Define el riesgo máximo por operación (1% Conservador, 2% Moderado, 3% Agresivo).",
    )

    if selected_risk != user_profile["risk_profile"]:
        user_profile["risk_profile"] = selected_risk
        profile_store.save_profile("default_user", user_profile)
        st.sidebar.success(f"Perfil actualizado a {selected_risk}")

    st.sidebar.markdown("---")

    # 2. Estado de Cuenta de Alpaca Paper Trading
    st.sidebar.subheader("📈 Alpaca Paper Trading")
    if st.sidebar.button("🔄 Actualizar Saldo", use_container_width=True):
        st.rerun()

    account_data = get_account_and_positions()

    if isinstance(account_data, ToolErrorObservation):
        st.sidebar.warning(f"⚠️ {account_data.message}")
        st.sidebar.info("Modo simulación de interfaz activo.")
    elif isinstance(account_data, AccountSummary):
        col1, col2 = st.sidebar.columns(2)
        col1.metric("Capital Total", f"${account_data.equity:,.2f}")
        col2.metric("Efectivo", f"${account_data.cash:,.2f}")

        st.sidebar.caption(f"Poder de Compra: ${account_data.buying_power:,.2f} USD")

        st.sidebar.markdown("##### 📌 Posiciones Abiertas")
        if account_data.open_positions:
            pos_records = []
            for p in account_data.open_positions:
                pos_records.append(
                    {
                        "Activo": p.symbol,
                        "Cant.": p.qty,
                        "Precio": f"${p.current_price:.2f}",
                        "P/L ($)": f"${p.unrealized_pl:.2f}",
                    }
                )
            df_pos = pd.DataFrame(pos_records)
            st.sidebar.dataframe(df_pos, hide_index=True, use_container_width=True)
        else:
            st.sidebar.caption("Sin posiciones abiertas actualmente.")

        st.sidebar.markdown("##### ⏳ Órdenes Pendientes")
        if account_data.open_orders:
            order_records = []
            for o in account_data.open_orders:
                sl_str = f"${o.stop_loss_price:.2f}" if o.stop_loss_price else "-"
                tp_str = f"${o.take_profit_price:.2f}" if o.take_profit_price else "-"
                order_records.append(
                    {
                        "Activo": o.symbol,
                        "Cant.": int(o.qty) if o.qty.is_integer() else o.qty,
                        "Lado": o.side.upper(),
                        "Estado": o.status.upper(),
                        "SL": sl_str,
                        "TP": tp_str,
                    }
                )
            df_orders = pd.DataFrame(order_records)
            st.sidebar.dataframe(df_orders, hide_index=True, use_container_width=True)
            has_pending = any(o.status.lower() in ["accepted", "new", "held"] for o in account_data.open_orders)
            if has_pending:
                st.sidebar.info("ℹ️ Órdenes en espera de apertura de mercado de Wall Street.")
        else:
            st.sidebar.caption("Sin órdenes pendientes.")

        # 3. Historial de Órdenes Recientes
        with st.sidebar.expander("📜 Historial de Trades", expanded=False):
            if account_data.recent_orders:
                hist_records = []
                for o in account_data.recent_orders:
                    date_short = o.submitted_at[:16].replace("T", " ") if o.submitted_at else "-"
                    price_val = f"${o.filled_avg_price:.2f}" if o.filled_avg_price else "-"
                    hist_records.append(
                        {
                            "Fecha": date_short,
                            "Activo": o.symbol,
                            "Operación": f"{o.side.upper()} {int(o.qty) if o.qty.is_integer() else o.qty}",
                            "Estado": o.status.upper(),
                            "Precio": price_val,
                        }
                    )
                df_hist = pd.DataFrame(hist_records)
                st.dataframe(df_hist, hide_index=True, use_container_width=True)
            else:
                st.caption("Sin operaciones registradas.")

    st.sidebar.markdown("---")
    st.sidebar.caption("📌 **ITBA TFI 2026** · AI Agent Developer")
