-- Canonical document and knowledge block read-model for Knowledge Factory

CREATE TABLE IF NOT EXISTS app.canonical_documents (
    doc_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    source_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    metadata_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    structure_tree JSONB NOT NULL DEFAULT '{}'::jsonb,
    extracted_tables JSONB NOT NULL DEFAULT '[]'::jsonb,
    section_summaries JSONB NOT NULL DEFAULT '[]'::jsonb,
    quality_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.knowledge_blocks (
    block_ref TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES app.canonical_documents(doc_id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    block_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    text TEXT NOT NULL,
    heading_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_canonical_documents_updated_at
    ON app.canonical_documents (updated_at DESC, doc_id DESC);

CREATE INDEX IF NOT EXISTS ix_canonical_documents_file_type
    ON app.canonical_documents (file_type);

CREATE INDEX IF NOT EXISTS ix_knowledge_blocks_doc_id
    ON app.knowledge_blocks (doc_id);

CREATE INDEX IF NOT EXISTS ix_knowledge_blocks_block_type
    ON app.knowledge_blocks (block_type);
