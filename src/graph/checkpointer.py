"""Configuración del checkpointer SQLite para persistencia y soporte de Human-in-the-Loop."""

import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("graph.checkpointer")


def get_checkpointer() -> SqliteSaver:
    """Crea y retorna una instancia de SqliteSaver conectada a data/checkpoints.db.

    Garantiza que el directorio contenedor exista y configura la conexión
    con check_same_thread=False para permitir uso seguro en entornos multihilo como Streamlit.
    """
    db_path = Path(settings.checkpoints_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    logger.info("Checkpointer SQLite inicializado en: %s", db_path)
    return SqliteSaver(conn)
