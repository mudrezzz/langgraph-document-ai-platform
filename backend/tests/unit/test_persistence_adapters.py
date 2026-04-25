from __future__ import annotations

import os

import pytest

from apps.api.dependencies import ApiContainer
from application.template_library_service import TemplateLibraryApplicationService
from domain_docs import TemplateCompiler
from infra.pgvector.vector_store import PgVectorStoreAdapter
from infra.postgres.artifact_store import PostgresArtifactStore
from infra.postgres.checkpoint_store import LangGraphPostgresCheckpointStore
from infra.postgres.config import PostgresSettings
from infra.postgres.document_repository import PostgresDocumentRepository
from infra.postgres.task_artifact_registry import PostgresTaskArtifactRegistry
from infra.postgres.template_store import PostgresTemplateStore


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


def test_document_repository_fallback_list_documents() -> None:
    repo = PostgresDocumentRepository(dsn=None, use_fallback_if_unset=True)
    _ = repo.save({"doc_id": "d-1", "title": "Spec 1"})
    _ = repo.save({"doc_id": "d-2", "title": "Spec 2"})

    listed = repo.list_documents(limit=10, offset=0)
    listed_ids = [item["doc_id"] for item in listed]

    assert listed_ids == ["d-2", "d-1"]


def test_pgvector_adapter_fallback_roundtrip() -> None:
    adapter = PgVectorStoreAdapter(dsn=None, use_fallback_if_unset=True)

    adapter.upsert_vector("k-1", [0.1, 0.2, 0.3], {"source": "test"})
    loaded = adapter.get_vector("k-1")

    assert loaded is not None
    vector, metadata = loaded
    assert vector == [0.1, 0.2, 0.3]
    assert metadata["source"] == "test"


def test_pgvector_adapter_fallback_query_similar() -> None:
    adapter = PgVectorStoreAdapter(dsn=None, use_fallback_if_unset=True)
    adapter.upsert_vector("k-1", [1.0, 0.0], {"kind": "knowledge_block_embedding", "doc_id": "d-1"})
    adapter.upsert_vector("k-2", [0.0, 1.0], {"kind": "knowledge_block_embedding", "doc_id": "d-2"})
    adapter.upsert_vector("k-3", [1.0, 0.0], {"kind": "other", "doc_id": "d-3"})

    results = adapter.query_similar(
        [1.0, 0.0],
        limit=5,
        metadata_filter={"kind": "knowledge_block_embedding"},
    )

    assert [item.key for item in results] == ["k-1", "k-2"]
    assert results[0].score > results[1].score


def test_artifact_store_fallback_roundtrip() -> None:
    store = PostgresArtifactStore(dsn=None, use_fallback_if_unset=True)

    store.save_artifact(
        "a-1",
        {
            "artifact_id": "a-1",
            "artifact_type": "release_report",
            "title": "Report",
            "content": "ok",
            "format": "markdown",
        },
    )
    loaded = store.read_artifact("a-1")

    assert loaded["artifact_type"] == "release_report"
    assert loaded["title"] == "Report"


def test_artifact_store_fallback_list_artifacts() -> None:
    store = PostgresArtifactStore(dsn=None, use_fallback_if_unset=True)
    store.save_artifact(
        "a-1",
        {
            "artifact_id": "a-1",
            "artifact_type": "release_report",
            "title": "Report 1",
            "content": "ok-1",
            "format": "markdown",
        },
    )
    store.save_artifact(
        "a-2",
        {
            "artifact_id": "a-2",
            "artifact_type": "traceability_map",
            "title": "Traceability",
            "content": "ok-2",
            "format": "text",
        },
    )

    listed_all = store.list_artifacts(limit=10, offset=0)
    listed_reports = store.list_artifacts(limit=10, offset=0, artifact_type="release_report")

    assert [item["artifact_id"] for item in listed_all] == ["a-2", "a-1"]
    assert [item["artifact_id"] for item in listed_reports] == ["a-1"]


def test_task_artifact_registry_fallback_roundtrip() -> None:
    registry = PostgresTaskArtifactRegistry(dsn=None, use_fallback_if_unset=True)

    registry.save_link(
        task_id="authoring-1",
        artifact_id="artifact-1",
        retrieval_task_id="retrieval-1",
        traceability={
            "retrieval_task_id": "retrieval-1",
            "source_refs": [{"doc_id": "REQ-1", "version": "1", "block_id": "D-1"}],
        },
    )
    link = registry.get_link("authoring-1")

    assert link.artifact_id == "artifact-1"
    assert link.retrieval_task_id == "retrieval-1"
    assert len(link.traceability["source_refs"]) == 1


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


def test_template_store_fallback_roundtrip_and_latest_version() -> None:
    store = PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    library = TemplateLibraryApplicationService(store=store)
    compiler = TemplateCompiler()

    library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={"version": "1", "sections": [{"section_id": "overview", "title": "Overview"}]},
        )
    )
    library.upsert_template(
        compiler.compile(
            template_id="decision_memo",
            template_payload={"version": "2", "sections": [{"section_id": "decision", "title": "Decision"}]},
        ),
        metadata={"owner": "unit-test"},
    )

    latest = library.get_template("decision_memo")
    v1 = library.get_template("decision_memo", "1")
    listed = library.list_templates(template_id="decision_memo")

    assert latest.version == "2"
    assert latest.template_spec.sections[0]["section_id"] == "decision"
    assert latest.metadata["owner"] == "unit-test"
    assert v1.version == "1"
    assert listed.total_returned == 2


def test_template_store_supports_publish_and_published_latest_resolution() -> None:
    store = PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    library = TemplateLibraryApplicationService(store=store)
    compiler = TemplateCompiler()

    library.upsert_template(
        compiler.compile(
            template_id="board_memo",
            template_payload={"version": "1", "sections": [{"section_id": "draft", "title": "Draft"}]},
        )
    )
    library.upsert_template(
        compiler.compile(
            template_id="board_memo",
            template_payload={"version": "2", "sections": [{"section_id": "live", "title": "Live"}]},
        )
    )
    library.publish_template("board_memo", "2")

    published_latest = library.get_template("board_memo", published_only=True)
    published_only_list = library.list_templates(template_id="board_memo", status="published")

    assert published_latest.version == "2"
    assert published_latest.status == "published"
    assert published_only_list.total_returned == 1
    assert published_only_list.items[0].version == "2"


def test_template_store_publish_demotes_previous_published_version() -> None:
    store = PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    library = TemplateLibraryApplicationService(store=store)
    compiler = TemplateCompiler()

    library.upsert_template(
        compiler.compile(
            template_id="ops_memo",
            template_payload={"version": "1", "sections": [{"section_id": "v1", "title": "Version 1"}]},
        )
    )
    library.upsert_template(
        compiler.compile(
            template_id="ops_memo",
            template_payload={"version": "2", "sections": [{"section_id": "v2", "title": "Version 2"}]},
        )
    )

    library.publish_template("ops_memo", "1")
    library.publish_template("ops_memo", "2")

    first = library.get_template("ops_memo", "1")
    second = library.get_template("ops_memo", "2")
    published_only_list = library.list_templates(template_id="ops_memo", status="published")

    assert first.status == "draft"
    assert second.status == "published"
    assert published_only_list.total_returned == 1
    assert published_only_list.items[0].version == "2"


def test_template_library_service_compile_template_normalizes_payload() -> None:
    library = TemplateLibraryApplicationService(
        store=PostgresTemplateStore(dsn=None, use_fallback_if_unset=True)
    )

    compiled = library.compile_template(
        template_id="status_report",
        version="5",
        sections=[{"section_id": "overview", "title": "Overview"}],
        assembly_rules=[{"rule_id": "overview_first", "section_order": ["overview"]}],
    )

    assert compiled.template_id == "status_report"
    assert compiled.version == "5"
    assert compiled.sections[0]["section_id"] == "overview"
    assert compiled.assembly_rules[0]["rule_id"] == "overview_first"
