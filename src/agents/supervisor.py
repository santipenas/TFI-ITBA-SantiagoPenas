"""Agente Supervisor y Orquestador del sistema multiagente financiero."""

from typing import Literal, cast

from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel, Field

from src.graph.state import AgentState
from src.utils.llm_factory import get_chat_model
from src.utils.logger import get_logger

logger = get_logger("agents.supervisor")

SUPERVISOR_SYSTEM_PROMPT = """Sos el Supervisor y Orquestador de un sistema multiagente de inteligencia financiera y trading en español (ITBA).
Tu función es comprender el requerimiento del usuario y coordinar a los agentes especializados:

1. 'analyst': Si el usuario solicita analizar un activo, investigar un gráfico/noticias/fundamentales, o solicita una orden de compra/venta sobre un activo (ej. comprar acciones, abrir posición, operar). El analista investiga el activo y formula la propuesta técnica de trade.
2. 'risk_gate': Únicamente si el usuario consulta sobre su saldo, capital, efectivo disponible, estado de cuenta o lista de posiciones abiertas en Alpaca Paper Trading.
3. 'respond': Si se trata de un saludo, una pregunta conceptual sobre finanzas/economía, o una aclaración general. En este caso, DEBES proveer una respuesta completa y profesional en 'response_text'.

Reglas obligatorias:
- Respondé siempre en español con tono profesional, objetivo y analítico.
- Nunca prometas ganancias garantizadas ni des consejos financieros informales.
- SIEMPRE que en el mensaje del usuario se mencione un activo, empresa o símbolo bursátil (ej. AAPL, NVDA, TSLA, AMZN, SPY), DEBES extraer con precisión el ticker en mayúsculas en el campo 'ticker', sin importar el agente elegido.
- Toda intención de operar, comprar, vender o analizar un activo específico DEBE delegarse a 'analyst'.
"""


class SupervisorDecision(BaseModel):
    """Estructura de decisión de enrutamiento del Supervisor."""

    next_agent: Literal["analyst", "risk_gate", "respond"] = Field(
        ...,
        description="Agente especializado al que se debe delegar la tarea o 'respond' si responde directamente.",
    )
    ticker: str | None = Field(default=None, description="Ticker identificado en la consulta si aplica")
    reasoning: str = Field(..., description="Justificación breve de la decisión de enrutamiento")
    response_text: str | None = Field(
        default=None,
        description="Respuesta directa al usuario en español si next_agent es 'respond'.",
    )


def supervisor_node(state: AgentState) -> dict:
    """Nodo de LangGraph que procesa la entrada del usuario y enruta la ejecución."""
    llm = get_chat_model(temperature=0.0)
    structured_llm = llm.with_structured_output(SupervisorDecision)

    messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + state.messages
    try:
        decision = cast(SupervisorDecision, structured_llm.invoke(messages))
        logger.info(
            "Decisión del Supervisor: %s (Ticker: %s, Motivo: %s)",
            decision.next_agent,
            decision.ticker,
            decision.reasoning,
        )

        update: dict = {"next_step": decision.next_agent}
        if decision.ticker:
            update["current_ticker"] = decision.ticker.upper()

        if decision.next_agent == "respond" and decision.response_text:
            update["messages"] = [AIMessage(content=decision.response_text)]

        return update

    except Exception as exc:
        logger.error("Error en nodo supervisor: %s. Enrutando a 'respond'.", exc)
        return {
            "messages": [AIMessage(content="Entendido. ¿En qué activo o consulta de mercado puedo ayudarte hoy?")],
            "next_step": "respond",
        }
