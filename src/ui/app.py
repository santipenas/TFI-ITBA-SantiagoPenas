"""Aplicación principal de usuario en Streamlit: Interfaz Conversacional, Gráficos y HITL."""

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path independientemente de cómo se invoque Streamlit
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uuid
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
import streamlit as st

from src.contracts.trade_schemas import ValidatedTradeProposal
from src.graph.workflow import create_financial_graph
from src.memory.user_profile_store import UserProfileStore
from src.tools.market_data import get_historical_candles
from src.ui.components.charts import create_candlestick_chart
from src.ui.components.hitl_card import render_hitl_card
from src.ui.components.portfolio_sidebar import render_portfolio_sidebar


# Configuración de página de Streamlit
st.set_page_config(
    page_title="Asistente de Inversión Multiagente - ITBA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicialización de Estado de Sesión en Streamlit
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"itba_session_{uuid.uuid4().hex[:8]}"

if "graph" not in st.session_state:
    st.session_state.graph = create_financial_graph()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **¡Hola! Soy tu Asistente Multiagente de Inteligencia Financiera y Trading (ITBA)**.\n\n"
                "Puedo ayudarte a:\n"
                "- Realizar análisis técnico y fundamental de acciones y ETFs (ej. `NVDA`, `AAPL`, `MSFT`, `SPY`).\n"
                "- Investigar catalizadores de noticias recientes.\n"
                "- Evaluar oportunidades de inversión con control estricto de riesgo y dimensionamiento de posición.\n"
                "- Preparar órdenes de compra o venta para el broker de **Paper Trading** de Alpaca.\n\n"
                "¿Qué activo o consulta te gustaría evaluar hoy?"
            ),
        }
    ]

if "pending_interrupt" not in st.session_state:
    st.session_state.pending_interrupt = None

if "last_analyzed_ticker" not in st.session_state:
    st.session_state.last_analyzed_ticker = None


# Renderizar Barra Lateral de Cartera
render_portfolio_sidebar()

# Título y Encabezado Principal
st.title("📈 Asistente Multiagente de Inversión y Trading")
st.caption("Certificación Profesional en AI Agent Developer · ITBA · Trabajo Final Integrador")

# Renderizado del Historial de Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Si hay un ticker analizado recientemente, mostrar el gráfico interactivo
if st.session_state.last_analyzed_ticker:
    with st.expander(f"📊 Gráfico Interactivo de Velas: {st.session_state.last_analyzed_ticker}", expanded=True):
        try:
            df_candles = get_historical_candles(st.session_state.last_analyzed_ticker, period="6mo", interval="1d")
            fig = create_candlestick_chart(df_candles, st.session_state.last_analyzed_ticker)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"No se pudo cargar el gráfico: {e}")


# Callback para procesar la decisión humana en HITL
def handle_hitl_verdict(verdict: str):
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    with st.spinner("Procesando tu decisión y comunicando con Alpaca Paper Trading..."):
        try:
            # Reanudar la ejecución del grafo pasando el veredicto
            res = st.session_state.graph.invoke(
                Command(resume={"action": verdict}),
                config=config,
            )
            st.session_state.pending_interrupt = None

            # Obtener el último mensaje del agente tras reanudar
            if res.get("messages"):
                last_msg = res["messages"][-1].content
                st.session_state.messages.append({"role": "assistant", "content": last_msg})
            st.rerun()

        except Exception as exc:
            st.error(f"Error al reanudar la orden: {exc}")
            st.session_state.pending_interrupt = None


# Renderizado de Tarjeta HITL si el grafo se encuentra pausado
if st.session_state.pending_interrupt:
    render_hitl_card(st.session_state.pending_interrupt, handle_hitl_verdict)


# Entrada de Chat del Usuario
user_input = st.chat_input("Escribe tu consulta financiera (ej. 'Analizá NVDA para una compra swing')...")

if user_input and not st.session_state.pending_interrupt:
    # 1. Agregar y mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Invocación del Grafo Multiagente
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    profile = UserProfileStore().get_profile("default_user")

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_profile": profile,
    }

    with st.chat_message("assistant"):
        with st.spinner("El equipo de agentes está investigando los mercados..."):
            try:
                res = st.session_state.graph.invoke(initial_state, config=config)

                # Verificar si el grafo entró en estado de pausa (HITL Interrupt)
                snapshot = st.session_state.graph.get_state(config)
                if snapshot.tasks and len(snapshot.tasks) > 0 and snapshot.tasks[0].interrupts:
                    interrupt_val = snapshot.tasks[0].interrupts[0].value
                    st.session_state.pending_interrupt = interrupt_val

                # Extraer respuesta del agente (último AIMessage)
                if res.get("messages"):
                    ai_msgs = [m for m in res["messages"] if isinstance(m, AIMessage) or getattr(m, "type", "") == "ai"]
                    if ai_msgs:
                        last_msg = ai_msgs[-1].content
                        st.session_state.messages.append({"role": "assistant", "content": last_msg})

                if res.get("current_ticker"):
                    st.session_state.last_analyzed_ticker = res["current_ticker"]

                st.rerun()

            except Exception as exc:
                err_msg = f"❌ Ocurrió un error al procesar la consulta: {str(exc)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
