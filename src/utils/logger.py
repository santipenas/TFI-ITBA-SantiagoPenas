"""Módulo de logging estructurado y sanitización de secretos para la terminal y auditoría."""

import logging
import re
import sys
from src.config import settings

# Patrones para detectar y enmascarar posibles claves de API en logs
_SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})"),  # OpenAI
    re.compile(r"(AQ\.[a-zA-Z0-9_\-]{30,})"),  # Gemini
    re.compile(r"(tvly-[a-zA-Z0-9_\-]{20,})"),  # Tavily
    re.compile(r"(PK[A-Z0-9]{20,})"),  # Alpaca Key
]


class SanitizedFormatter(logging.Formatter):
    """Formateador de logs que enmascara automáticamente tokens y credenciales."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        sanitized = original
        for pattern in _SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger configurado con el nivel del sistema y formateador seguro."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = SanitizedFormatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    return logger
