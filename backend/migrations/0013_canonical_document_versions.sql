-- Version history for canonical documents while keeping latest-read model stable

CREATE TABLE IF NOT EXISTS app.canonical_document_versions (
    doc_id TEXT NOT NULL,
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
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (doc_id, version)
);

CREATE TABLE IF NOT EXISTS app.knowledge_block_versions (
    block_ref TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    version TEXT NOT NULL,
    block_id TEXT NOT NULL,
    block_type TEXT NOT NULL,
    text TEXT NOT NULL,
    heading_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (doc_id, version) REFERENCES app.canonical_document_versions(doc_id, version) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_canonical_document_versions_updated_at
    ON app.canonical_document_versions (updated_at DESC, doc_id DESC, version DESC);

CREATE INDEX IF NOT EXISTS ix_canonical_document_versions_file_type
    ON app.canonical_document_versions (file_type, updated_at DESC, doc_id DESC, version DESC);

CREATE INDEX IF NOT EXISTS ix_knowledge_block_versions_doc_version
    ON app.knowledge_block_versions (doc_id, version, updated_at DESC, block_ref DESC);

CREATE INDEX IF NOT EXISTS ix_knowledge_block_versions_block_type
    ON app.knowledge_block_versions (block_type, updated_at DESC, block_ref DESC);

INSERT INTO app.canonical_document_versions (
    doc_id,
    version,
    source_path,
    file_type,
    metadata_profile,
    structure_tree,
    extracted_tables,
    section_summaries,
    quality_flags,
    payload,
    created_at,
    updated_at
)
SELECT
    doc_id,
    version,
    source_path,
    file_type,
    metadata_profile,
    structure_tree,
    extracted_tables,
    section_summaries,
    quality_flags,
    payload,
    created_at,
    updated_at
FROM app.canonical_documents
ON CONFLICT (doc_id, version) DO NOTHING;

INSERT INTO app.knowledge_block_versions (
    block_ref,
    doc_id,
    version,
    block_id,
    block_type,
    text,
    heading_path,
    metadata,
    created_at,
    updated_at
)
SELECT
    block_ref,
    doc_id,
    version,
    block_id,
    block_type,
    text,
    heading_path,
    metadata,
    created_at,
    updated_at
FROM app.knowledge_blocks
ON CONFLICT (block_ref) DO NOTHING;
