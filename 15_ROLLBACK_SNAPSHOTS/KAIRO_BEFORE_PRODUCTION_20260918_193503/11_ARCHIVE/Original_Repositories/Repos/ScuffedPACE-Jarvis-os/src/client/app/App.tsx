import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import type { ActivityEvent } from '../../shared/schemas/activity';
import type { BootstrapResponse } from '../../shared/contracts/api';
import type { ExplanationDepth, Message, PendingAction } from '../../shared/types';
import {
  decideAction,
  fetchBootstrap,
  streamAssistant,
  updateSettings,
} from '../services/api';
import { appReducer, initialMachine } from './stateMachine';
import { LeftNav, type NavView } from '../components/LeftNav';
import { NeuralSphere } from '../components/NeuralSphere';
import { StatusStrip } from '../components/StatusStrip';
import { LowerWorkspace } from '../components/LowerWorkspace';
import { ConversationPanel } from '../features/assistant/ConversationPanel';
import { CommandInput } from '../features/assistant/CommandInput';
import { ActivityRail } from '../features/activity/ActivityRail';
import { ApprovalCard } from '../features/permissions/ApprovalCard';
import { MemoryPanel } from '../features/memory/MemoryPanel';
import { ProjectsPanel } from '../features/projects/ProjectsPanel';
import { MailPanel } from '../features/google/MailPanel';
import { CalendarPanel } from '../features/google/CalendarPanel';
import { TasksPanel } from '../features/tasks/TasksPanel';
import { TradingPanel } from '../features/trading/TradingPanel';
import { SettingsPanel } from '../features/settings/SettingsPanel';
import { useSpeechInput } from '../features/voice/useSpeechInput';
import { useSpeechOutput } from '../features/voice/useSpeechOutput';
import { detectSensitive } from '../../shared/security/sensitive';

function greeting(): string {
  const hour = new Date().getHours();
  const part = hour < 5 ? 'evening' : hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening';
  return `Good ${part}, Farhan`;
}

const STATE_CAPTIONS: Record<string, string> = {
  booting: 'Starting up…',
  idle: 'Ready',
  listening: 'Listening…',
  transcribing: 'Transcript ready — edit or send',
  routing: 'Analyzing your request',
  thinking: 'Thinking',
  executing: 'Executing tool',
  permission: 'Awaiting your approval',
  speaking: 'Speaking',
  error: 'Attention needed',
};

export default function App() {
  const [machine, dispatch] = useReducer(appReducer, initialMachine);
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [serverHealthy, setServerHealthy] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [explanationDepth, setExplanationDepth] = useState<ExplanationDepth>('normal');
  const [speechRate, setSpeechRate] = useState(1);
  const [voiceUri, setVoiceUri] = useState<string | null>(null);
  const [memoryCount, setMemoryCount] = useState(0);
  const [view, setView] = useState<NavView>('home');
  const [seededText, setSeededText] = useState('');
  const [notice, setNotice] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Synchronous in-flight guard: rapid double submissions (e.g. two quick
  // clicks on a quick-command chip) land before React re-renders, so the
  // state-machine check alone cannot prevent duplicate requests.
  const requestActiveRef = useRef(false);

  const speechOutput = useSpeechOutput({
    onStart: () => dispatch({ type: 'SPEECH_STARTED' }),
    onBoundary: () => dispatch({ type: 'SPEECH_BOUNDARY' }),
    onEnd: () => dispatch({ type: 'SPEECH_ENDED' }),
    onError: (message) => {
      dispatch({ type: 'SPEECH_ENDED' });
      setNotice(message);
    },
  });

  const loadBootstrap = useCallback(() => {
    fetchBootstrap()
      .then((data) => {
        setBootstrap(data);
        setServerHealthy(true);
        setMessages(data.messages);
        setConversationId(data.conversation?.id);
        setAutoSpeak(data.settings.autoSpeak);
        setExplanationDepth(data.settings.explanationDepth);
        setSpeechRate(data.settings.speechRate);
        setVoiceUri(data.settings.voiceUri);
        const firstPending = data.pendingActions[0] ?? null;
        setPendingAction(firstPending);
        dispatch({ type: 'BOOTSTRAP_SUCCEEDED' });
        if (firstPending) {
          dispatch({ type: 'PERMISSION_REQUIRED', actionId: firstPending.id });
        }
      })
      .catch(() => {
        setServerHealthy(false);
        dispatch({
          type: 'BOOTSTRAP_FAILED',
          message:
            'Could not reach the JARVIS server. Make sure `npm run dev` is running, then retry.',
        });
      });
  }, []);

  useEffect(loadBootstrap, [loadBootstrap]);

  const handleStreamEvent = useCallback(
    (event: ActivityEvent): void => {
      setEvents((previous) => [...previous, event]);
      switch (event.eventType) {
        case 'request.accepted':
          setConversationId(event.payload.conversationId);
          break;
        case 'route.selected':
          dispatch({ type: 'ROUTE_SELECTED' });
          break;
        case 'model.started':
          dispatch({ type: 'MODEL_STARTED' });
          break;
        case 'tool.started':
          dispatch({ type: 'TOOL_STARTED' });
          break;
        case 'permission.required':
          setPendingAction(event.payload.action);
          dispatch({ type: 'PERMISSION_REQUIRED', actionId: event.payload.actionId });
          break;
        case 'memory.saved':
          setMemoryCount((count) => count + 1);
          break;
        case 'response.completed': {
          const message = event.payload.message;
          setMessages((previous) => [...previous, message]);
          dispatch({ type: 'RESPONSE_RECEIVED' });
          break;
        }
        case 'request.failed':
          dispatch({ type: 'FAILURE', message: event.payload.message });
          break;
        default:
          break;
      }
    },
    [],
  );

  const submit = useCallback(
    (text: string, options: { fromVoice?: boolean } = {}): void => {
      if (requestActiveRef.current) return;
      // A final voice transcript arrives while the machine is still in
      // `listening` (the FINAL_TRANSCRIPT dispatch has not rendered yet), so
      // the closure state check applies only to typed submissions.
      if (!options.fromVoice && machine.state !== 'idle' && machine.state !== 'transcribing') return;
      requestActiveRef.current = true;
      dispatch({ type: 'SUBMIT_REQUEST' });
      setNotice(null);
      // Optimistic local echo; the server persists the authoritative copy.
      setMessages((previous) => [
        ...previous,
        {
          id: `local-${Date.now()}`,
          conversationId: conversationId ?? 'pending',
          role: 'user',
          content: text,
          provider: null,
          model: null,
          createdAt: new Date().toISOString(),
        },
      ]);

      const abort = new AbortController();
      abortRef.current = abort;
      let sawPermission = false;
      let lastAssistant: Message | null = null;

      streamAssistant(
        text,
        conversationId,
        (event) => {
          if (event.eventType === 'permission.required') sawPermission = true;
          if (event.eventType === 'response.completed') lastAssistant = event.payload.message;
          handleStreamEvent(event);
        },
        abort.signal,
      )
        .then(() => {
          // Speak the answer only when no approval card is pending.
          if (lastAssistant && !sawPermission && autoSpeak && speechOutput.synthesisSupported) {
            const content = (lastAssistant as Message).content;
            // Never read likely-sensitive content aloud without warning.
            const sensitive = detectSensitive(content);
            if (sensitive) {
              setNotice(
                `I didn't read that reply aloud because ${sensitive.reason}. The text above is unaffected.`,
              );
            } else {
              speechOutput.speak(content, voiceUri, speechRate);
            }
          }
        })
        .catch((error: unknown) => {
          if (abort.signal.aborted) return; // user interrupted — already back to idle
          dispatch({
            type: 'FAILURE',
            message:
              error instanceof Error
                ? error.message
                : 'The request failed. The server may be offline.',
          });
        })
        .finally(() => {
          requestActiveRef.current = false;
        });
    },
    [machine.state, conversationId, autoSpeak, speechOutput, voiceUri, speechRate, handleStreamEvent],
  );

  const speechInput = useSpeechInput({
    onLevel: (level) => dispatch({ type: 'AUDIO_LEVEL_CHANGED', level }),
    onPartial: (text) => dispatch({ type: 'PARTIAL_TRANSCRIPT', text }),
    onFinal: (text) => {
      dispatch({ type: 'FINAL_TRANSCRIPT', text });
      // Push-to-talk release submits the finished transcript automatically,
      // exactly once. If a request is somehow still running, keep the
      // transcript editable in the input instead of dropping it.
      if (requestActiveRef.current) {
        setSeededText(text);
        return;
      }
      submit(text, { fromVoice: true });
    },
    onEmpty: () => {
      dispatch({ type: 'STOP_LISTENING' });
      setNotice('I did not catch anything — try again or type instead.');
    },
    onError: (message) => dispatch({ type: 'FAILURE', message }),
  });

  const interrupt = useCallback((): void => {
    abortRef.current?.abort();
    speechInput.stop();
    speechOutput.cancel();
    dispatch({ type: 'INTERRUPT' });
  }, [speechInput, speechOutput]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') interrupt();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [interrupt]);

  const micPress = useCallback((): void => {
    if (machine.state !== 'idle' && machine.state !== 'transcribing') return;
    speechOutput.cancel();
    dispatch({ type: 'START_LISTENING' });
    speechInput.start();
  }, [machine.state, speechInput, speechOutput]);

  const micRelease = useCallback((): void => {
    speechInput.stop();
  }, [speechInput]);

  const decide = useCallback(
    async (decision: 'approve' | 'cancel'): Promise<void> => {
      if (!pendingAction) return;
      const updated = await decideAction(pendingAction.id, decision);
      setPendingAction(null);
      dispatch({ type: decision === 'approve' ? 'ACTION_APPROVED' : 'ACTION_CANCELLED' });
      setNotice(
        updated.status === 'simulated_completed'
          ? 'Recorded: simulated send approved. Nothing was actually sent.'
          : updated.status === 'completed'
            ? 'Approved and completed.'
            : updated.status === 'failed'
              ? `The approved action failed: ${updated.executionError ?? 'unknown error'}`
              : 'Cancelled — nothing was sent or changed.',
      );
      // Executors may have appended messages (e.g. a Claude CLI reply).
      loadBootstrap();
    },
    [pendingAction, loadBootstrap],
  );

  // Panels (Mail/Calendar) propose actions; the shared approval card decides.
  const handlePanelAction = useCallback((action: PendingAction): void => {
    setPendingAction(action);
    dispatch({ type: 'PERMISSION_REQUIRED', actionId: action.id });
  }, []);

  const changeExplanationDepth = useCallback((depth: ExplanationDepth): void => {
    setExplanationDepth((previous) => {
      updateSettings({ explanationDepth: depth }).catch(() => {
        setExplanationDepth(previous);
        setNotice('Could not save the explanation depth setting.');
      });
      return depth;
    });
  }, []);

  const toggleAutoSpeak = useCallback((): void => {
    const next = !autoSpeak;
    setAutoSpeak(next);
    updateSettings({ autoSpeak: next }).catch(() => {
      setAutoSpeak(!next);
      setNotice('Could not save the auto-speak setting.');
    });
  }, [autoSpeak]);

  const provider = bootstrap?.provider ?? null;

  return (
    <div className="app">
      <LeftNav
        view={view === 'chat' ? 'chat' : view}
        onNavigate={setView}
        appState={machine.state}
        voiceStatusLabel={speechInput.recognitionSupported ? 'push-to-talk ready' : 'unavailable'}
      />

      <main className="center">
        <div className="center-header">
          <span className="greeting">{greeting()}</span>
          <span className={`state-chip${machine.state === 'error' ? ' error' : ''}`}>
            {STATE_CAPTIONS[machine.state]}
          </span>
        </div>

        {machine.state === 'error' && (
          <div className="error-banner" role="alert">
            <span>{machine.errorMessage ?? 'Something went wrong.'}</span>
            <button
              type="button"
              className="btn"
              onClick={() => {
                if (bootstrap === null) loadBootstrap();
                dispatch({ type: 'RECOVER' });
              }}
            >
              Recover
            </button>
          </div>
        )}
        {notice && machine.state !== 'error' && (
          <div className="error-banner" role="status" style={{ borderColor: 'var(--line-bright)', color: 'var(--text-dim)', background: 'var(--bg-panel)' }}>
            <span>{notice}</span>
            <button type="button" className="btn" onClick={() => setNotice(null)}>
              Dismiss
            </button>
          </div>
        )}

        <div className="sphere-wrap">
          <NeuralSphere
            state={machine.state}
            audioLevel={machine.audioLevel}
            speechPulse={machine.speechPulse}
          />
          <span className="sphere-caption">{STATE_CAPTIONS[machine.state]}</span>
          <span className="transcript-live" aria-live="polite">
            {machine.state === 'listening' ? machine.partialTranscript || '…' : ''}
          </span>
        </div>

        <ConversationPanel messages={messages} />

        <CommandInput
          appState={machine.state}
          onSubmit={submit}
          onInterrupt={interrupt}
          micSupported={speechInput.recognitionSupported}
          onMicPress={micPress}
          onMicRelease={micRelease}
          seededText={seededText}
          onSeededTextConsumed={() => setSeededText('')}
        />

        <LowerWorkspace
          project={bootstrap?.activeProject ?? null}
          pendingActions={pendingAction ? [pendingAction] : []}
          memoryCount={memoryCount}
        />
      </main>

      <ActivityRail
        events={events}
        provider={provider}
        serverHealthy={serverHealthy}
        speechRecognitionSupported={speechInput.recognitionSupported}
        speechSynthesisSupported={speechOutput.synthesisSupported}
        schemaVersion={bootstrap?.schemaVersion ?? null}
      />

      <StatusStrip
        appState={machine.state}
        appVersion={bootstrap?.appVersion ?? null}
        provider={provider}
        serverHealthy={serverHealthy}
        recognitionSupported={speechInput.recognitionSupported}
        synthesisSupported={speechOutput.synthesisSupported}
        autoSpeak={autoSpeak}
        onToggleAutoSpeak={toggleAutoSpeak}
        explanationDepth={explanationDepth}
        onChangeExplanationDepth={changeExplanationDepth}
      />

      {machine.state === 'permission' && pendingAction && (
        <ApprovalCard action={pendingAction} onDecide={decide} />
      )}

      {view === 'memory' && (
        <MemoryPanel onClose={() => setView('home')} onCountChange={setMemoryCount} />
      )}

      {view === 'projects' && <ProjectsPanel onClose={() => setView('home')} />}

      {view === 'mail' && (
        <MailPanel onClose={() => setView('home')} onActionCreated={handlePanelAction} />
      )}

      {view === 'calendar' && (
        <CalendarPanel onClose={() => setView('home')} onActionCreated={handlePanelAction} />
      )}

      {view === 'tasks' && (
        <TasksPanel onClose={() => setView('home')} onDecide={handlePanelAction} />
      )}

      {view === 'trading' && <TradingPanel onClose={() => setView('home')} />}

      {view === 'settings' && (
        <SettingsPanel
          onClose={() => setView('home')}
          settings={{ autoSpeak, voiceUri, speechRate, explanationDepth }}
          onSettingsChanged={(s) => {
            setAutoSpeak(s.autoSpeak);
            setVoiceUri(s.voiceUri);
            setSpeechRate(s.speechRate);
            setExplanationDepth(s.explanationDepth);
          }}
          providerLabel={provider?.label ?? 'unknown'}
        />
      )}
    </div>
  );
}
