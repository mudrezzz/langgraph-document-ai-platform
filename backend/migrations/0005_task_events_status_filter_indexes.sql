-- Indexes for task_events status filters and summary aggregations

CREATE INDEX IF NOT EXISTS ix_task_events_from_status
    ON app.task_events (from_status);

CREATE INDEX IF NOT EXISTS ix_task_events_from_to_created_at
    ON app.task_events (from_status, to_status, created_at DESC);
