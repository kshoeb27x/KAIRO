import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Google OAuth for a local desktop app: official loopback-redirect flow with
 * PKCE. Least privilege in tiers — "read" connects Gmail/Calendar read-only;
 * "actions" is a separate, explicit upgrade adding send/modify scopes.
 * Tokens live in a file inside the gitignored data directory, never in git
 * and never exposed through any API response.
 */

export const READ_SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.readonly',
  'https://www.googleapis.com/auth/userinfo.email',
];

export const ACTION_SCOPES = [
  ...READ_SCOPES,
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/calendar.events',
];

const AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth';
const TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token';
const REVOKE_ENDPOINT = 'https://oauth2.googleapis.com/revoke';
const USERINFO_ENDPOINT = 'https://openidconnect.googleapis.com/v1/userinfo';

export interface StoredTokens {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: string;
  scopes: string[];
  accountEmail: string | null;
  obtainedAt: string;
}

export interface GoogleAuthStatus {
  configured: boolean;
  connected: boolean;
  accountEmail: string | null;
  scopes: string[];
  actionsEnabled: boolean;
  setupMessage: string | null;
}

export class GoogleAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'GoogleAuthError';
  }
}

interface PendingAuth {
  state: string;
  verifier: string;
  scopes: string[];
  createdAt: number;
}

export class GoogleAuthManager {
  private readonly tokenFile: string;
  private pending: PendingAuth | null = null;
  private readonly fetchFn: typeof fetch;

  constructor(
    private readonly clientId: string | null,
    private readonly clientSecret: string | null,
    dataDir: string,
    private readonly redirectUri: string,
    fetchFn: typeof fetch = fetch,
  ) {
    this.tokenFile = path.join(dataDir, 'google-tokens.json');
    this.fetchFn = fetchFn;
  }

  configured(): boolean {
    return Boolean(this.clientId && this.clientSecret);
  }

  readTokens(): StoredTokens | null {
    try {
      const raw = JSON.parse(fs.readFileSync(this.tokenFile, 'utf8')) as StoredTokens;
      return typeof raw.accessToken === 'string' ? raw : null;
    } catch {
      return null;
    }
  }

  private writeTokens(tokens: StoredTokens): void {
    fs.mkdirSync(path.dirname(this.tokenFile), { recursive: true });
    fs.writeFileSync(this.tokenFile, JSON.stringify(tokens, null, 2));
  }

  status(): GoogleAuthStatus {
    if (!this.configured()) {
      return {
        configured: false,
        connected: false,
        accountEmail: null,
        scopes: [],
        actionsEnabled: false,
        setupMessage:
          'Google is not configured. Create an OAuth "Desktop app" client in Google Cloud Console, ' +
          'enable the Gmail and Calendar APIs, then set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env ' +
          '(see docs/INTEGRATIONS.md) and restart JARVIS.',
      };
    }
    const tokens = this.readTokens();
    if (!tokens) {
      return {
        configured: true,
        connected: false,
        accountEmail: null,
        scopes: [],
        actionsEnabled: false,
        setupMessage: 'Not connected. Use "Connect Google" to authorize read-only access.',
      };
    }
    return {
      configured: true,
      connected: true,
      accountEmail: tokens.accountEmail,
      scopes: tokens.scopes,
      actionsEnabled: ACTION_SCOPES.every((s) => tokens.scopes.includes(s)),
      setupMessage: null,
    };
  }

  /** Begins the loopback OAuth flow; returns the URL the owner must open. */
  startAuth(tier: 'read' | 'actions'): string {
    if (!this.configured()) {
      throw new GoogleAuthError('GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set.');
    }
    const scopes = tier === 'actions' ? ACTION_SCOPES : READ_SCOPES;
    const verifier = base64url(crypto.randomBytes(48));
    const state = base64url(crypto.randomBytes(24));
    this.pending = { state, verifier, scopes, createdAt: Date.now() };
    const challenge = base64url(crypto.createHash('sha256').update(verifier).digest());
    const params = new URLSearchParams({
      client_id: this.clientId!,
      redirect_uri: this.redirectUri,
      response_type: 'code',
      scope: scopes.join(' '),
      access_type: 'offline',
      prompt: 'consent',
      state,
      code_challenge: challenge,
      code_challenge_method: 'S256',
    });
    return `${AUTH_ENDPOINT}?${params.toString()}`;
  }

  /** Handles the loopback redirect: exchanges the code and stores tokens. */
  async completeAuth(code: string, state: string): Promise<StoredTokens> {
    const pending = this.pending;
    if (!pending || pending.state !== state || Date.now() - pending.createdAt > 10 * 60 * 1000) {
      throw new GoogleAuthError('The sign-in attempt is unknown or expired. Start again.');
    }
    this.pending = null;
    const response = await this.fetchFn(TOKEN_ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: this.clientId!,
        client_secret: this.clientSecret!,
        code,
        code_verifier: pending.verifier,
        grant_type: 'authorization_code',
        redirect_uri: this.redirectUri,
      }),
    });
    if (!response.ok) {
      throw new GoogleAuthError('Google rejected the sign-in code. Try connecting again.');
    }
    const body = (await response.json()) as {
      access_token: string;
      refresh_token?: string;
      expires_in: number;
      scope?: string;
    };
    const tokens: StoredTokens = {
      accessToken: body.access_token,
      refreshToken: body.refresh_token ?? this.readTokens()?.refreshToken ?? null,
      expiresAt: new Date(Date.now() + (body.expires_in - 60) * 1000).toISOString(),
      scopes: body.scope ? body.scope.split(' ') : pending.scopes,
      accountEmail: null,
      obtainedAt: new Date().toISOString(),
    };
    tokens.accountEmail = await this.fetchAccountEmail(tokens.accessToken);
    this.writeTokens(tokens);
    return tokens;
  }

  private async fetchAccountEmail(accessToken: string): Promise<string | null> {
    try {
      const response = await this.fetchFn(USERINFO_ENDPOINT, {
        headers: { authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) return null;
      const info = (await response.json()) as { email?: string };
      return info.email ?? null;
    } catch {
      return null;
    }
  }

  /** Returns a valid access token, refreshing when expired. */
  async getAccessToken(): Promise<string> {
    const tokens = this.readTokens();
    if (!tokens) throw new GoogleAuthError('Google is not connected.');
    if (new Date(tokens.expiresAt).getTime() > Date.now()) return tokens.accessToken;
    if (!tokens.refreshToken) {
      throw new GoogleAuthError('The Google session expired. Connect again.');
    }
    const response = await this.fetchFn(TOKEN_ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: this.clientId!,
        client_secret: this.clientSecret!,
        refresh_token: tokens.refreshToken,
        grant_type: 'refresh_token',
      }),
    });
    if (!response.ok) {
      throw new GoogleAuthError('Google session refresh failed. Connect again.');
    }
    const body = (await response.json()) as { access_token: string; expires_in: number };
    const updated: StoredTokens = {
      ...tokens,
      accessToken: body.access_token,
      expiresAt: new Date(Date.now() + (body.expires_in - 60) * 1000).toISOString(),
    };
    this.writeTokens(updated);
    return updated.accessToken;
  }

  /** Revokes at Google and deletes the local token file. */
  async disconnect(): Promise<void> {
    const tokens = this.readTokens();
    if (tokens) {
      const target = tokens.refreshToken ?? tokens.accessToken;
      try {
        await this.fetchFn(`${REVOKE_ENDPOINT}?token=${encodeURIComponent(target)}`, {
          method: 'POST',
        });
      } catch {
        // Revocation is best-effort; the local copy is removed regardless.
      }
    }
    fs.rmSync(this.tokenFile, { force: true });
  }
}

function base64url(buffer: Buffer): string {
  return buffer.toString('base64').replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}
