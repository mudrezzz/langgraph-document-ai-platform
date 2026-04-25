-- Minimal template governance: draft/published lifecycle for reusable templates

ALTER TABLE app.document_templates
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft';

UPDATE app.document_templates
SET status = COALESCE(NULLIF(status, ''), 'draft')
WHERE status IS DISTINCT FROM COALESCE(NULLIF(status, ''), 'draft');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_document_templates_status'
          AND conrelid = 'app.document_templates'::regclass
    ) THEN
        ALTER TABLE app.document_templates
            ADD CONSTRAINT ck_document_templates_status
            CHECK (status IN ('draft', 'published'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_document_templates_status_updated_at
    ON app.document_templates (status, updated_at DESC, template_id DESC, version DESC);
