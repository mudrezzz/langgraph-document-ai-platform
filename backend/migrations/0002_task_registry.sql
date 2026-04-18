-- Persistent task registry for API lifecycle history

CREATE TABLE IF NOT EXISTS app.tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    current_node TEXT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_tasks_updated_at ON app.tasks (updated_at DESC);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON app.tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_task_type ON app.tasks (task_type);
