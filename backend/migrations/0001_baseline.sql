-- Baseline schema for LangGraph Document AI Platform

CREATE SCHEMA IF NOT EXISTS app;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS app.documents (
    doc_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.checkpoints (
    run_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.embeddings (
    vector_key TEXT PRIMARY KEY,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_embeddings_created_at ON app.embeddings (created_at);
CREATE INDEX IF NOT EXISTS ix_documents_created_at ON app.documents (created_at);
CREATE INDEX IF NOT EXISTS ix_checkpoints_created_at ON app.checkpoints (created_at);