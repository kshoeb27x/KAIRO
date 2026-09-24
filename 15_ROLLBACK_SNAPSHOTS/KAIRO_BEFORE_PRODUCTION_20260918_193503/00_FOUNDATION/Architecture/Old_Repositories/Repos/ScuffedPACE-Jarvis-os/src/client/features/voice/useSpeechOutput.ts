import { useCallback, useEffect, useRef } from 'react';

export interface SpeechOutputCallbacks {
  onStart: () => void;
  /** Fired on real SpeechSynthesis boundary events — drives speak pulses. */
  onBoundary: () => void;
  onEnd: () => void;
  onError: (message: string) => void;
}

export interface SpeechOutput {
  synthesisSupported: boolean;
  speak: (text: string, voiceUri: string | null, rate?: number) => void;
  cancel: () => void;
}

/**
 * Spoken responses via window.speechSynthesis. The speaking state follows
 * real start/boundary/end/error events — browser synthesis exposes no audio
 * stream, so no amplitude is faked. Cancellation is immediate and the text
 * response is never lost when synthesis fails.
 */
export function useSpeechOutput(callbacks: SpeechOutputCallbacks): SpeechOutput {
  const cbRef = useRef(callbacks);
  cbRef.current = callbacks;
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const cancellingRef = useRef(false);
  const watchdogRef = useRef(0);

  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  const cancel = useCallback(() => {
    if (!supported) return;
    window.clearTimeout(watchdogRef.current);
    cancellingRef.current = true;
    window.speechSynthesis.cancel();
    utteranceRef.current = null;
  }, [supported]);

  useEffect(() => cancel, [cancel]);

  const speak = useCallback(
    (text: string, voiceUri: string | null, rate = 1) => {
      if (!supported) {
        cbRef.current.onError('Speech output is not supported in this browser.');
        return;
      }
      const synth = window.speechSynthesis;
      window.clearTimeout(watchdogRef.current);
      // Clear only an actually busy queue: calling cancel() right before
      // speak() when nothing is queued can swallow the new utterance in
      // Chrome.
      if (synth.speaking || synth.pending) synth.cancel();
      cancellingRef.current = false;

      const utterance = new SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance; // keep a reference so events keep firing
      utterance.rate = Math.min(2, Math.max(0.5, rate));

      if (voiceUri) {
        const voice = window.speechSynthesis.getVoices().find((v) => v.voiceURI === voiceUri);
        if (voice) utterance.voice = voice;
      }

      let started = false;
      let ended = false;
      utterance.onstart = () => {
        if (ended) return; // the watchdog already reported this utterance dead
        window.clearTimeout(watchdogRef.current);
        started = true;
        cbRef.current.onStart();
      };
      utterance.onboundary = () => {
        if (started && !ended) cbRef.current.onBoundary();
      };
      utterance.onend = () => {
        if (ended) return;
        window.clearTimeout(watchdogRef.current);
        ended = true;
        utteranceRef.current = null;
        cbRef.current.onEnd();
      };
      utterance.onerror = (event) => {
        if (ended) return;
        window.clearTimeout(watchdogRef.current);
        ended = true;
        utteranceRef.current = null;
        if (cancellingRef.current || event.error === 'canceled' || event.error === 'interrupted') {
          cbRef.current.onEnd();
        } else {
          cbRef.current.onError(
            'Speech playback failed in this browser; the text response above is unaffected.',
          );
        }
      };

      // Chrome can leave the engine wedged in a paused state after a cancel;
      // resume() is a harmless no-op when it is not paused.
      if (typeof synth.resume === 'function') synth.resume();
      synth.speak(utterance);

      // Honest failure: if the engine never starts (e.g. the browser's voice
      // is broken or unavailable), report it instead of staying silent.
      watchdogRef.current = window.setTimeout(() => {
        if (started || ended) return;
        ended = true;
        utteranceRef.current = null;
        cancellingRef.current = true;
        synth.cancel();
        cbRef.current.onError(
          'Speech output did not start — the browser voice may be unavailable. The text response above is unaffected.',
        );
      }, 3000);
    },
    [supported, cancel],
  );

  return { synthesisSupported: supported, speak, cancel };
}
