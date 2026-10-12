"""Definición y compilación del flujo multiagente (StateGraph) con LangGraph."""

from langgraph.graph import END, START, StateGraph

from src.agents.market_analyst import market_analyst_node
from src.agents.risk_gatekeeper import risk_gatekeeper_node
from src.agents.supervisor import supervisor_node
from src.graph.checkpointer import get_checkpointer
from src.graph.state import AgentState
from src.utils.logger import get_logger

logger = get_logger("graph.workflow")


def route_supervisor(state: AgentState) -> str:
    """Función de enrutamiento condicional desde el Supervisor."""
    step = state.next_step
    if step == "analyst":
        return "market_analyst"
    elif step == "risk_gate":
        return "risk_gate"
    return END


def route_analyst(state: AgentState) -> str:
    """Función de enrutamiento condicional desde el Analista de Mercado."""
    if state.next_step == "risk_gate" and state.trade_proposal:
        return "risk_gate"
    return END


def create_financial_graph(checkpointer=None):
    """Construye y compila el StateGraph multiagente con soporte de persistencia y HITL."""
    builder = StateGraph(AgentState)

    # 1. Agregar Nodos de Agentes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("market_analyst", market_analyst_node)
    builder.add_node("risk_gate", risk_gatekeeper_node)

    # 2. Agregar Aristas
    builder.add_edge(START, "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "market_analyst": "market_analyst",
            "risk_gate": "risk_gate",
            END: END,
        },
    )

    builder.add_conditional_edges(
        "market_analyst",
        route_analyst,
        {
            "risk_gate": "risk_gate",
            END: END,
        },
    )

    builder.add_edge("risk_gate", END)

    # 3. Compilación con Checkpointer
    cp = checkpointer if checkpointer is not None else get_checkpointer()
    graph = builder.compile(checkpointer=cp)
    logger.info("StateGraph multiagente financiero compilado exitosamente.")
    return graph
