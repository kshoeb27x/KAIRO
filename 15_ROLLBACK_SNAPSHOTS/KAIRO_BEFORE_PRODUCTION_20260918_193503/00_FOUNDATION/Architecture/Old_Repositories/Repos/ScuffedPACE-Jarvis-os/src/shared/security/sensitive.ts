/**
 * Deterministic detector for content that should never be stored silently.
 * Used by the memory system to require explicit owner confirmation before
 * persisting anything that looks like a credential, financial identifier, or
 * government ID. Errs on the side of asking — a false positive only costs one
 * confirmation click.
 */

export interface SensitiveMatch {
  /** Short human-readable reason shown to the owner. */
  reason: string;
}

const PATTERNS: Array<{ pattern: RegExp; reason: string }> = [
  {
    pattern: /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
    reason: 'it contains a private key',
  },
  {
    pattern: /\b(sk|pk|ghp|gho|xox[bap])[-_][A-Za-z0-9_-]{10,}/,
    reason: 'it looks like an API key or access token',
  },
  {
    pattern: /\b(api[_ -]?key|access[_ -]?token|secret[_ -]?key|client[_ -]?secret|bearer\s+[A-Za-z0-9._-]{10,})\b/i,
    reason: 'it mentions an API key, token, or secret',
  },
  {
    pattern: /\b(password|passcode|passphrase|pin)\b[\s:=-]*\S/i,
    reason: 'it appears to contain a password or PIN',
  },
  {
    pattern: /\b(?:\d[ -]?){13,19}\b/,
    reason: 'it contains a long digit sequence that could be a card or account number',
  },
  {
    pattern: /\b\d{3}-\d{2}-\d{4}\b/,
    reason: 'it looks like a government ID number',
  },
  {
    pattern: /\b(iban|routing number|account number|sort code|swift code)\b/i,
    reason: 'it references a bank account identifier',
  },
];

export function detectSensitive(text: string): SensitiveMatch | null {
  for (const { pattern, reason } of PATTERNS) {
    if (pattern.test(text)) return { reason };
  }
  return null;
}
