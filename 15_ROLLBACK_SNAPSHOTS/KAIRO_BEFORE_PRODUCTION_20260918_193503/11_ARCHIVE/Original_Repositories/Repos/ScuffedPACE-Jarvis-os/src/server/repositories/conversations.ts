import { randomUUID } from 'node:crypto';
import type Database from 'better-sqlite3';
import type { Conversation, Message, MessageRole } from '../../shared/types';
import { nowIso } from '../persistence/db';

interface ConversationRow {
  id: string;
  project_id: string | null;
  title: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

interface MessageRow {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  provider: string | null;
  model: string | null;
  created_at: string;
}

function toConversation(row: ConversationRow): Conversation {
  return {
    id: row.id,
    projectId: row.project_id,
    title: row.title,
    summary: row.summary,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    archivedAt: row.archived_at,
  };
}

function toMessage(row: MessageRow): Message {
  return {
    id: row.id,
    conversationId: row.conversation_id,
    role: row.role as MessageRole,
    content: row.content,
    provider: row.provider,
    model: row.model,
    createdAt: row.created_at,
  };
}

export function createConversationsRepository(db: Database.Database) {
  return {
    findById(id: string): Conversation | null {
      const row = db.prepare('SELECT * FROM conversations WHERE id = ?').get(id) as
        | ConversationRow
        | undefined;
      return row ? toConversation(row) : null;
    },

    findMostRecent(): Conversation | null {
      const row = db
        .prepare(
          'SELECT * FROM conversations WHERE archived_at IS NULL ORDER BY updated_at DESC LIMIT 1',
        )
        .get() as ConversationRow | undefined;
      return row ? toConversation(row) : null;
    },

    create(input: { projectId: string | null; title: string }): Conversation {
      const now = nowIso();
      const conversation: Conversation = {
        id: randomUUID(),
        projectId: input.projectId,
        title: input.title,
        summary: null,
        createdAt: now,
        updatedAt: now,
        archivedAt: null,
      };
      db.prepare(
        `INSERT INTO conversations (id, project_id, title, summary, created_at, updated_at, archived_at)
         VALUES (?, ?, ?, NULL, ?, ?, NULL)`,
      ).run(conversation.id, conversation.projectId, conversation.title, now, now);
      return conversation;
    },

    touch(id: string): void {
      db.prepare('UPDATE conversations SET updated_at = ? WHERE id = ?').run(nowIso(), id);
    },

    addMessage(input: {
      conversationId: string;
      role: MessageRole;
      content: string;
      provider?: string | null;
      model?: string | null;
    }): Message {
      const now = nowIso();
      const message: Message = {
        id: randomUUID(),
        conversationId: input.conversationId,
        role: input.role,
        content: input.content,
        provider: input.provider ?? null,
        model: input.model ?? null,
        createdAt: now,
      };
      db.prepare(
        `INSERT INTO messages (id, conversation_id, role, content, provider, model, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      ).run(
        message.id,
        message.conversationId,
        message.role,
        message.content,
        message.provider,
        message.model,
        now,
      );
      this.touch(input.conversationId);
      return message;
    },

    listMessages(conversationId: string, limit = 200): Message[] {
      const rows = db
        .prepare(
          `SELECT * FROM (
             SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC, id DESC LIMIT ?
           ) ORDER BY created_at ASC, id ASC`,
        )
        .all(conversationId, limit) as MessageRow[];
      return rows.map(toMessage);
    },
  };
}

export type ConversationsRepository = ReturnType<typeof createConversationsRepository>;
