MIGRATION_SQL = """
-- 001_create_incidents_table.sql
-- Implements mandatory RCA enforcement at the database level.

DO $$ BEGIN
    CREATE TYPE rca_category AS ENUM (
        'code_deploy', 'config_change', 'dependency_failure',
        'resource_exhaustion', 'human_error', 'external_outage',
        'security_incident', 'unknown'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE incident_state AS ENUM ('OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE severity AS ENUM ('P0', 'P1', 'P2', 'P3');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    source          VARCHAR(128) NOT NULL,

    -- RCA enforcement: NOT NULL constraints mean the DB rejects
    -- any row without these fields — last-resort defense after
    -- the service-layer RcaPolicy check.
    root_cause      TEXT NOT NULL,
    rca_category    rca_category NOT NULL,
    rca_description TEXT NOT NULL,
    rca_verified_by VARCHAR(128),
    state           incident_state NOT NULL DEFAULT 'OPEN',
    severity        severity NOT NULL DEFAULT 'P2',
    component       VARCHAR(128) NOT NULL DEFAULT 'unknown',
    first_signal_at TIMESTAMPTZ,
    rca_submitted_at TIMESTAMPTZ,
    mttr_seconds    INTEGER,

    hash            VARCHAR(64) NOT NULL UNIQUE,
    metadata        JSONB DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_hash
    ON incidents(hash);

CREATE INDEX IF NOT EXISTS idx_incidents_rca_category
    ON incidents(rca_category);

CREATE INDEX IF NOT EXISTS idx_incidents_created_at
    ON incidents(created_at DESC);
"""

ROLLBACK_SQL = """
-- 001_rollback_create_incidents_table.sql

DROP TABLE IF EXISTS incidents;
DROP TYPE IF EXISTS incident_state;
DROP TYPE IF EXISTS severity;
DROP TYPE IF EXISTS rca_category;
"""
