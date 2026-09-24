-- Schema version 2: expanded memory categories and provenance.
-- SQLite cannot alter CHECK constraints, so the memories table is rebuilt
-- in place. All existing rows are preserved; existing kind/source values
-- remain valid members of the expanded sets.

CREATE TABLE memories_v2 (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN (
    'preference', 'personal_fact', 'project_fact', 'fact', 'decision',
    'task', 'lesson', 'working_context', 'note'
  )),
  memory_key TEXT,
  value TEXT NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '[]',
  source TEXT NOT NULL DEFAULT 'user_explicit' CHECK (source IN (
    'user_explicit', 'owner_confirmed', 'model_inferred', 'integration', 'seed'
  )),
  source_detail TEXT,
  sensitive INTEGER NOT NULL DEFAULT 0 CHECK (sensitive IN (0, 1)),
  project_id TEXT REFERENCES projects(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT
);

INSERT INTO memories_v2 (
  id, kind, memory_key, value, tags_json, source,
  project_id, created_at, updated_at, archived_at
)
SELECT
  id, kind, memory_key, value, tags_json, source,
  project_id, created_at, updated_at, archived_at
FROM memories;

DROP TABLE memories;
ALTER TABLE memories_v2 RENAME TO memories;
CREATE INDEX idx_memories_active ON memories(archived_at, kind);
