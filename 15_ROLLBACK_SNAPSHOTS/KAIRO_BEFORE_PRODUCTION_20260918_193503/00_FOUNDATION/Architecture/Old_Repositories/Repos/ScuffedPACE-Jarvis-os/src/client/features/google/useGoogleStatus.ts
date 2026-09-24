import { useCallback, useEffect, useState } from 'react';

export interface GoogleStatus {
  configured: boolean;
  connected: boolean;
  accountEmail: string | null;
  scopes: string[];
  actionsEnabled: boolean;
  setupMessage: string | null;
}

/** Shared Google connection state + connect/disconnect actions for panels. */
export function useGoogleStatus() {
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback((): void => {
    fetch('/api/google/status')
      .then(async (r) => (r.ok ? ((await r.json()) as GoogleStatus) : null))
      .then((s) => setStatus(s))
      .catch(() => setError('Could not load the Google connection state.'));
  }, []);

  useEffect(refresh, [refresh]);

  const connect = useCallback(
    async (tier: 'read' | 'actions'): Promise<void> => {
      setError(null);
      const response = await fetch('/api/google/connect', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ tier }),
      });
      const body = (await response.json()) as { authUrl?: string; error?: { message?: string } };
      if (!response.ok || !body.authUrl) {
        setError(body.error?.message ?? 'Could not start the Google sign-in.');
        return;
      }
      window.open(body.authUrl, '_blank', 'noopener');
    },
    [],
  );

  const disconnect = useCallback(async (): Promise<void> => {
    await fetch('/api/google/disconnect', { method: 'POST' });
    refresh();
  }, [refresh]);

  return { status, error, refresh, connect, disconnect };
}
