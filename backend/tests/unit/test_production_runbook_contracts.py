from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_production_runbook_references_existing_operational_scripts() -> None:
    runbook = (REPO_ROOT / "docs" / "production_runbook.md").read_text(encoding="utf-8")
    required_scripts = [
        "backend/scripts/postgres_up.sh",
        "backend/scripts/postgres_migrate.sh",
        "backend/scripts/async_up.sh",
        "backend/scripts/async_down.sh",
        "backend/scripts/smoke_retrieval_api.sh",
        "backend/scripts/smoke_retrieval_async_api.sh",
        "backend/scripts/smoke_knowledge_indexing_api.sh",
        "backend/scripts/smoke_canonical_retrieval.sh",
        "backend/scripts/smoke_authoring_async_api.sh",
        "backend/scripts/smoke_retrieval_mcp.sh",
        "backend/scripts/smoke_repository_mcp.sh",
        "backend/scripts/smoke_artifact_writer_mcp.sh",
        "backend/scripts/smoke_template_library_mcp.sh",
        "backend/scripts/smoke_review_approval_mcp.sh",
        "backend/scripts/smoke_configuration_library_mcp.sh",
        "backend/scripts/smoke_release_gate.sh",
        "backend/scripts/release_decision_gate.sh",
        "backend/scripts/postgres_down.sh",
    ]

    for script in required_scripts:
        assert script in runbook
        assert (REPO_ROOT / script).exists(), script


def test_production_runbook_covers_required_operational_sections() -> None:
    runbook = (REPO_ROOT / "docs" / "production_runbook.md").read_text(encoding="utf-8")

    for heading in [
        "## 3. Deploy And Migrate",
        "## 4. FastAPI Smoke",
        "## 5. Async/Celery Smoke",
        "## 6. MCP Smoke",
        "## 7. RBAC Rehearsal",
        "## 8. Backup And Restore",
        "## 9. Rollback",
        "## 10. Release Gate",
    ]:
        assert heading in runbook

    for env_name in [
        "APP_RUNTIME_PROFILE",
        "APP_DB_DSN",
        "APP_ASYNC_PROVIDER",
        "APP_AUTH_ENABLED",
        "OPENROUTER_API_KEY",
        "RUN_DOCKER_ASYNC_E2E",
        "RUN_EXTERNAL_LLM_TESTS",
    ]:
        assert env_name in runbook


def test_increment_30_handoff_points_to_production_runbook() -> None:
    handoff = (REPO_ROOT / "docs" / "handoff" / "2026-04-27_increment_30_production_boundary_handoff.md").read_text(
        encoding="utf-8"
    )

    assert "docs/production_runbook.md" in handoff
    assert "Increment 31: Knowledge Factory Hardening" in handoff
