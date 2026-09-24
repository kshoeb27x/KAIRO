import { useCallback, useEffect, useRef } from 'react';

export interface SpeechInputCallbacks {
  /** Measured microphone RMS level, 0..1, while listening. */
  onLevel: (level: number) => void;
  onPartial: (text: string) => void;
  /** Delivered once when listening ends with a usable transcript. */
  onFinal: (text: string) => void;
  /** Listening ended without a transcript (silence, stop, no-match). */
  onEmpty: () => void;
  onError: (message: string) => void;
}

export interface SpeechInput {
  /** SpeechRecognition feature-detected in this browser. */
  recognitionSupported: boolean;
  /** Begin push-to-talk. Must be called from a user gesture. */
  start: () => void;
  /** End push-to-talk (release). */
  stop: () => void;
}

function getRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

/**
 * Push-to-talk speech input. The microphone is never activated automatically:
 * `start()` runs only from a user gesture. Uses getUserMedia + AnalyserNode
 * for real measured levels and Web Speech recognition for transcription
 * (browser recognition may be network-based — this is not claimed to be
 * local). All tracks, contexts, and recognition sessions are cleaned up.
 */
export function useSpeechInput(callbacks: SpeechInputCallbacks): SpeechInput {
  const cbRef = useRef(callbacks);
  cbRef.current = callbacks;

  const activeRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const rafRef = useRef(0);
  const finalTextRef = useRef('');
  const errorReportedRef = useRef(false);

  const cleanup = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    if (recognitionRef.current) {
      recognitionRef.current.onresult = null;
      recognitionRef.current.onerror = null;
      recognitionRef.current.onend = null;
      try {
        recognitionRef.current.abort();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    void audioContextRef.current?.close().catch(() => undefined);
    audioContextRef.current = null;
    activeRef.current = false;
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const start = useCallback(() => {
    if (activeRef.current) return;
    const Recognition = getRecognitionConstructor();
    if (!Recognition) {
      cbRef.current.onError('Speech recognition is not supported in this browser. Type instead.');
      return;
    }
    activeRef.current = true;
    finalTextRef.current = '';
    errorReportedRef.current = false;

    // Microphone level metering via getUserMedia + AnalyserNode.
    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        if (!activeRef.current) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const audioContext = new AudioContext();
        audioContextRef.current = audioContext;
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
        const data = new Uint8Array(analyser.fftSize);
        const meter = (): void => {
          if (!activeRef.current) return;
          analyser.getByteTimeDomainData(data);
          let sum = 0;
          for (const sample of data) {
            const centered = (sample - 128) / 128;
            sum += centered * centered;
          }
          const rms = Math.sqrt(sum / data.length);
          cbRef.current.onLevel(Math.min(1, rms * 4));
          rafRef.current = requestAnimationFrame(meter);
        };
        rafRef.current = requestAnimationFrame(meter);
      })
      .catch(() => {
        if (!activeRef.current) return;
        errorReportedRef.current = true;
        cleanup();
        cbRef.current.onError(
          'Microphone access was denied or no microphone is available. You can keep typing.',
        );
      });

    // Recognition session.
    const recognition = new Recognition();
    recognitionRef.current = recognition;
    recognition.lang = navigator.language || 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i]!;
        const transcript = result[0]?.transcript ?? '';
        if (result.isFinal) final += transcript;
        else interim += transcript;
      }
      finalTextRef.current = final;
      cbRef.current.onPartial((final + interim).trim());
    };

    recognition.onerror = (event) => {
      if (!activeRef.current || errorReportedRef.current) return;
      if (event.error === 'no-speech' || event.error === 'aborted') return; // onend handles these
      errorReportedRef.current = true;
      const message =
        event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? 'Microphone permission was denied. Allow it in the browser, or keep typing.'
          : event.error === 'audio-capture'
            ? 'No microphone was found. You can keep typing.'
            : event.error === 'network'
              ? 'Speech recognition needs a network connection and could not reach it. You can keep typing.'
              : 'Speech recognition failed. You can keep typing.';
      cleanup();
      cbRef.current.onError(message);
    };

    recognition.onend = () => {
      if (!activeRef.current) return;
      const text = finalTextRef.current.trim();
      cleanup();
      if (errorReportedRef.current) return;
      if (text.length > 0) cbRef.current.onFinal(text);
      else cbRef.current.onEmpty();
    };

    try {
      recognition.start();
    } catch {
      cleanup();
      cbRef.current.onError('Could not start speech recognition. You can keep typing.');
    }
  }, [cleanup]);

  const stop = useCallback(() => {
    if (!activeRef.current) return;
    // Ask recognition to finalize; onend delivers the transcript and cleans up.
    cancelAnimationFrame(rafRef.current);
    try {
      recognitionRef.current?.stop();
    } catch {
      cleanup();
      cbRef.current.onEmpty();
    }
  }, [cleanup]);

  return {
    recognitionSupported: getRecognitionConstructor() !== null,
    start,
    stop,
  };
}
