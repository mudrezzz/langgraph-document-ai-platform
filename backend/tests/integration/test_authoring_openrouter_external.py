from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from apps.api.dependencies import get_container
from apps.api.main import app


def _external_llm_tests_enabled() -> bool:
    """Разрешает внешний LLM-тест только при явном флаге и наличии ключа."""

    return os.getenv("RUN_EXTERNAL_LLM_TESTS", "0").strip() == "1" and bool(os.getenv("OPENROUTER_API_KEY", "").strip())


@pytest.mark.skipif(
    not _external_llm_tests_enabled(),
    reason="RUN_EXTERNAL_LLM_TESTS=1 и OPENROUTER_API_KEY обязательны для external LLM теста",
)
def test_external_authoring_openrouter_llm_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LLM_ENABLED", "true")
    monkeypatch.setenv("APP_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("APP_LLM_STRICT", "true")
    if not os.getenv("OPENROUTER_MODEL", "").strip():
        monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    get_container.cache_clear()
    try:
        client = TestClient(app)

        start_response = client.post(
            "/api/v1/tasks/authoring/start",
            json={
                "query": "Подготовь короткий release readiness draft по evidence",
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": {
                    "requester": "external-openrouter-test",
                    "case_dataset_id": "saa_release_readiness",
                },
                "artifact_type": "release_report",
                "artifact_title": "External LLM Authoring Draft",
                "artifact_format": "markdown",
                "draft_strategy": "llm",
                "workflow_mode": "multi_step",
            },
        )
        assert start_response.status_code == 200

        task_id = start_response.json()["task_id"]
        artifact_response = client.get(f"/api/v1/tasks/{task_id}/artifact")
        assert artifact_response.status_code == 200

        artifact_payload = artifact_response.json()
        assert artifact_payload["metadata"]["draft_generation_mode"] == "llm"
        assert artifact_payload["metadata"]["draft_model_provider"] == "openrouter"
        assert artifact_payload["metadata"]["workflow_mode"] == "multi_step"
        assert len(artifact_payload["metadata"]["steps_summary"]) == 4
        assert len(artifact_payload["content"].strip()) >= 80
    finally:
        get_container.cache_clear()
