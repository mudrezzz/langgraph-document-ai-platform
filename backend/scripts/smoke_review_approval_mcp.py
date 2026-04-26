from __future__ import annotations

import argparse
import json

from apps.api.dependencies import ApiContainer
from infra.fastmcp.review_approval_service import FastMcpReviewApprovalService
from schemas.api.contracts import StartAuthoringTaskRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Smoke-проверка Review/Approval MCP service')
    parser.add_argument('--query', default='подготовь demo draft для review approval mcp', help='Запрос для authoring task')
    parser.add_argument('--reviewer', default='smoke-reviewer', help='Reviewer для submit/summary')
    parser.add_argument('--decision', default='approve', choices=['approve', 'needs_changes', 'reject'])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    container = ApiContainer()
    service = FastMcpReviewApprovalService(
        container.authoring_service,
        dispatcher=container.authoring_dispatcher,
    )
    service.register_tools()

    started = container.authoring_service.start(
        StartAuthoringTaskRequest(
            query=args.query,
            filters={'project_id': 'p1'},
            task_context={'requester': 'review-approval-mcp-smoke'},
            artifact_type='release_report',
            artifact_title='Review Approval MCP Smoke',
            artifact_format='markdown',
            draft_strategy='deterministic',
            workflow_mode='multi_step',
            hitl_required=True,
        )
    )
    if started.status != 'waiting_human':
        raise RuntimeError(f'Expected waiting_human, got {started.status}')

    status_before = service.get_hitl_status({'task_id': started.task_id})
    listed_before = service.list_hitl_actions({'task_id': started.task_id, 'limit': 20})
    submitted = service.submit_hitl_review(
        {
            'task_id': started.task_id,
            'decision': args.decision,
            'comment': f'smoke decision: {args.decision}',
            'metadata': {'reviewer': args.reviewer, 'source': 'smoke-review-approval-mcp'},
            'idempotency_key': f'review-approval-mcp-{started.task_id}-1',
            'expected_iteration': 1,
        }
    )
    status_after = service.get_hitl_status({'task_id': started.task_id})
    listed_after = service.list_hitl_actions({'task_id': started.task_id, 'limit': 20})
    summary = service.get_hitl_observability_summary({'task_id': started.task_id, 'reviewer': args.reviewer})

    payload = {
        'tool_names': service.metadata()['tool_names'],
        'task_id': started.task_id,
        'start_status': started.status,
        'hitl_status_before': status_before['status'],
        'can_submit_before': status_before['can_submit'],
        'actions_before': listed_before['total_returned'],
        'submit_status': submitted['status'],
        'hitl_status_after': status_after['status'],
        'current_iteration_after': status_after['current_iteration'],
        'actions_after': listed_after['total_returned'],
        'summary_total_actions': summary['total_actions'],
        'summary_completed_actions': summary['completed_actions'],
        'summary_decisions': {item['decision']: item['total'] for item in summary['decisions']},
        'summary_reviewers': [item['reviewer'] for item in summary['reviewers']],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=4))


if __name__ == '__main__':
    main()
