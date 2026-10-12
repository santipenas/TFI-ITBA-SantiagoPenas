"""Agente Supervisor y Orquestador del sistema multiagente financiero."""

from typing import Literal
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from src.graph.state import AgentState
from src.utils.llm_factory import get_chat_model
from src.utils.logger import get_logger

logger = get_logger("agents.supervisor")

SUPERVISOR_SYSTEM_PROMPT = """Sos el Supervisor y Orquestador de un sistema multiagente de inteligencia financiera y trading en español (ITBA).
Tu función es comprender el requerimiento del usuario y coordinar a los agentes especializados:

1. 'analyst': Si el usuario solicita analizar un activo (técnico, fundamental, noticias, balance, gráfico o si conviene comprar/vender).
2. 'risk_gate': Si el usuario pregunta por su saldo, cartera, posiciones abiertas o si ya hay una propuesta lista para validar.
3. 'respond': Si se trata de un saludo, una pregunta conceptual sobre trading o finanzas, o la síntesis final de una consulta ya analizada.

Reglas obligatorias:
- Respondé siempre en español con tono profesional, objetivo y analítico.
- Nunca prometas ganancias garantizadas ni des consejos financieros informales.
- Si decidís delegar a 'analyst', extraé con precisión el símbolo o ticker del activo (ej. AAPL, NVDA, TSLA, SPY).
"""


class SupervisorDecision(BaseModel):
    """Estructura de decisión de enrutamiento del Supervisor."""

    next_agent: Literal["analyst", "risk_gate", "respond"] = Field(
        ...,
        description="Agente especializado al que se debe delegar la tarea o 'respond' si responde directamente.",
    )
    ticker: str | None = Field(default=None, description="Ticker identificado en la consulta si aplica")
    reasoning: str = Field(..., description="Justificación breve de la decisión de enrutamiento")


def supervisor_node(state: AgentState) -> dict:
    """Nodo de LangGraph que procesa la entrada del usuario y enruta la ejecución."""
    llm = get_chat_model(temperature=0.0)
    structured_llm = llm.with_structured_output(SupervisorDecision)

    messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)] + state.messages
    try:
        decision: SupervisorDecision = structured_llm.invoke(messages)
        logger.info("Decisión del Supervisor: %s (Ticker: %s, Motivo: %s)",
                    decision.next_agent, decision.ticker, decision.reasoning)

        update: dict = {"next_step": decision.next_agent}
        if decision.ticker:
            update["current_ticker"] = decision.ticker.upper()
        return update

    except Exception as exc:
        logger.error("Error en nodo supervisor: %s. Enrutando a 'respond'.", exc)
        return {"next_step": "respond"}
