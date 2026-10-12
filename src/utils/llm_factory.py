"""Fábrica de modelos LLM con soporte de fallback automático acotado (OpenAI <-> Gemini)."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("utils.llm_factory")


def get_chat_model(temperature: float = 0.1) -> BaseChatModel:
    """Crea y retorna el modelo de chat configurado con fallback automático en caso de falla.

    Si el proveedor primario es OpenAI, intenta ChatOpenAI y conmuta a ChatGoogleGenerativeAI
    ante errores de cuota, timeout o conexión.

    Args:
        temperature: Parámetro de creatividad / determinismo del modelo (0.0 a 1.0).

    Returns:
        Instancia de BaseChatModel (con .with_fallbacks si ambos están configurados).
    """
    primary_provider = settings.primary_llm_provider.lower()
    openai_model = None
    gemini_model = None

    # Inicialización de OpenAI si la clave está disponible
    if settings.openai_api_key:
        try:
            openai_model = ChatOpenAI(
                model=settings.openai_model_name,
                api_key=settings.openai_api_key,
                temperature=temperature,
                timeout=25.0,
                max_retries=2,
            )
        except Exception as exc:
            logger.warning("No se pudo instanciar ChatOpenAI: %s", exc)

    # Inicialización de Gemini si la clave está disponible
    if settings.gemini_api_key:
        try:
            gemini_model = ChatGoogleGenerativeAI(
                model=settings.gemini_model_name,
                google_api_key=settings.gemini_api_key,
                temperature=temperature,
                timeout=25.0,
                max_retries=2,
            )
        except Exception as exc:
            logger.warning("No se pudo instanciar ChatGoogleGenerativeAI: %s", exc)

    # Configuración de Primary con Fallback
    if primary_provider == "openai":
        if openai_model and gemini_model:
            logger.info(
                "Configurado OpenAI (%s) como primario con fallback a Gemini (%s).",
                settings.openai_model_name,
                settings.gemini_model_name,
            )
            return openai_model.with_fallbacks([gemini_model])
        elif openai_model:
            logger.info("Configurado OpenAI (%s) como único modelo disponible.", settings.openai_model_name)
            return openai_model
        elif gemini_model:
            logger.warning("OpenAI no disponible. Usando Gemini (%s) directamente.", settings.gemini_model_name)
            return gemini_model

    elif primary_provider == "gemini":
        if gemini_model and openai_model:
            logger.info(
                "Configurado Gemini (%s) como primario con fallback a OpenAI (%s).",
                settings.gemini_model_name,
                settings.openai_model_name,
            )
            return gemini_model.with_fallbacks([openai_model])
        elif gemini_model:
            return gemini_model
        elif openai_model:
            return openai_model

    raise RuntimeError("No se pudo inicializar ningún proveedor LLM. Verifique las claves en .env.")
