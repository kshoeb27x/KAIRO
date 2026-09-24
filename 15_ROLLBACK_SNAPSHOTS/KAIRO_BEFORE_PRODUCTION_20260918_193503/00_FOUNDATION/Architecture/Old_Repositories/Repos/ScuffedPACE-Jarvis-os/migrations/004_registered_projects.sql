-- Schema version 4: owner-registered local project directories that JARVIS
-- may inspect read-only. The stored profile is a bounded, non-sensitive
-- summary produced by the scanner (never raw file contents of secrets).

CREATE TABLE registered_projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  root_path TEXT NOT NULL UNIQUE,
  profile_json TEXT NOT NULL DEFAULT '{}',
  last_inspected_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT
);

CREATE INDEX idx_registered_projects_active ON registered_projects(archived_at, name);
