import {
  Brain,
  Calendar,
  CheckSquare,
  Files,
  FolderKanban,
  Home,
  Mail,
  MessageSquare,
  Search,
  Settings,
  Wallet,
} from 'lucide-react';
import type { AppState } from '../app/stateMachine';

export type NavView =
  | 'home'
  | 'chat'
  | 'memory'
  | 'projects'
  | 'mail'
  | 'calendar'
  | 'tasks'
  | 'trading'
  | 'settings';

interface NavEntry {
  key: string;
  label: string;
  icon: React.ComponentType<{ size?: number | string }>;
  view?: NavView;
  planned?: boolean;
}

// Unimplemented areas are explicitly marked "Planned" and disabled — the
// interface never pretends a section works when it doesn't.
const ENTRIES: NavEntry[] = [
  { key: 'home', label: 'Home', icon: Home, view: 'home' },
  { key: 'chat', label: 'Chat', icon: MessageSquare, view: 'chat' },
  { key: 'memory', label: 'Memory', icon: Brain, view: 'memory' },
  { key: 'calendar', label: 'Calendar', icon: Calendar, view: 'calendar' },
  { key: 'mail', label: 'Mail', icon: Mail, view: 'mail' },
  { key: 'projects', label: 'Projects', icon: FolderKanban, view: 'projects' },
  { key: 'tasks', label: 'Tasks', icon: CheckSquare, view: 'tasks' },
  { key: 'trading', label: 'Trading', icon: Wallet, view: 'trading' },
  { key: 'files', label: 'Files', icon: Files, planned: true },
  { key: 'research', label: 'Research', icon: Search, planned: true },
  { key: 'settings', label: 'Settings', icon: Settings, view: 'settings' },
];

interface LeftNavProps {
  view: NavView;
  onNavigate: (view: NavView) => void;
  appState: AppState;
  voiceStatusLabel: string;
}

export function LeftNav({ view, onNavigate, appState, voiceStatusLabel }: LeftNavProps) {
  return (
    <nav className="nav" aria-label="Main navigation">
      <div className="nav-brand">
        <span className="nav-brand-dot" aria-hidden="true" />
        JARVIS
      </div>
      <ul className="nav-list">
        {ENTRIES.map((entry) => {
          const Icon = entry.icon;
          return (
            <li key={entry.key}>
              <button
                type="button"
                className={`nav-item${entry.view === view ? ' active' : ''}`}
                disabled={entry.planned}
                aria-disabled={entry.planned}
                onClick={() => entry.view && onNavigate(entry.view)}
                title={entry.planned ? `${entry.label} — planned for a later phase` : entry.label}
              >
                <Icon size={16} />
                {entry.label}
                {entry.planned && <span className="planned">Planned</span>}
              </button>
            </li>
          );
        })}
      </ul>
      <div className="nav-voice">
        Voice: {appState === 'listening' ? 'listening…' : voiceStatusLabel}
      </div>
    </nav>
  );
}
