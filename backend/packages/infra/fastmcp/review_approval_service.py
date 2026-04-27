from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from application.async_dispatcher import AuthoringAsyncDispatcher
from application.authoring_service import AuthoringApplicationService
from application.errors import InvalidCursorError, InvalidTaskStateError, TaskNotFoundError, WorkflowExecutionError
from framework.mcp import BaseFastMcpService
from schemas.api.contracts import SubmitHitlReviewRequest
from schemas.mcp.review_approval import (
    ReviewApprovalMcpGetHitlObservabilitySummaryInput,
    ReviewApprovalMcpGetHitlObservabilitySummaryOutput,
    ReviewApprovalMcpGetHitlStatusInput,
    ReviewApprovalMcpGetHitlStatusOutput,
    ReviewApprovalMcpListHitlActionsInput,
    ReviewApprovalMcpListHitlActionsOutput,
    ReviewApprovalMcpSubmitHitlReviewInput,
    ReviewApprovalMcpSubmitHitlReviewOutput,
)


class FastMcpReviewApprovalService(BaseFastMcpService):
    """MCP-сервис reviewer/HITL boundary поверх existing authoring service."""

    def __init__(
        self,
        authoring_service: AuthoringApplicationService,
        *,
        dispatcher: AuthoringAsyncDispatcher,
    ) -> None:
        super().__init__(service_name='review-approval-mcp', version='0.1.0')
        self._authoring_service = authoring_service
        self._dispatcher = dispatcher
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tools(self) -> None:
        self._tools = self._register_toolset(
            {
                'get_hitl_status': self.get_hitl_status,
                'list_hitl_actions': self.list_hitl_actions,
                'submit_hitl_review': self.submit_hitl_review,
                'get_hitl_observability_summary': self.get_hitl_observability_summary,
            },
            required_roles={'submit_hitl_review': ('reviewer',)},
        )

    def get_hitl_status(self, payload: ReviewApprovalMcpGetHitlStatusInput | dict[str, Any]) -> dict[str, Any]:
        """Возвращает текущий HITL-статус authoring задачи."""

        validated = ReviewApprovalMcpGetHitlStatusInput.model_validate(payload)
        try:
            result = self._authoring_service.hitl_status(validated.task_id)
        except (InvalidTaskStateError, TaskNotFoundError) as exc:
            raise self._operation_error(exc) from exc
        response = ReviewApprovalMcpGetHitlStatusOutput.model_validate(result.model_dump(mode='json'))
        return response.model_dump(mode='json')

    def list_hitl_actions(
        self,
        payload: ReviewApprovalMcpListHitlActionsInput | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает историю reviewer/HITL действий с фильтрами."""

        if payload is None:
            validated = ReviewApprovalMcpListHitlActionsInput()
        else:
            validated = ReviewApprovalMcpListHitlActionsInput.model_validate(payload)

        try:
            result = self._authoring_service.list_hitl_actions(
                limit=validated.limit,
                cursor=validated.cursor,
                task_id=validated.task_id,
                decision=validated.decision,
                status=validated.status,
                reviewer=validated.reviewer,
                created_from=validated.created_from,
                created_to=validated.created_to,
            )
        except InvalidCursorError as exc:
            raise self._operation_error(exc) from exc
        response = ReviewApprovalMcpListHitlActionsOutput.model_validate(result.model_dump(mode='json'))
        return response.model_dump(mode='json')

    def submit_hitl_review(self, payload: ReviewApprovalMcpSubmitHitlReviewInput | dict[str, Any]) -> dict[str, Any]:
        """Принимает reviewer-решение и ставит continuation в existing async dispatcher plane."""

        validated = ReviewApprovalMcpSubmitHitlReviewInput.model_validate(payload)
        actor_context = self._authorize_tool('submit_hitl_review', actor=validated.actor, roles=validated.roles)
        metadata = dict(validated.metadata)
        if actor_context.actor_id is not None:
            metadata['reviewer'] = actor_context.actor_id
        request = SubmitHitlReviewRequest(
            decision=validated.decision,
            comment=validated.comment,
            metadata=metadata,
            idempotency_key=validated.idempotency_key,
            expected_iteration=validated.expected_iteration,
        )
        try:
            result = self._authoring_service.submit_hitl(
                validated.task_id,
                request,
                dispatcher=self._dispatcher,
            )
        except (InvalidTaskStateError, TaskNotFoundError, WorkflowExecutionError) as exc:
            raise self._operation_error(exc) from exc
        response = ReviewApprovalMcpSubmitHitlReviewOutput.model_validate(result.model_dump(mode='json'))
        return response.model_dump(mode='json')

    def get_hitl_observability_summary(
        self,
        payload: ReviewApprovalMcpGetHitlObservabilitySummaryInput | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает reviewer/HITL observability summary поверх existing read-model."""

        if payload is None:
            validated = ReviewApprovalMcpGetHitlObservabilitySummaryInput()
        else:
            validated = ReviewApprovalMcpGetHitlObservabilitySummaryInput.model_validate(payload)

        result = self._authoring_service.hitl_observability_summary(
            task_id=validated.task_id,
            decision=validated.decision,
            status=validated.status,
            reviewer=validated.reviewer,
            created_from=validated.created_from,
            created_to=validated.created_to,
        )
        response = ReviewApprovalMcpGetHitlObservabilitySummaryOutput.model_validate(result.model_dump(mode='json'))
        return response.model_dump(mode='json')


def create_fastmcp_review_approval_server(service: FastMcpReviewApprovalService) -> Any:
    """Создает FastMCP runtime-сервер для review/approval service."""

    try:
        from fastmcp import FastMCP
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            'Не удалось импортировать fastmcp. Установите пакет `fastmcp` для запуска MCP-сервиса.'
        ) from exc

    service.register_tools()
    server = FastMCP('review-approval-mcp')

    @server.tool()
    def get_hitl_status(task_id: str) -> dict[str, Any]:
        """MCP tool: get_hitl_status."""

        return service.get_hitl_status({'task_id': task_id})

    @server.tool()
    def list_hitl_actions(
        limit: int = 50,
        cursor: str | None = None,
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: list_hitl_actions."""

        return service.list_hitl_actions(
            {
                'limit': limit,
                'cursor': cursor,
                'task_id': task_id,
                'decision': decision,
                'status': status,
                'reviewer': reviewer,
                'created_from': _parse_optional_datetime(created_from),
                'created_to': _parse_optional_datetime(created_to),
            }
        )

    @server.tool()
    def submit_hitl_review(
        task_id: str,
        decision: str,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        expected_iteration: int | None = None,
        actor: str | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """MCP tool: submit_hitl_review."""

        return service.submit_hitl_review(
            {
                'task_id': task_id,
                'decision': decision,
                'comment': comment,
                'metadata': metadata or {},
                'idempotency_key': idempotency_key,
                'expected_iteration': expected_iteration,
                'actor': actor,
                'roles': roles or [],
            }
        )

    @server.tool()
    def get_hitl_observability_summary(
        task_id: str | None = None,
        decision: str | None = None,
        status: str | None = None,
        reviewer: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> dict[str, Any]:
        """MCP tool: get_hitl_observability_summary."""

        return service.get_hitl_observability_summary(
            {
                'task_id': task_id,
                'decision': decision,
                'status': status,
                'reviewer': reviewer,
                'created_from': _parse_optional_datetime(created_from),
                'created_to': _parse_optional_datetime(created_to),
            }
        )

    return server


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    return datetime.fromisoformat(value)
