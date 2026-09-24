# Backup and Restore

Your entire JARVIS state (conversations, memories, actions, settings,
registered projects) lives in `.data/jarvis.db`. Google tokens live next to
it in `.data/google-tokens.json` (not included in database backups; you can
simply reconnect after a restore).

## Backup

```sh
npm run jarvis:stop
npm run backup -- --output backups/2026-07-14
```

Uses SQLite's online backup API and writes a manifest (app version, schema
version, creation time, per-table counts, sha256 checksum). The `backups/`
folder is gitignored — copy it to external storage for real safety.

## Restore

```sh
npm run jarvis:stop
npm run restore -- --input backups/2026-07-14          # into an empty .data
npm run restore -- --input backups/2026-07-14 --force  # replace existing data
```

Restore validates the manifest and checksum, refuses unsupported schema
versions, refuses to overwrite without `--force`, and always takes a
pre-restore backup before replacing anything. Older-schema backups are
upgraded automatically by migrations at the next start (a pre-migration
backup of your v1 data exists at `backups/pre-schema-v2` from the upgrade).

## Export / delete everything

- Export: a backup folder *is* the export (open `jarvis.db` with any SQLite
  tool).
- Delete: stop JARVIS and delete `.data`. Disconnect Google first if you
  also want the grant revoked (Settings panel).
