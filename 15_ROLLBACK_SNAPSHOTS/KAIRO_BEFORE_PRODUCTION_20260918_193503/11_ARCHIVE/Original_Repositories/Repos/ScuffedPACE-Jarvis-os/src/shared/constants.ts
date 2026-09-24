export const APP_VERSION = '0.2.0';
export const SCHEMA_VERSION = 4;

/** Maximum accepted length for a user request, in characters. */
export const MAX_INPUT_LENGTH = 8000;

/** How long a pending consequential action stays approvable. */
export const PENDING_ACTION_TTL_MS = 10 * 60 * 1000;

/** Bounded conversation window sent to model providers. */
export const CONTEXT_MESSAGE_LIMIT = 12;

/** Bounded number of memories loaded into model context. */
export const CONTEXT_MEMORY_LIMIT = 8;
