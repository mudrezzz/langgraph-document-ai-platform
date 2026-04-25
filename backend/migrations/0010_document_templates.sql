-- Reusable persisted template library for template-aware authoring

CREATE TABLE IF NOT EXISTS app.document_templates (
    template_id TEXT NOT NULL,
    version TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (template_id, version)
);

CREATE INDEX IF NOT EXISTS ix_document_templates_updated_at
    ON app.document_templates (updated_at DESC, template_id DESC, version DESC);
