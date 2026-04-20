from __future__ import annotations

import os

import pytest

from apps.api.dependencies import ApiContainer
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.config import PostgresSettings
from infra.postgres.document_repository import PostgresDocumentRepository


def test_checkpoint_store_fallback_roundtrip() -> None:
    store = LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True)

    store.save_checkpoint("run-1", {"status": "ok"})
    loaded = store.load_checkpoint("run-1")

    assert loaded == {"status": "ok"}


def test_document_repository_fallback_roundtrip() -> None:
    repo = PostgresDocumentRepository(dsn=None, use_fallback_if_unset=True)

    doc_id = repo.save({"doc_id": "d-1", "title": "Spec"})
    loaded = repo.read_document(doc_id)

    assert loaded["title"] == "Spec"


def test_pgvector_adapter_fallback_roundtrip() -> None:
    adapter = PgVectorStoreAdapter(dsn=None, use_fallback_if_unset=True)

    adapter.upsert_vector("k-1", [0.1, 0.2, 0.3], {"source": "test"})
    loaded = adapter.get_vector("k-1")

    assert loaded is not None
    vector, metadata = loaded
    assert vector == [0.1, 0.2, 0.3]
    assert metadata["source"] == "test"


def test_postgres_settings_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_DB_DSN", "postgresql://user:pass@localhost:5432/app")
    monkeypatch.setenv("APP_DB_SCHEMA", "app")
    monkeypatch.setenv("APP_VECTOR_DIM", "768")
    monkeypatch.setenv("APP_RUNTIME_PROFILE", "stage")

    settings = PostgresSettings.from_env()

    assert settings.dsn is not None
    assert settings.schema == "app"
    assert settings.vector_dim == 768
    assert settings.runtime_profile == "stage"
    assert settings.allow_fallback_persistence is True


def test_postgres_settings_rejects_invalid_schema(monkeypatch) -> None:
    monkeypatch.setenv("APP_DB_DSN", "postgresql://user:pass@localhost:5432/app")
    monkeypatch.setenv("APP_DB_SCHEMA", "bad-schema")

    try:
        _ = PostgresSettings.from_env()
    except ValueError as exc:
        assert "Некорректный SQL identifier" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка валидации schema")


def test_postgres_settings_rejects_invalid_runtime_profile(monkeypatch) -> None:
    monkeypatch.setenv("APP_RUNTIME_PROFILE", "qa")

    with pytest.raises(ValueError, match="APP_RUNTIME_PROFILE"):
        _ = PostgresSettings.from_env()


def test_postgres_settings_disables_fallback_in_prod(monkeypatch) -> None:
    monkeypatch.setenv("APP_RUNTIME_PROFILE", "prod")
    monkeypatch.delenv("APP_DB_DSN", raising=False)

    settings = PostgresSettings.from_env()

    assert settings.runtime_profile == "prod"
    assert settings.allow_fallback_persistence is False


def test_api_container_requires_dsn_in_prod(monkeypatch) -> None:
    monkeypatch.setenv("APP_RUNTIME_PROFILE", "prod")
    monkeypatch.delenv("APP_DB_DSN", raising=False)

    with pytest.raises(ValueError, match="DSN обязателен"):
        _ = ApiContainer()


def test_psycopg_mode_requires_dsn() -> None:
    try:
        _ = LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=False)
    except ValueError as exc:
        assert "DSN обязателен" in str(exc)
    else:
        raise AssertionError("Ожидалась ошибка обязательного DSN")


# Небольшая проверка, что текущий процесс не зависит от внешнего APP_DB_DSN.
def test_env_does_not_force_real_db_mode() -> None:
    previous = os.getenv("APP_DB_DSN")
    try:
        if previous is not None:
            os.environ["APP_DB_DSN"] = previous
        store = LangGraphPostgresCheckpointStore(dsn=None, use_fallback_if_unset=True)
        store.save_checkpoint("run-x", {"k": "v"})
        assert store.load_checkpoint("run-x") == {"k": "v"}
    finally:
        if previous is None:
            os.environ.pop("APP_DB_DSN", None)
        else:
            os.environ["APP_DB_DSN"] = previous
