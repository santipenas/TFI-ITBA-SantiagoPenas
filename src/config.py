"""Módulo de configuración central del sistema usando Pydantic Settings.

Carga variables de entorno desde .env de forma tipada, segura y con validaciones.
"""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuraciones del sistema y variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Entorno y Logging
    app_env: str = Field(default="development", description="Entorno de ejecución")
    log_level: str = Field(default="INFO", description="Nivel de logging (DEBUG, INFO, WARNING, ERROR)")

    # Modelos LLM y Estrategia de Fallback
    primary_llm_provider: Literal["openai", "gemini"] = Field(
        default="openai",
        description="Proveedor primario de LLM ('openai' o 'gemini')",
    )
    fallback_llm_provider: Literal["openai", "gemini"] = Field(
        default="gemini",
        description="Proveedor secundario ante rate-limits o errores",
    )
    openai_model_name: str = Field(default="gpt-4o", description="Nombre del modelo OpenAI")
    gemini_model_name: str = Field(default="gemini-2.5-flash", description="Nombre del modelo Gemini")

    # Claves de LLMs
    openai_api_key: str | None = Field(default=None, description="API Key de OpenAI")
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        description="API Key de Google Gemini",
    )

    # Broker: Alpaca Paper Trading
    alpaca_api_key: str | None = Field(default=None, description="Alpaca Paper API Key")
    alpaca_secret_key: str | None = Field(default=None, description="Alpaca Paper Secret Key")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets/v2",
        description="Endpoint de Paper Trading de Alpaca",
    )

    # Datos Financieros y Noticias
    fmp_api_key: str | None = Field(default=None, description="API Key de Financial Modeling Prep")
    tavily_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILI_API_KEY"),
        description="API Key de Tavily Search",
    )
    fred_api_key: str | None = Field(default=None, description="API Key de FRED (Macroeconomía)")
    finnhub_api_key: str | None = Field(default=None, description="API Key de Finnhub")
    massive_api_key: str | None = Field(default=None, description="API Key de Massive / Polygon")
    alpha_vantage_api_key: str | None = Field(default=None, description="API Key de Alpha Vantage")

    # Observabilidad (LangSmith)
    langchain_tracing_v2: bool = Field(default=False, description="Activar trazabilidad LangSmith")
    langchain_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGCHAIN_API_KEY", "LANGSMITH_API_KEY"),
        description="API Key de LangSmith",
    )
    langchain_project: str = Field(
        default="itba-tfi-financial-agent",
        validation_alias=AliasChoices("LANGCHAIN_PROJECT", "LANGSMITH_PROJECT"),
        description="Proyecto en LangSmith",
    )

    # Rutas de Persistencia
    data_dir: Path = Field(default=Path("data"), description="Directorio de datos locales")
    checkpoints_db_path: Path = Field(
        default=Path("data/checkpoints.db"),
        description="Ruta de la base de datos de checkpoints de LangGraph",
    )
    user_profile_db_path: Path = Field(
        default=Path("data/user_profile.db"),
        description="Ruta de la base de datos de perfiles de usuario",
    )

    def model_post_init(self, __context: object) -> None:
        """Exportar variables de entorno para LangSmith si la clave está presente."""
        import os

        if self.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
            os.environ["LANGSMITH_API_KEY"] = self.langchain_api_key
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.langchain_project
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


# Instancia singleton accesible desde toda la aplicación
settings = Settings()
