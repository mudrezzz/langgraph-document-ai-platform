CREATE TABLE IF NOT EXISTS app.task_artifacts (
    task_id TEXT PRIMARY KEY REFERENCES app.tasks(task_id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL REFERENCES app.artifacts(artifact_id) ON DELETE CASCADE,
    retrieval_task_id TEXT NOT NULL REFERENCES app.tasks(task_id) ON DELETE CASCADE,
    traceability JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_task_artifacts_artifact_id
    ON app.task_artifacts (artifact_id);

CREATE INDEX IF NOT EXISTS ix_task_artifacts_retrieval_task_id
    ON app.task_artifacts (retrieval_task_id);
