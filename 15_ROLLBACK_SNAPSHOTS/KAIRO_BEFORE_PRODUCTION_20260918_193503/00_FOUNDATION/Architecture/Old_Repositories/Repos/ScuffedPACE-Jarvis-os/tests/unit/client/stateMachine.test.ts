import { describe, expect, it } from 'vitest';
import {
  appReducer,
  initialMachine,
  type AppEvent,
  type MachineContext,
} from '../../../src/client/app/stateMachine';

function run(events: AppEvent[], from: MachineContext = initialMachine): MachineContext {
  return events.reduce(appReducer, from);
}

const booted = run([{ type: 'BOOTSTRAP_SUCCEEDED' }]);

describe('app state machine', () => {
  it('boots into idle on success and error on failure', () => {
    expect(booted.state).toBe('idle');
    expect(run([{ type: 'BOOTSTRAP_FAILED', message: 'down' }]).state).toBe('error');
  });

  it('follows the full voice request happy path', () => {
    const ctx = run(
      [
        { type: 'START_LISTENING' },
        { type: 'AUDIO_LEVEL_CHANGED', level: 0.6 },
        { type: 'PARTIAL_TRANSCRIPT', text: 'what are we' },
        { type: 'FINAL_TRANSCRIPT', text: 'what are we building today' },
        { type: 'SUBMIT_REQUEST' },
        { type: 'ROUTE_SELECTED' },
        { type: 'MODEL_STARTED' },
        { type: 'RESPONSE_RECEIVED' },
        { type: 'SPEECH_STARTED' },
        { type: 'SPEECH_BOUNDARY' },
        { type: 'SPEECH_ENDED' },
      ],
      booted,
    );
    expect(ctx.state).toBe('idle');
    expect(ctx.speechPulse).toBe(1);
  });

  it('enforces a single active request', () => {
    const busy = run([{ type: 'SUBMIT_REQUEST' }], booted);
    expect(busy.state).toBe('routing');
    // A second submission while busy is ignored.
    expect(run([{ type: 'SUBMIT_REQUEST' }], busy)).toEqual(busy);
    expect(run([{ type: 'START_LISTENING' }], busy).state).toBe('routing');
  });

  it('tool execution reaches permission and completes only via a decision', () => {
    const inPermission = run(
      [
        { type: 'SUBMIT_REQUEST' },
        { type: 'ROUTE_SELECTED' },
        { type: 'TOOL_STARTED' },
        { type: 'PERMISSION_REQUIRED', actionId: 'a-1' },
      ],
      booted,
    );
    expect(inPermission.state).toBe('permission');
    expect(inPermission.pendingActionId).toBe('a-1');
    // The stream finishing does not leave permission — only a decision does.
    const afterResponse = run([{ type: 'RESPONSE_RECEIVED' }], inPermission);
    expect(afterResponse.state).toBe('permission');
    expect(run([{ type: 'ACTION_APPROVED' }], afterResponse).state).toBe('idle');
    expect(run([{ type: 'ACTION_CANCELLED' }], afterResponse).pendingActionId).toBeNull();
  });

  it('interruption returns to idle from active states and preserves transcript context', () => {
    const listening = run(
      [{ type: 'START_LISTENING' }, { type: 'PARTIAL_TRANSCRIPT', text: 'hold on' }],
      booted,
    );
    const interrupted = run([{ type: 'INTERRUPT' }], listening);
    expect(interrupted.state).toBe('idle');
    expect(interrupted.partialTranscript).toBe('hold on');

    const speaking = run(
      [{ type: 'SUBMIT_REQUEST' }, { type: 'ROUTE_SELECTED' }, { type: 'RESPONSE_RECEIVED' }, { type: 'SPEECH_STARTED' }],
      booted,
    );
    expect(speaking.state).toBe('speaking');
    expect(run([{ type: 'INTERRUPT' }], speaking).state).toBe('idle');
  });

  it('errors never silently become success — only RECOVER leaves error', () => {
    const failed = run([{ type: 'SUBMIT_REQUEST' }, { type: 'FAILURE', message: 'boom' }], booted);
    expect(failed.state).toBe('error');
    expect(run([{ type: 'RESPONSE_RECEIVED' }], failed).state).toBe('error');
    expect(run([{ type: 'SPEECH_STARTED' }], failed).state).toBe('error');
    expect(run([{ type: 'INTERRUPT' }], failed).state).toBe('error');
    const recovered = run([{ type: 'RECOVER' }], failed);
    expect(recovered.state).toBe('idle');
    expect(recovered.errorMessage).toBeNull();
  });

  it('audio levels only apply while listening and are clamped', () => {
    const listening = run([{ type: 'START_LISTENING' }], booted);
    expect(run([{ type: 'AUDIO_LEVEL_CHANGED', level: 4 }], listening).audioLevel).toBe(1);
    expect(run([{ type: 'AUDIO_LEVEL_CHANGED', level: 0.5 }], booted).audioLevel).toBe(0);
  });

  it('stop listening without a transcript returns to idle', () => {
    const listening = run([{ type: 'START_LISTENING' }], booted);
    expect(run([{ type: 'STOP_LISTENING' }], listening).state).toBe('idle');
  });

  it('speech boundary events increment the pulse only while speaking', () => {
    expect(run([{ type: 'SPEECH_BOUNDARY' }], booted).speechPulse).toBe(0);
  });
});
