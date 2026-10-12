"""Prueba de integración en vivo con LangSmith Observability Platform.
Valida conexión, envío automático de trazas del grafo LangGraph y consulta de métricas.
"""

import sys
import time
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langsmith import Client

# Asegurar raíz en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.graph.workflow import create_financial_graph


def main():
    print(f"[*] LangSmith API Key presente: {bool(settings.langchain_api_key)}")
    print(f"[*] LangSmith Project: {settings.langchain_project}")

    client = Client()

    # Validar acceso a la plataforma
    projects = [p.name for p in client.list_projects(limit=10)]
    print(f"[*] Proyectos existentes en tu cuenta de LangSmith: {projects}")

    # Ejecutar una consulta breve para generar telemetría y trazas
    print("[*] Ejecutando workflow LangGraph con trazabilidad activa...")
    graph = create_financial_graph(checkpointer=MemorySaver())
    thread_id = f"test_langsmith_{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}

    res = graph.invoke(
        {"messages": [HumanMessage(content="Hola, ¿cuál es tu objetivo principal? Responde en una sola frase.")]},
        config=config,
    )
    last_msg = res["messages"][-1].content
    print(f"[+] Respuesta recibida: {last_msg[:80]}...")

    # Esperar propagación asíncrona a la API de LangSmith
    print("[*] Verificando recepción de telemetría en LangSmith...")
    time.sleep(3)

    runs = list(client.list_runs(project_name=settings.langchain_project, limit=5))
    print(f"[+] Trazas activas registradas en '{settings.langchain_project}': {len(runs)}")

    for run in runs:
        print(f"    - Trace ID: {run.id}")
        print(f"      Nombre: {run.name}")
        print(f"      Status: {run.status}")
        print(f"      Latencia: {run.end_time - run.start_time if run.end_time else 'En progreso'}")
        print(f"      URL de inspección: {run.url or 'https://smith.langchain.com'}")

    # URL directa al panel de observabilidad
    ui_url = f"https://smith.langchain.com/o/default/projects/p/{settings.langchain_project}"
    print("\n" + "=" * 60)
    print(f"PANEL DE CONTROL DE LANGSMITH EN VIVO:\n{ui_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
