from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class FrameworkClientError(RuntimeError):
    """Raised when platform API call fails."""


@dataclass
class FrameworkClient:
    """Thin client over the framework public HTTP API.

    This keeps example agents independent from internal framework code.
    """

    base_url: str
    timeout_sec: int = 30

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body: bytes | None = None
        headers: dict[str, str] = {}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        request = urllib.request.Request(url=url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            detail = raw
            try:
                detail = json.dumps(json.loads(raw), ensure_ascii=False)
            except json.JSONDecodeError:
                pass
            raise FrameworkClientError(f"{method} {path} failed: HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise FrameworkClientError(f"{method} {path} failed: {exc}") from exc

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def start_retrieval(
        self,
        *,
        query: str,
        requester: str,
        case_dataset_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/tasks/retrieval/start",
            payload={
                "query": query,
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": {
                    "requester": requester,
                    "case_dataset_id": case_dataset_id,
                },
            },
        )

    def start_authoring(
        self,
        *,
        query: str,
        requester: str,
        case_dataset_id: str,
        workflow_mode: str,
        draft_strategy: str,
        artifact_title: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/tasks/authoring/start",
            payload={
                "query": query,
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": {
                    "requester": requester,
                    "case_dataset_id": case_dataset_id,
                },
                "artifact_type": "release_report",
                "artifact_title": artifact_title,
                "artifact_format": "markdown",
                "workflow_mode": workflow_mode,
                "draft_strategy": draft_strategy,
            },
        )

    def start_authoring_async(
        self,
        *,
        query: str,
        requester: str,
        case_dataset_id: str,
        workflow_mode: str,
        draft_strategy: str,
        artifact_title: str,
        hitl_required: bool,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/tasks/authoring/start_async",
            payload={
                "query": query,
                "filters": {
                    "project_id": "p1",
                    "document_types": ["requirements", "methodology", "security", "operations", "governance"],
                },
                "task_context": {
                    "requester": requester,
                    "case_dataset_id": case_dataset_id,
                },
                "artifact_type": "release_report",
                "artifact_title": artifact_title,
                "artifact_format": "markdown",
                "workflow_mode": workflow_mode,
                "draft_strategy": draft_strategy,
                "hitl_required": hitl_required,
            },
        )

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/tasks/{urllib.parse.quote(task_id)}")

    def get_evidence(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/tasks/{urllib.parse.quote(task_id)}/evidence")

    def get_artifact(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/tasks/{urllib.parse.quote(task_id)}/artifact")

    def get_hitl_status(self, task_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/tasks/{urllib.parse.quote(task_id)}/hitl")

    def submit_hitl_review(
        self,
        *,
        task_id: str,
        decision: str,
        expected_iteration: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/tasks/{urllib.parse.quote(task_id)}/hitl/submit",
            payload={
                "decision": decision,
                "comment": f"agent_examples decision: {decision}",
                "metadata": {"source": "agent_examples"},
                "expected_iteration": expected_iteration,
                "idempotency_key": idempotency_key,
            },
        )
