import type Database from 'better-sqlite3';
import { createProjectsRepository } from './projects';
import { createConversationsRepository } from './conversations';
import { createMemoriesRepository } from './memories';
import { createPendingActionsRepository } from './pendingActions';
import { createActivityEventsRepository } from './activityEvents';
import { createSettingsRepository } from './settings';
import { createRegisteredProjectsRepository } from './registeredProjects';

export function createRepositories(db: Database.Database) {
  return {
    projects: createProjectsRepository(db),
    conversations: createConversationsRepository(db),
    memories: createMemoriesRepository(db),
    pendingActions: createPendingActionsRepository(db),
    activityEvents: createActivityEventsRepository(db),
    settings: createSettingsRepository(db),
    registeredProjects: createRegisteredProjectsRepository(db),
  };
}

export type Repositories = ReturnType<typeof createRepositories>;
