-- Audit trail for task status transitions

CREATE TABLE IF NOT EXISTS app.task_events (
    event_id BIGSERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES app.tasks(task_id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,
    from_status TEXT NULL,
    to_status TEXT NOT NULL,
    from_current_node TEXT NULL,
    to_current_node TEXT NULL,
    event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_task_events_task_id_created_at
    ON app.task_events (task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_task_events_to_status
    ON app.task_events (to_status);

CREATE INDEX IF NOT EXISTS ix_tasks_updated_at_task_id
    ON app.tasks (updated_at DESC, task_id DESC);
