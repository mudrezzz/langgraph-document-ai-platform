CREATE TABLE IF NOT EXISTS app.hitl_actions (
    action_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES app.tasks(task_id) ON DELETE CASCADE,
    iteration INTEGER NOT NULL,
    decision TEXT NOT NULL,
    status TEXT NOT NULL,
    comment TEXT NULL,
    reviewer TEXT NULL,
    idempotency_key TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (iteration >= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_hitl_actions_task_idempotency
    ON app.hitl_actions (task_id, idempotency_key);

CREATE INDEX IF NOT EXISTS ix_hitl_actions_task_created_at
    ON app.hitl_actions (task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_hitl_actions_decision_created_at
    ON app.hitl_actions (decision, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_hitl_actions_reviewer_created_at
    ON app.hitl_actions (reviewer, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_hitl_actions_status_created_at
    ON app.hitl_actions (status, created_at DESC);
