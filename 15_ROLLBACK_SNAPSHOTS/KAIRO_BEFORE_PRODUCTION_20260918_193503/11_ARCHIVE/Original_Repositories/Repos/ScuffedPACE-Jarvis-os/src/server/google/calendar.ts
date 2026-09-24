import type { GoogleAuthManager } from './oauth';
import { GoogleAuthError } from './oauth';

/**
 * Minimal Google Calendar REST client (official API, native fetch). Reads
 * are bounded; writes exist only as functions the approval-gated executors
 * call after an explicit owner decision.
 */

const BASE = 'https://www.googleapis.com/calendar/v3';

export interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  allDay: boolean;
  location: string | null;
  attendees: number;
  status: string;
  organizerSelf: boolean;
}

export class CalendarError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CalendarError';
  }
}

interface RawEvent {
  id: string;
  summary?: string;
  status?: string;
  location?: string;
  start?: { dateTime?: string; date?: string };
  end?: { dateTime?: string; date?: string };
  attendees?: Array<{ email?: string; self?: boolean; responseStatus?: string }>;
  organizer?: { self?: boolean };
}

export class CalendarClient {
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
      throw new CalendarError(`Calendar returned an error (HTTP ${response.status}).`);
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  }

  async listEvents(options: { fromIso: string; toIso: string; query?: string }): Promise<CalendarEvent[]> {
    const params = new URLSearchParams({
      timeMin: options.fromIso,
      timeMax: options.toIso,
      singleEvents: 'true',
      orderBy: 'startTime',
      maxResults: '50',
    });
    if (options.query) params.set('q', options.query.slice(0, 200));
    const body = await this.call<{ items?: RawEvent[] }>(
      `${BASE}/calendars/primary/events?${params.toString()}`,
    );
    return (body.items ?? []).filter((e) => e.status !== 'cancelled').map(toEvent);
  }

  /** Executor-only. */
  async createEvent(input: {
    summary: string;
    startIso: string;
    endIso: string;
    location?: string;
    attendees?: string[];
    description?: string;
  }): Promise<{ id: string }> {
    return await this.call<{ id: string }>(`${BASE}/calendars/primary/events?sendUpdates=all`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        summary: input.summary,
        location: input.location,
        description: input.description,
        start: { dateTime: input.startIso },
        end: { dateTime: input.endIso },
        attendees: (input.attendees ?? []).map((email) => ({ email })),
      }),
    });
  }

  /** Executor-only. */
  async updateEvent(
    eventId: string,
    patch: { summary?: string; startIso?: string; endIso?: string; location?: string },
  ): Promise<void> {
    const body: Record<string, unknown> = {};
    if (patch.summary) body.summary = patch.summary;
    if (patch.location !== undefined) body.location = patch.location;
    if (patch.startIso) body.start = { dateTime: patch.startIso };
    if (patch.endIso) body.end = { dateTime: patch.endIso };
    await this.call(
      `${BASE}/calendars/primary/events/${encodeURIComponent(eventId)}?sendUpdates=all`,
      {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      },
    );
  }

  /** Executor-only. */
  async deleteEvent(eventId: string): Promise<void> {
    await this.call(
      `${BASE}/calendars/primary/events/${encodeURIComponent(eventId)}?sendUpdates=all`,
      { method: 'DELETE' },
    );
  }

  /** Executor-only: responds to an invitation as the signed-in account. */
  async respondToEvent(eventId: string, response: 'accepted' | 'declined' | 'tentative'): Promise<void> {
    const event = await this.call<RawEvent>(
      `${BASE}/calendars/primary/events/${encodeURIComponent(eventId)}`,
    );
    const attendees = (event.attendees ?? []).map((a) =>
      a.self ? { ...a, responseStatus: response } : a,
    );
    await this.call(
      `${BASE}/calendars/primary/events/${encodeURIComponent(eventId)}?sendUpdates=all`,
      {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ attendees }),
      },
    );
  }
}

function toEvent(raw: RawEvent): CalendarEvent {
  const start = raw.start?.dateTime ?? raw.start?.date ?? '';
  const end = raw.end?.dateTime ?? raw.end?.date ?? '';
  return {
    id: raw.id,
    summary: raw.summary ?? '(no title)',
    start,
    end,
    allDay: Boolean(raw.start?.date),
    location: raw.location ?? null,
    attendees: raw.attendees?.length ?? 0,
    status: raw.status ?? 'confirmed',
    organizerSelf: raw.organizer?.self ?? false,
  };
}

/** Overlapping timed events (deterministic, tested). */
export function findConflicts(events: CalendarEvent[]): Array<[CalendarEvent, CalendarEvent]> {
  const timed = events
    .filter((e) => !e.allDay)
    .sort((a, b) => a.start.localeCompare(b.start));
  const conflicts: Array<[CalendarEvent, CalendarEvent]> = [];
  for (let i = 0; i < timed.length; i += 1) {
    for (let j = i + 1; j < timed.length; j += 1) {
      if (timed[j]!.start < timed[i]!.end) conflicts.push([timed[i]!, timed[j]!]);
      else break;
    }
  }
  return conflicts;
}

/** Free gaps of at least `minMinutes` between events within a window. */
export function suggestFreeSlots(
  events: CalendarEvent[],
  windowStartIso: string,
  windowEndIso: string,
  minMinutes = 30,
): Array<{ startIso: string; endIso: string }> {
  const timed = events
    .filter((e) => !e.allDay)
    .map((e) => ({ start: Date.parse(e.start), end: Date.parse(e.end) }))
    .filter((e) => Number.isFinite(e.start) && Number.isFinite(e.end))
    .sort((a, b) => a.start - b.start);
  const windowStart = Date.parse(windowStartIso);
  const windowEnd = Date.parse(windowEndIso);
  const slots: Array<{ startIso: string; endIso: string }> = [];
  let cursor = windowStart;
  for (const event of timed) {
    if (event.start > cursor && event.start - cursor >= minMinutes * 60 * 1000) {
      slots.push({
        startIso: new Date(cursor).toISOString(),
        endIso: new Date(Math.min(event.start, windowEnd)).toISOString(),
      });
    }
    cursor = Math.max(cursor, event.end);
    if (cursor >= windowEnd) break;
  }
  if (windowEnd - cursor >= minMinutes * 60 * 1000) {
    slots.push({
      startIso: new Date(cursor).toISOString(),
      endIso: new Date(windowEnd).toISOString(),
    });
  }
  return slots.slice(0, 10);
}
