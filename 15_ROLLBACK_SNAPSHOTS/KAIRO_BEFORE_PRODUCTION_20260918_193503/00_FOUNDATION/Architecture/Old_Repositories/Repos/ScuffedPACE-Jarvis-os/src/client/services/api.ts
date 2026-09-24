import { activityEventSchema, type ActivityEvent } from '../../shared/schemas/activity';
import {
  bootstrapResponseSchema,
  type BootstrapResponse,
} from '../../shared/contracts/api';
import type { Memory, PendingAction, Settings } from '../../shared/types';

export class ApiRequestError extends Error {
  readonly code: string;
  readonly status: number;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = code;
  }
}

async function parseFailure(response: Response): Promise<never> {
  let code = 'request_failed';
  let message = `Request failed (${response.status})`;
  try {
    const body = (await response.json()) as { error?: { code?: string; message?: string } };
    if (body.error?.message) {
      code = body.error.code ?? code;
      message = body.error.message;
    }
  } catch {
    // keep defaults
  }
  throw new ApiRequestError(response.status, code, message);
}

export async function fetchBootstrap(): Promise<BootstrapResponse> {
  const response = await fetch('/api/bootstrap');
  if (!response.ok) await parseFailure(response);
  return bootstrapResponseSchema.parse(await response.json());
}

/**
 * Streams NDJSON activity events. Each line is validated against the shared
 * envelope schema before it reaches the UI.
 */
export async function streamAssistant(
  input: string,
  conversationId: string | undefined,
  onEvent: (event: ActivityEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/assistant/stream', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ input, conversationId }),
    signal,
  });
  if (!response.ok || !response.body) await parseFailure(response);

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.trim().length === 0) continue;
      onEvent(activityEventSchema.parse(JSON.parse(line)));
    }
  }
  if (buffer.trim().length > 0) {
    onEvent(activityEventSchema.parse(JSON.parse(buffer)));
  }
}

export async function decideAction(
  actionId: string,
  decision: 'approve' | 'cancel',
): Promise<PendingAction> {
  const response = await fetch(`/api/actions/${actionId}/decision`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ decision }),
  });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { action: PendingAction };
  return body.action;
}

export async function listMemories(query?: string): Promise<Memory[]> {
  const url = query ? `/api/memories?q=${encodeURIComponent(query)}` : '/api/memories';
  const response = await fetch(url);
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { memories: Memory[] };
  return body.memories;
}

export async function createMemory(payload: {
  kind: Memory['kind'];
  value: string;
  confirmSensitive?: boolean;
  allowDuplicate?: boolean;
}): Promise<Memory> {
  const response = await fetch('/api/memories', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { memory: Memory };
  return body.memory;
}

export async function updateMemory(
  id: string,
  patch: { value?: string; kind?: Memory['kind']; tags?: string[] },
): Promise<Memory> {
  const response = await fetch(`/api/memories/${id}`, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { memory: Memory };
  return body.memory;
}

export async function archiveMemory(id: string): Promise<Memory> {
  const response = await fetch(`/api/memories/${id}`, { method: 'DELETE' });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { memory: Memory };
  return body.memory;
}

export interface RegisteredProject {
  id: string;
  name: string;
  rootPath: string;
  lastInspectedAt: string | null;
  archivedAt: string | null;
  profile: {
    projectType: string;
    languages: string[];
    fileCount: number;
    description: string;
    hasTests: boolean;
    hasReadme: boolean;
    git: { isRepo: boolean; branch: string | null; dirtyFiles: number | null };
    health: { level: 'good' | 'attention' | 'unknown'; notes: string[] };
  } | null;
}

export async function listRegisteredProjects(): Promise<RegisteredProject[]> {
  const response = await fetch('/api/projects/registered');
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { projects: RegisteredProject[] };
  return body.projects;
}

export async function registerProject(path: string, name?: string): Promise<RegisteredProject> {
  const response = await fetch('/api/projects/register', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ path, name }),
  });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { project: RegisteredProject };
  return body.project;
}

export async function refreshRegisteredProject(id: string): Promise<RegisteredProject> {
  const response = await fetch(`/api/projects/registered/${id}/refresh`, { method: 'POST' });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { project: RegisteredProject };
  return body.project;
}

export async function unregisterProject(id: string): Promise<void> {
  const response = await fetch(`/api/projects/registered/${id}`, { method: 'DELETE' });
  if (!response.ok) await parseFailure(response);
}

export async function updateSettings(partial: Partial<Settings>): Promise<Settings> {
  const response = await fetch('/api/settings', {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(partial),
  });
  if (!response.ok) await parseFailure(response);
  const body = (await response.json()) as { settings: Settings };
  return body.settings;
}
