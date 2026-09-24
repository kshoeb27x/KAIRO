// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { useSpeechInput } from '../../../src/client/features/voice/useSpeechInput';

class FakeRecognition {
  static instances: FakeRecognition[] = [];
  lang = '';
  continuous = false;
  interimResults = false;
  maxAlternatives = 1;
  onresult: ((event: unknown) => void) | null = null;
  onerror: ((event: { error: string; message: string }) => void) | null = null;
  onend: (() => void) | null = null;
  started = false;
  constructor() {
    FakeRecognition.instances.push(this);
  }
  start() {
    this.started = true;
  }
  stop() {
    this.onend?.();
  }
  abort() {
    this.started = false;
  }
}

function resultEvent(entries: Array<{ text: string; final: boolean }>) {
  return {
    resultIndex: 0,
    results: entries.map((entry) => ({
      isFinal: entry.final,
      length: 1,
      0: { transcript: entry.text, confidence: 0.9 },
    })),
  };
}

beforeEach(() => {
  FakeRecognition.instances = [];
  (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition =
    FakeRecognition;
  // Minimal getUserMedia + AudioContext fakes for the level meter.
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [] }),
    },
  });
  vi.stubGlobal(
    'AudioContext',
    class {
      createMediaStreamSource() {
        return { connect: () => undefined };
      }
      createAnalyser() {
        return {
          fftSize: 512,
          getByteTimeDomainData: (data: Uint8Array) => data.fill(128),
        };
      }
      close() {
        return Promise.resolve();
      }
    },
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
});

function makeCallbacks() {
  return {
    onLevel: vi.fn(),
    onPartial: vi.fn(),
    onFinal: vi.fn(),
    onEmpty: vi.fn(),
    onError: vi.fn(),
  };
}

describe('useSpeechInput', () => {
  it('feature-detects recognition support', () => {
    const { result } = renderHook(() => useSpeechInput(makeCallbacks()));
    expect(result.current.recognitionSupported).toBe(true);
  });

  it('delivers partial then final transcripts on push-to-talk release', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechInput(cb));
    act(() => result.current.start());
    const recognition = FakeRecognition.instances[0]!;
    expect(recognition.started).toBe(true);

    act(() => recognition.onresult?.(resultEvent([{ text: 'what are we', final: false }])));
    expect(cb.onPartial).toHaveBeenCalledWith('what are we');

    act(() =>
      recognition.onresult?.(resultEvent([{ text: 'what are we building today', final: true }])),
    );
    act(() => result.current.stop()); // release triggers stop → onend
    expect(cb.onFinal).toHaveBeenCalledWith('what are we building today');
    expect(cb.onError).not.toHaveBeenCalled();
  });

  it('reports silence as empty rather than an error', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechInput(cb));
    act(() => result.current.start());
    act(() => result.current.stop());
    expect(cb.onEmpty).toHaveBeenCalledTimes(1);
    expect(cb.onFinal).not.toHaveBeenCalled();
  });

  it('maps permission denial to an understandable message', () => {
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechInput(cb));
    act(() => result.current.start());
    const recognition = FakeRecognition.instances[0]!;
    act(() => recognition.onerror?.({ error: 'not-allowed', message: '' }));
    expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining('permission'));
  });

  it('errors gracefully when recognition is unavailable', () => {
    delete (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
    const cb = makeCallbacks();
    const { result } = renderHook(() => useSpeechInput(cb));
    expect(result.current.recognitionSupported).toBe(false);
    act(() => result.current.start());
    expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining('not supported'));
  });
});
