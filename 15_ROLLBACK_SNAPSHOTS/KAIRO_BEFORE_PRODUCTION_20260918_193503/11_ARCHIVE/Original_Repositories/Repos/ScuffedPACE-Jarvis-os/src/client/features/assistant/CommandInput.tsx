import { useEffect, useState } from 'react';
import { Mic, Send, Square } from 'lucide-react';
import type { AppState } from '../../app/stateMachine';

interface CommandInputProps {
  appState: AppState;
  onSubmit: (text: string) => void;
  onInterrupt: () => void;
  micSupported: boolean;
  onMicPress: () => void;
  onMicRelease: () => void;
  /** Final transcript delivered by speech recognition, editable before send. */
  seededText: string;
  onSeededTextConsumed: () => void;
}

const QUICK_COMMANDS = [
  'What are we building today?',
  "Break tonight's build into the next three steps.",
  'Draft an email telling my collaborator the prototype will be ready tomorrow.',
  'Evaluate whether this architecture will scale to multiple businesses.',
  'Remember that I prefer approval before any external action.',
];

export function CommandInput({
  appState,
  onSubmit,
  onInterrupt,
  micSupported,
  onMicPress,
  onMicRelease,
  seededText,
  onSeededTextConsumed,
}: CommandInputProps) {
  const [text, setText] = useState('');

  // Seed the editable input with the final voice transcript exactly once.
  useEffect(() => {
    if (seededText) {
      setText(seededText);
      onSeededTextConsumed();
    }
  }, [seededText]); // onSeededTextConsumed is intentionally not a dependency

  const busy =
    appState === 'routing' || appState === 'thinking' || appState === 'executing';
  const canSubmit =
    (appState === 'idle' || appState === 'transcribing') && text.trim().length > 0;
  const listening = appState === 'listening';

  const submit = (): void => {
    const trimmed = text.trim();
    if (!canSubmit || trimmed.length === 0) return;
    setText('');
    onSubmit(trimmed);
  };

  return (
    <>
      <div className="command-row">
        <button
          type="button"
          className={`btn mic${listening ? ' listening' : ''}`}
          disabled={!micSupported || (busy && !listening)}
          aria-label={
            !micSupported
              ? 'Microphone input not supported in this browser'
              : listening
                ? 'Release to stop listening'
                : 'Hold to talk'
          }
          title={micSupported ? 'Hold to talk (push-to-talk)' : 'Speech recognition unavailable'}
          onPointerDown={(e) => {
            e.preventDefault();
            if (!listening) onMicPress();
          }}
          onPointerUp={() => listening && onMicRelease()}
          onPointerLeave={() => listening && onMicRelease()}
          onKeyDown={(e) => {
            if ((e.key === ' ' || e.key === 'Enter') && !listening && !e.repeat) {
              e.preventDefault();
              onMicPress();
            }
          }}
          onKeyUp={(e) => {
            if ((e.key === ' ' || e.key === 'Enter') && listening) {
              e.preventDefault();
              onMicRelease();
            }
          }}
        >
          <Mic size={16} />
        </button>
        <textarea
          className="command-input"
          rows={1}
          placeholder="Ask Jarvis anything…"
          value={text}
          maxLength={8000}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          aria-label="Command input"
        />
        {busy || appState === 'speaking' || listening ? (
          <button type="button" className="btn danger" onClick={onInterrupt}>
            <Square size={13} /> Stop
          </button>
        ) : (
          <button
            type="button"
            className="btn primary"
            disabled={!canSubmit}
            onClick={submit}
            aria-label="Send"
          >
            <Send size={14} /> Send
          </button>
        )}
      </div>
      <div className="quick-commands" aria-label="Quick commands">
        {QUICK_COMMANDS.map((command) => (
          <button
            key={command}
            type="button"
            className="btn"
            disabled={busy || listening}
            onClick={() => {
              if (appState === 'idle' || appState === 'transcribing') {
                setText('');
                onSubmit(command);
              }
            }}
          >
            {command}
          </button>
        ))}
      </div>
    </>
  );
}
