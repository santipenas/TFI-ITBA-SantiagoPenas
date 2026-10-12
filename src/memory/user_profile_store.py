"""Almacenamiento persistente de perfil y preferencias de usuario mediante SQLite."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger("memory.user_profile")


class UserProfileStore:
    """Gestiona la persistencia de perfiles y preferencias de usuario en SQLite."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path(settings.user_profile_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    risk_profile TEXT NOT NULL DEFAULT 'MODERATE',
                    watchlist TEXT NOT NULL DEFAULT '["AAPL", "NVDA", "MSFT", "SPY"]',
                    preferred_timeframe TEXT NOT NULL DEFAULT '1d',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get_profile(self, user_id: str = "default_user") -> dict[str, Any]:
        """Recupera el perfil de usuario o crea uno por defecto si no existe."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT risk_profile, watchlist, preferred_timeframe FROM user_profiles WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "risk_profile": row[0],
                    "watchlist": json.loads(row[1]),
                    "preferred_timeframe": row[2],
                }

        # Perfil por defecto
        default_profile = {
            "risk_profile": "MODERATE",
            "watchlist": ["AAPL", "NVDA", "MSFT", "SPY"],
            "preferred_timeframe": "1d",
        }
        self.save_profile(user_id, default_profile)
        return default_profile

    def save_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        """Guarda o actualiza las preferencias del usuario."""
        risk_profile = profile.get("risk_profile", "MODERATE")
        watchlist = json.dumps(profile.get("watchlist", ["AAPL", "NVDA", "MSFT", "SPY"]))
        timeframe = profile.get("preferred_timeframe", "1d")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (user_id, risk_profile, watchlist, preferred_timeframe, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    risk_profile = excluded.risk_profile,
                    watchlist = excluded.watchlist,
                    preferred_timeframe = excluded.preferred_timeframe,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, risk_profile, watchlist, timeframe),
            )
            conn.commit()
        logger.info("Perfil de usuario '%s' actualizado: %s", user_id, risk_profile)
