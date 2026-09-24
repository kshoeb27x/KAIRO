/**
 * Explicit typed application state machine. The sphere and every visual state
 * derive from these transitions — which are driven by real application
 * events, never by decorative timers.
 *
 * Invariants:
 * - Only one assistant request is active at a time (SUBMIT_REQUEST is ignored
 *   outside idle/transcribing).
 * - INTERRUPT always returns to idle; callers cancel fetch/recognition/speech.
 * - A consequential action leaves `permission` only via an explicit decision.
 * - Errors never silently become success — only RECOVER leaves `error`.
 */

export type AppState =
  | 'booting'
  | 'idle'
  | 'listening'
  | 'transcribing'
  | 'routing'
  | 'thinking'
  | 'executing'
  | 'permission'
  | 'speaking'
  | 'error';

export interface MachineContext {
  state: AppState;
  /** Measured microphone level 0..1 while listening; 0 otherwise. */
  audioLevel: number;
  partialTranscript: string;
  finalTranscript: string;
  errorMessage: string | null;
  pendingActionId: string | null;
  /** Increments on real SpeechSynthesis boundary events; drives speak pulses. */
  speechPulse: number;
}

export type AppEvent =
  | { type: 'BOOTSTRAP_SUCCEEDED' }
  | { type: 'BOOTSTRAP_FAILED'; message: string }
  | { type: 'START_LISTENING' }
  | { type: 'AUDIO_LEVEL_CHANGED'; level: number }
  | { type: 'PARTIAL_TRANSCRIPT'; text: string }
  | { type: 'FINAL_TRANSCRIPT'; text: string }
  | { type: 'STOP_LISTENING' }
  | { type: 'SUBMIT_REQUEST' }
  | { type: 'ROUTE_SELECTED' }
  | { type: 'MODEL_STARTED' }
  | { type: 'TOOL_STARTED' }
  | { type: 'PERMISSION_REQUIRED'; actionId: string }
  | { type: 'ACTION_APPROVED' }
  | { type: 'ACTION_CANCELLED' }
  | { type: 'RESPONSE_RECEIVED' }
  | { type: 'SPEECH_STARTED' }
  | { type: 'SPEECH_BOUNDARY' }
  | { type: 'SPEECH_ENDED' }
  | { type: 'INTERRUPT' }
  | { type: 'FAILURE'; message: string }
  | { type: 'RECOVER' };

export const initialMachine: MachineContext = {
  state: 'booting',
  audioLevel: 0,
  partialTranscript: '',
  finalTranscript: '',
  errorMessage: null,
  pendingActionId: null,
  speechPulse: 0,
};

const BUSY_STATES: AppState[] = ['routing', 'thinking', 'executing'];

export function appReducer(ctx: MachineContext, event: AppEvent): MachineContext {
  switch (event.type) {
    case 'BOOTSTRAP_FAILED':
      return { ...ctx, state: 'error', errorMessage: event.message };
    case 'BOOTSTRAP_SUCCEEDED':
      return ctx.state === 'booting' ? { ...ctx, state: 'idle' } : ctx;

    case 'FAILURE':
      return { ...ctx, state: 'error', errorMessage: event.message, audioLevel: 0 };
    case 'RECOVER':
      return ctx.state === 'error' ? { ...ctx, state: 'idle', errorMessage: null } : ctx;

    case 'INTERRUPT':
      // Preserve transcript context; callers cancel fetch/recognition/speech.
      if (ctx.state === 'booting' || ctx.state === 'error') return ctx;
      return { ...ctx, state: 'idle', audioLevel: 0 };

    case 'START_LISTENING':
      if (ctx.state !== 'idle' && ctx.state !== 'transcribing') return ctx;
      return { ...ctx, state: 'listening', partialTranscript: '', finalTranscript: '' };
    case 'AUDIO_LEVEL_CHANGED':
      if (ctx.state !== 'listening') return ctx;
      return { ...ctx, audioLevel: clamp01(event.level) };
    case 'PARTIAL_TRANSCRIPT':
      if (ctx.state !== 'listening') return ctx;
      return { ...ctx, partialTranscript: event.text };
    case 'FINAL_TRANSCRIPT':
      if (ctx.state !== 'listening') return ctx;
      return {
        ...ctx,
        state: 'transcribing',
        finalTranscript: event.text,
        partialTranscript: '',
        audioLevel: 0,
      };
    case 'STOP_LISTENING':
      if (ctx.state !== 'listening') return ctx;
      return { ...ctx, state: 'idle', audioLevel: 0 };

    case 'SUBMIT_REQUEST':
      // Only one active request in the MVP.
      if (ctx.state !== 'idle' && ctx.state !== 'transcribing') return ctx;
      return { ...ctx, state: 'routing', finalTranscript: '', partialTranscript: '' };

    case 'ROUTE_SELECTED':
      return ctx.state === 'routing' ? { ...ctx, state: 'thinking' } : ctx;
    case 'MODEL_STARTED':
      return BUSY_STATES.includes(ctx.state) ? { ...ctx, state: 'thinking' } : ctx;
    case 'TOOL_STARTED':
      return BUSY_STATES.includes(ctx.state) ? { ...ctx, state: 'executing' } : ctx;

    case 'PERMISSION_REQUIRED':
      if (!BUSY_STATES.includes(ctx.state) && ctx.state !== 'idle') return ctx;
      return { ...ctx, state: 'permission', pendingActionId: event.actionId };
    case 'ACTION_APPROVED':
    case 'ACTION_CANCELLED':
      if (ctx.state !== 'permission') return ctx;
      return { ...ctx, state: 'idle', pendingActionId: null };

    case 'RESPONSE_RECEIVED':
      // While awaiting permission, the approval card keeps visual priority —
      // the decision, not the model text, completes the action.
      if (ctx.state === 'permission') return ctx;
      if (!BUSY_STATES.includes(ctx.state)) return ctx;
      return { ...ctx, state: 'idle' };

    case 'SPEECH_STARTED':
      if (ctx.state !== 'idle' && !BUSY_STATES.includes(ctx.state)) return ctx;
      return { ...ctx, state: 'speaking' };
    case 'SPEECH_BOUNDARY':
      if (ctx.state !== 'speaking') return ctx;
      return { ...ctx, speechPulse: ctx.speechPulse + 1 };
    case 'SPEECH_ENDED':
      return ctx.state === 'speaking' ? { ...ctx, state: 'idle' } : ctx;

    default:
      return ctx;
  }
}

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}
