// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { useSpeechOutput } from '../../../src/client/features/voice/useSpeechOutput';

type UtteranceLike = {
  text: string;
  voice: unknown;
  onstart: (() => void) | null;
  onboundary: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
};

let spoken: UtteranceLike[] = [];
let cancelCalls = 0;

class FakeUtterance implements UtteranceLike {
  text: string;
  voice: unknown = null;
  onstart: (() => void) | null = null;
  onboundary: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

beforeEach(() => {
  spoken = [];
  cancelCalls = 0;
  vi.stubGlobal('SpeechSynthesisUtterance', FakeUtterance);
  Object.defineProperty(window, 'speechSynthesis', {
    configurable: true,
    value: {
      speaking: false,
      pending: false,
      paused: false,
      resume: () => undefined,
      speak: (utterance: UtteranceLike) => spoken.push(utterance),
      cancel: () => {
        cancelCalls += 1;
        // Real browsers fire an error/end on the active utterance.
        const active = spoken[spoken.length - 1];
        active?.onerror?.({ error: 'interrupted' });
      },
      getVoices: () => [],
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function makeCallbacks() {
  return {
    onStart: vi.fn(),
    onBoundary: vi.fn(),
    onEnd: vi.fn(),
    onError: vi.fn(),
  };
}

describe('useSpeechOutput', () => {
  it('drives speaking state from real start/boundary/end events', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechOutput(cb));
    expect(result.current.synthesisSupported).toBe(true);

    act(() => result.current.speak('Hello Farhan', null));
    const utterance = spoken[0]!;
    act(() => utterance.onstart?.());
    act(() => utterance.onboundary?.());
    act(() => utterance.onboundary?.());
    act(() => utterance.onend?.());

    expect(cb.onStart).toHaveBeenCalledTimes(1);
    expect(cb.onBoundary).toHaveBeenCalledTimes(2);
    expect(cb.onEnd).toHaveBeenCalledTimes(1);
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it('supports immediate interruption without reporting an error', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechOutput(cb));
    act(() => result.current.speak('long response', null));
    act(() => spoken[0]!.onstart?.());
    act(() => result.current.cancel());
    expect(cancelCalls).toBeGreaterThan(0);
    expect(cb.onEnd).toHaveBeenCalled();
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it('reports synthesis failure without losing the text response', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechOutput(cb));
    act(() => result.current.speak('will fail', null));
    act(() => spoken[0]!.onerror?.({ error: 'synthesis-failed' }));
    expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining('text response'));
  });

  it('never fires duplicate end events', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechOutput(cb));
    act(() => result.current.speak('x', null));
    const utterance = spoken[0]!;
    act(() => utterance.onend?.());
    act(() => utterance.onend?.());
    act(() => utterance.onerror?.({ error: 'canceled' }));
    expect(cb.onEnd).toHaveBeenCalledTimes(1);
  });

  it('reports honestly when synthesis never starts instead of staying silent', () => {
    vi.useFakeTimers();
    try {
      const cb = makeCallbacks();
      const { result } = renderHook(() => useSpeechOutput(cb));
      act(() => result.current.speak('never starts', null));
      act(() => {
        vi.advanceTimersByTime(3100);
      });
      expect(cb.onStart).not.toHaveBeenCalled();
      expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining('text response'));
      // Late events from the dead utterance must not double-report.
      act(() => spoken[0]!.onstart?.());
      act(() => spoken[0]!.onend?.());
      expect(cb.onStart).not.toHaveBeenCalled();
      expect(cb.onEnd).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it('does not fire the watchdog once speech has started', () => {
    vi.useFakeTimers();
    try {
      const cb = makeCallbacks();
      const { result } = renderHook(() => useSpeechOutput(cb));
      act(() => result.current.speak('starts fine', null));
      act(() => spoken[0]!.onstart?.());
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      expect(cb.onError).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
