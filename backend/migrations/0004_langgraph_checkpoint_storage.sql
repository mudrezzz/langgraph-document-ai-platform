-- Dedicated storage for LangGraph checkpointer runtime data

CREATE TABLE IF NOT EXISTS app.langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT NULL,
    checkpoint_payload JSONB NOT NULL,
    metadata_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX IF NOT EXISTS ix_lg_checkpoints_thread_ns_checkpoint
    ON app.langgraph_checkpoints (thread_id, checkpoint_ns, checkpoint_id DESC);

CREATE INDEX IF NOT EXISTS ix_lg_checkpoints_updated_at
    ON app.langgraph_checkpoints (updated_at DESC);

CREATE TABLE IF NOT EXISTS app.langgraph_checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel_name TEXT NOT NULL,
    channel_version TEXT NOT NULL,
    blob_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, channel_name, channel_version)
);

CREATE INDEX IF NOT EXISTS ix_lg_blobs_thread_ns
    ON app.langgraph_checkpoint_blobs (thread_id, checkpoint_ns);

CREATE TABLE IF NOT EXISTS app.langgraph_checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    write_idx INTEGER NOT NULL,
    channel_name TEXT NOT NULL,
    value_payload JSONB NOT NULL,
    task_path TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
);

CREATE INDEX IF NOT EXISTS ix_lg_writes_thread_ns_checkpoint_created
    ON app.langgraph_checkpoint_writes (thread_id, checkpoint_ns, checkpoint_id, created_at DESC);
