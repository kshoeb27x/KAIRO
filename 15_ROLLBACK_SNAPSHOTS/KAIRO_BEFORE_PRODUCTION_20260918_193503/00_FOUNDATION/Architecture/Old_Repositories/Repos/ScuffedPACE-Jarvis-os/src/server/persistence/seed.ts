import type { Repositories } from '../repositories';

/**
 * Fixed id so seeding is idempotent: if the project exists — even archived —
 * it is never recreated. Only the minimum demo records are seeded.
 */
export const SEED_PROJECT_ID = '6f1e2a3b-0c4d-4e5f-8a6b-7c8d9e0f1a2b';

export const SEED_PROJECT_SUMMARY =
  'Voice-first personal AI command center MVP: visual shell with animated neural sphere, ' +
  'push-to-talk voice loop, deterministic router, honest activity feed, local SQLite memory, ' +
  'and one mocked mail workflow with server-enforced approval.';

export function seedDatabase(repos: Repositories): { seededProject: boolean } {
  const existing = repos.projects.findById(SEED_PROJECT_ID);
  if (existing) {
    return { seededProject: false };
  }
  repos.projects.create({
    id: SEED_PROJECT_ID,
    name: 'JARVIS OS',
    summary: SEED_PROJECT_SUMMARY,
    isActive: true,
  });
  return { seededProject: true };
}
