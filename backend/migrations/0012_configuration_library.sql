CREATE TABLE IF NOT EXISTS app.configuration_library (
    config_id TEXT NOT NULL,
    version TEXT NOT NULL,
    config_type TEXT NOT NULL DEFAULT 'generic',
    title TEXT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (config_id, version)
);

CREATE INDEX IF NOT EXISTS ix_configuration_library_updated_at
    ON app.configuration_library (updated_at DESC, config_id DESC, version DESC);

CREATE INDEX IF NOT EXISTS ix_configuration_library_type_updated_at
    ON app.configuration_library (config_type, updated_at DESC, config_id DESC, version DESC);

CREATE INDEX IF NOT EXISTS ix_configuration_library_tags
    ON app.configuration_library USING GIN (tags);
