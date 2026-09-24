import type { GoogleAuthManager } from './oauth';
import { GoogleAuthError } from './oauth';
import { boundText, htmlToText } from './sanitize';

/**
 * Minimal Gmail REST client (official API, native fetch, no SDK). Reads are
 * bounded and sanitized; writes exist only as functions the approval-gated
 * executors call — nothing here is reachable without an approved action.
 */

const BASE = 'https://gmail.googleapis.com/gmail/v1/users/me';

export interface MailSummary {
  id: string;
  threadId: string;
  from: string;
  subject: string;
  date: string;
  snippet: string;
  unread: boolean;
}

export interface MailBody extends MailSummary {
  to: string;
  text: string;
}

export class GmailError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GmailError';
  }
}

interface GmailMessageMeta {
  id: string;
  threadId: string;
  snippet?: string;
  labelIds?: string[];
  payload?: GmailPart;
}

interface GmailPart {
  mimeType?: string;
  headers?: Array<{ name: string; value: string }>;
  body?: { data?: string; size?: number };
  parts?: GmailPart[];
}

export class GmailClient {
  constructor(
    private readonly auth: GoogleAuthManager,
    private readonly fetchFn: typeof fetch = fetch,
  ) {}

  private async call<T>(url: string, init: RequestInit = {}): Promise<T> {
    const token = await this.auth.getAccessToken();
    const response = await this.fetchFn(url, {
      ...init,
      headers: { ...init.headers, authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(20000),
    });
    if (response.status === 401 || response.status === 403) {
      throw new GoogleAuthError(
        'Google rejected the request — the connection may lack the needed permission tier.',
      );
    }
    if (!response.ok) {
      throw new GmailError(`Gmail returned an error (HTTP ${response.status}).`);
    }
    return (await response.json()) as T;
  }

  async listMessages(options: { query?: string; limit?: number } = {}): Promise<MailSummary[]> {
    const limit = Math.min(Math.max(options.limit ?? 15, 1), 25);
    const params = new URLSearchParams({ maxResults: String(limit) });
    if (options.query) params.set('q', options.query.slice(0, 300));
    const list = await this.call<{ messages?: Array<{ id: string }> }>(
      `${BASE}/messages?${params.toString()}`,
    );
    const ids = (list.messages ?? []).map((m) => m.id);
    const summaries: MailSummary[] = [];
    for (const id of ids) {
      const meta = await this.call<GmailMessageMeta>(
        `${BASE}/messages/${id}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date`,
      );
      summaries.push(toSummary(meta));
    }
    return summaries;
  }

  async getMessage(id: string): Promise<MailBody> {
    const message = await this.call<GmailMessageMeta>(
      `${BASE}/messages/${encodeURIComponent(id)}?format=full`,
    );
    const summary = toSummary(message);
    return {
      ...summary,
      to: header(message.payload, 'To'),
      text: boundText(extractText(message.payload)),
    };
  }

  /** Executor-only: sends an RFC 2822 message. */
  async sendMessage(input: {
    to: string;
    subject: string;
    body: string;
    inReplyToMessageId?: string;
    threadId?: string;
  }): Promise<{ id: string }> {
    let references = '';
    if (input.inReplyToMessageId) {
      try {
        const original = await this.call<GmailMessageMeta>(
          `${BASE}/messages/${encodeURIComponent(input.inReplyToMessageId)}?format=metadata&metadataHeaders=Message-ID`,
        );
        const messageId = header(original.payload, 'Message-ID');
        if (messageId) references = `In-Reply-To: ${messageId}\r\nReferences: ${messageId}\r\n`;
      } catch {
        // Reply threading is best-effort; the send itself remains explicit.
      }
    }
    const raw = [
      `To: ${input.to}`,
      `Subject: ${encodeHeader(input.subject)}`,
      'MIME-Version: 1.0',
      'Content-Type: text/plain; charset=UTF-8',
      references.trimEnd(),
      '',
      input.body,
    ]
      .filter((line) => line !== '')
      .join('\r\n')
      .replace('Content-Type: text/plain; charset=UTF-8\r\n', 'Content-Type: text/plain; charset=UTF-8\r\n\r\n');
    const encoded = Buffer.from(raw, 'utf8')
      .toString('base64')
      .replaceAll('+', '-')
      .replaceAll('/', '_')
      .replace(/=+$/, '');
    return await this.call<{ id: string }>(`${BASE}/messages/send`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ raw: encoded, threadId: input.threadId }),
    });
  }

  /** Executor-only: archive = remove from INBOX (never deletes). */
  async archiveMessage(id: string): Promise<void> {
    await this.call(`${BASE}/messages/${encodeURIComponent(id)}/modify`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ removeLabelIds: ['INBOX'] }),
    });
  }

  /** Executor-only: moves to trash (recoverable in Gmail for ~30 days). */
  async trashMessage(id: string): Promise<void> {
    await this.call(`${BASE}/messages/${encodeURIComponent(id)}/trash`, { method: 'POST' });
  }
}

function toSummary(message: GmailMessageMeta): MailSummary {
  return {
    id: message.id,
    threadId: message.threadId,
    from: header(message.payload, 'From'),
    subject: header(message.payload, 'Subject') || '(no subject)',
    date: header(message.payload, 'Date'),
    snippet: message.snippet ?? '',
    unread: message.labelIds?.includes('UNREAD') ?? false,
  };
}

function header(payload: GmailPart | undefined, name: string): string {
  return (
    payload?.headers?.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value ?? ''
  );
}

function decodeBody(data: string | undefined): string {
  if (!data) return '';
  return Buffer.from(data.replaceAll('-', '+').replaceAll('_', '/'), 'base64').toString('utf8');
}

/** Prefers text/plain; falls back to stripped text/html. Bounded upstream. */
export function extractText(payload: GmailPart | undefined): string {
  if (!payload) return '';
  if (payload.mimeType === 'text/plain' && payload.body?.data) {
    return decodeBody(payload.body.data);
  }
  if (payload.mimeType === 'text/html' && payload.body?.data) {
    return htmlToText(decodeBody(payload.body.data));
  }
  for (const part of payload.parts ?? []) {
    const text = extractText(part);
    if (text) return text;
  }
  return '';
}

function encodeHeader(value: string): string {
  return /^[\x20-\x7e]*$/.test(value)
    ? value
    : `=?UTF-8?B?${Buffer.from(value, 'utf8').toString('base64')}?=`;
}
