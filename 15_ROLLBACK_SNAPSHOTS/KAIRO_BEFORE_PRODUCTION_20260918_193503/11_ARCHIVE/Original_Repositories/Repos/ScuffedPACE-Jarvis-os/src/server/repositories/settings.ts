import type Database from 'better-sqlite3';
import type { Settings } from '../../shared/types';
import { defaultSettings, settingsSchema } from '../../shared/schemas/entities';
import { nowIso } from '../persistence/db';

export function createSettingsRepository(db: Database.Database) {
  return {
    get(): Settings {
      const rows = db.prepare('SELECT key, value_json FROM settings').all() as Array<{
        key: string;
        value_json: string;
      }>;
      const raw: Record<string, unknown> = {};
      for (const row of rows) {
        raw[row.key] = JSON.parse(row.value_json);
      }
      const parsed = settingsSchema.safeParse({ ...defaultSettings, ...raw });
      return parsed.success ? parsed.data : defaultSettings;
    },

    update(partial: Partial<Settings>): Settings {
      const now = nowIso();
      const stmt = db.prepare(
        `INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)
         ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at`,
      );
      const write = db.transaction(() => {
        for (const [key, value] of Object.entries(partial)) {
          if (value === undefined) continue;
          stmt.run(key, JSON.stringify(value), now);
        }
      });
      write();
      return this.get();
    },
  };
}

export type SettingsRepository = ReturnType<typeof createSettingsRepository>;
