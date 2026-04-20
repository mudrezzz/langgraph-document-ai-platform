from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal, cast


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


RuntimeProfile = Literal["dev", "stage", "prod"]


@dataclass(slots=True)
class PostgresSettings:
    """Настройки подключения persistence-адаптеров к PostgreSQL."""

    dsn: str | None
    schema: str = "app"
    vector_dim: int = 1536
    runtime_profile: RuntimeProfile = "dev"

    @property
    def allow_fallback_persistence(self) -> bool:
        """Разрешает fallback-хранилища только вне production-профиля."""

        return self.runtime_profile != "prod"

    @classmethod
    def from_env(cls) -> "PostgresSettings":
        """Строит настройки из переменных окружения приложения."""

        dsn = os.getenv("APP_DB_DSN")
        schema = os.getenv("APP_DB_SCHEMA", "app")
        vector_dim_value = os.getenv("APP_VECTOR_DIM", "1536")
        runtime_profile = os.getenv("APP_RUNTIME_PROFILE", "dev").strip().lower()

        if runtime_profile not in {"dev", "stage", "prod"}:
            raise ValueError("APP_RUNTIME_PROFILE должен быть одним из: dev, stage, prod")

        try:
            vector_dim = int(vector_dim_value)
        except ValueError as exc:
            raise ValueError("APP_VECTOR_DIM должен быть целым числом") from exc

        validate_identifier(schema)

        return cls(
            dsn=dsn,
            schema=schema,
            vector_dim=vector_dim,
            runtime_profile=cast(RuntimeProfile, runtime_profile),
        )


def validate_identifier(identifier: str) -> None:
    """Проверяет, что идентификатор безопасен для подстановки в SQL."""

    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Некорректный SQL identifier: {identifier}")
