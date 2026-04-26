from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from application.async_dispatcher import InlineAuthoringAsyncDispatcher
from application.errors import InvalidCursorError, InvalidTaskStateError
from infra.fastmcp.review_approval_service import FastMcpReviewApprovalService
from schemas.api.contracts import (
    HitlActionStatusSummaryItem,
    HitlActionsResponse,
    HitlDecisionSummaryItem,
    HitlObservabilityResponse,
    HitlOutlineResponse,
    HitlOutlineSectionResponse,
    HitlReviewActionResponse,
    HitlReviewStatusResponse,
    HitlReviewerSummaryItem,
    SubmitHitlReviewRequest,
    TaskStatusResponse,
)


class _FakeAuthoringService:
    def __init__(self) -> None:
        self.submit_calls: list[dict[str, Any]] = []
        self.list_calls: list[dict[str, Any]] = []
        self.summary_calls: list[dict[str, Any]] = []
        self.raise_on_submit = False

    def hitl_status(self, task_id: str) -> HitlReviewStatusResponse:
        return HitlReviewStatusResponse(
            task_id=task_id,
            status='waiting_human',
            required=True,
            current_iteration=1,
            max_iterations=2,
            can_submit=True,
            pending_action_id='action-1',
            pending_reason='Нужно reviewer решение.',
            reviewer_notes='Check release blockers.',
            phase='outline_review',
            outline=HitlOutlineResponse(
                template_id='release_readiness',
                sections=[
                    HitlOutlineSectionResponse(
                        section_id='risk_assessment',
                        title='Risk Assessment',
                        review_status='pending',
                        objective='Assess blockers.',
                        required_keywords=['risk'],
                    )
                ],
            ),
            actions=[
                HitlReviewActionResponse(
                    action_id='action-0',
                    iteration=1,
                    decision='needs_changes',
                    comment='Need more details',
                    status='completed',
                    metadata={'reviewer': 'alice'},
                    created_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
                )
            ],
        )

    def list_hitl_actions(self, **kwargs: Any) -> HitlActionsResponse:
        self.list_calls.append(dict(kwargs))
        return HitlActionsResponse(
            items=[
                HitlReviewActionResponse(
                    action_id='action-1',
                    iteration=1,
                    decision='approve',
                    comment='Ship it',
                    status='completed',
                    metadata={'reviewer': 'alice'},
                    created_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
                )
            ],
            limit=int(kwargs.get('limit', 50) or 50),
            total_returned=1,
            next_cursor=None,
            has_more=False,
        )

    def submit_hitl(
        self,
        task_id: str,
        request: SubmitHitlReviewRequest,
        *,
        dispatcher: InlineAuthoringAsyncDispatcher,
    ) -> TaskStatusResponse:
        self.submit_calls.append({'task_id': task_id, 'request': request, 'dispatcher': dispatcher})
        if self.raise_on_submit:
            raise InvalidTaskStateError('submit not allowed')
        return TaskStatusResponse(
            task_id=task_id,
            status='queued',
            current_node='hitl_dispatch',
            details={'hitl_dispatch_id': 'dispatch-1', 'queue_name': 'authoring'},
        )

    def hitl_observability_summary(self, **kwargs: Any) -> HitlObservabilityResponse:
        self.summary_calls.append(dict(kwargs))
        return HitlObservabilityResponse(
            total_actions=2,
            unique_tasks=1,
            pending_actions=0,
            queued_actions=0,
            processing_actions=0,
            completed_actions=2,
            approve_total=1,
            needs_changes_total=1,
            reject_total=0,
            avg_iteration=1.5,
            max_iteration=2,
            latest_action_at=datetime(2026, 4, 26, tzinfo=timezone.utc),
            statuses=[HitlActionStatusSummaryItem(status='completed', total=2)],
            decisions=[
                HitlDecisionSummaryItem(decision='approve', total=1),
                HitlDecisionSummaryItem(decision='needs_changes', total=1),
            ],
            reviewers=[
                HitlReviewerSummaryItem(
                    reviewer='alice',
                    total=2,
                    approve_total=1,
                    needs_changes_total=1,
                    reject_total=0,
                )
            ],
        )


def _build_dispatcher() -> InlineAuthoringAsyncDispatcher:
    return InlineAuthoringAsyncDispatcher(
        runner=lambda task_id, payload: {'task_id': task_id, 'payload': payload},
        hitl_runner=lambda task_id, payload: {'task_id': task_id, 'payload': payload},
    )


def test_fastmcp_review_approval_service_metadata_contains_tools() -> None:
    service = FastMcpReviewApprovalService(_FakeAuthoringService(), dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    metadata = service.metadata()

    assert metadata['service_name'] == 'review-approval-mcp'
    assert 'get_hitl_status' in metadata['tool_names']
    assert 'list_hitl_actions' in metadata['tool_names']
    assert 'submit_hitl_review' in metadata['tool_names']
    assert 'get_hitl_observability_summary' in metadata['tool_names']


def test_fastmcp_review_approval_service_get_hitl_status_returns_status_payload() -> None:
    service = FastMcpReviewApprovalService(_FakeAuthoringService(), dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    result = service.get_hitl_status({'task_id': 'task-1'})

    assert result['task_id'] == 'task-1'
    assert result['status'] == 'waiting_human'
    assert result['can_submit'] is True
    assert result['outline']['template_id'] == 'release_readiness'
    assert result['actions'][0]['decision'] == 'needs_changes'


def test_fastmcp_review_approval_service_list_hitl_actions_returns_filtered_page() -> None:
    fake = _FakeAuthoringService()
    service = FastMcpReviewApprovalService(fake, dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    result = service.list_hitl_actions({'task_id': 'task-1', 'reviewer': 'alice', 'limit': 10})

    assert result['total_returned'] == 1
    assert result['items'][0]['decision'] == 'approve'
    assert fake.list_calls[0]['task_id'] == 'task-1'
    assert fake.list_calls[0]['reviewer'] == 'alice'
    assert fake.list_calls[0]['limit'] == 10


def test_fastmcp_review_approval_service_submit_hitl_review_uses_existing_dispatcher() -> None:
    fake = _FakeAuthoringService()
    dispatcher = _build_dispatcher()
    service = FastMcpReviewApprovalService(fake, dispatcher=dispatcher)  # type: ignore[arg-type]
    service.register_tools()

    result = service.submit_hitl_review(
        {
            'task_id': 'task-1',
            'decision': 'approve',
            'comment': 'Looks good',
            'metadata': {'reviewer': 'alice'},
            'idempotency_key': 'mcp-1',
            'expected_iteration': 1,
        }
    )

    assert result['status'] == 'queued'
    assert fake.submit_calls[0]['task_id'] == 'task-1'
    assert fake.submit_calls[0]['dispatcher'] is dispatcher
    assert fake.submit_calls[0]['request'].decision == 'approve'
    assert fake.submit_calls[0]['request'].idempotency_key == 'mcp-1'


def test_fastmcp_review_approval_service_submit_hitl_review_maps_invalid_state_to_value_error() -> None:
    fake = _FakeAuthoringService()
    fake.raise_on_submit = True
    service = FastMcpReviewApprovalService(fake, dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    with pytest.raises(ValueError, match='submit not allowed'):
        service.submit_hitl_review({'task_id': 'task-1', 'decision': 'approve'})


def test_fastmcp_review_approval_service_list_hitl_actions_invalid_cursor_maps_to_value_error() -> None:
    class _BrokenAuthoringService(_FakeAuthoringService):
        def list_hitl_actions(self, **kwargs: Any) -> HitlActionsResponse:  # type: ignore[override]
            raise InvalidCursorError('cursor is invalid')

    service = FastMcpReviewApprovalService(_BrokenAuthoringService(), dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    with pytest.raises(ValueError, match='cursor is invalid'):
        service.list_hitl_actions({'cursor': 'bad-cursor'})


def test_fastmcp_review_approval_service_get_hitl_observability_summary_returns_aggregates() -> None:
    fake = _FakeAuthoringService()
    service = FastMcpReviewApprovalService(fake, dispatcher=_build_dispatcher())  # type: ignore[arg-type]
    service.register_tools()

    result = service.get_hitl_observability_summary({'reviewer': 'alice'})

    assert result['total_actions'] == 2
    assert result['approve_total'] == 1
    assert result['reviewers'][0]['reviewer'] == 'alice'
    assert fake.summary_calls[0]['reviewer'] == 'alice'
