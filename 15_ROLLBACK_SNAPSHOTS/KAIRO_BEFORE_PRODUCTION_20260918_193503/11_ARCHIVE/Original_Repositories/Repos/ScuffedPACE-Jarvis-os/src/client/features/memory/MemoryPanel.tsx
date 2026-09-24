import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import type { Memory } from '../../../shared/types';
import {
  ApiRequestError,
  archiveMemory,
  createMemory,
  listMemories,
  updateMemory,
} from '../../services/api';

interface MemoryPanelProps {
  onClose: () => void;
  onCountChange: (count: number) => void;
}

const KIND_OPTIONS: Memory['kind'][] = [
  'preference',
  'personal_fact',
  'project_fact',
  'decision',
  'task',
  'lesson',
  'note',
];

/**
 * Inspectable explicit memory. "Forget" archives (the record is excluded from
 * context but never destroyed). Sensitive values require a deliberate
 * confirmation and duplicates require an explicit override — nothing is
 * stored silently.
 */
export function MemoryPanel({ onClose, onCountChange }: MemoryPanelProps) {
  const [memories, setMemories] = useState<Memory[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newKind, setNewKind] = useState<Memory['kind']>('note');
  const [confirmPrompt, setConfirmPrompt] = useState<{
    message: string;
    flag: 'confirmSensitive' | 'allowDuplicate';
  } | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const searchTimer = useRef(0);

  const refresh = (q = query): void => {
    listMemories(q.trim() || undefined)
      .then((items) => {
        setMemories(items);
        if (!q.trim()) onCountChange(items.length);
      })
      .catch(() => setError('Could not load memories from the server.'));
  };

  useEffect(() => {
    refresh('');
  }, []); // load once on open — refresh is stable for the panel's lifetime

  const onSearch = (value: string): void => {
    setQuery(value);
    window.clearTimeout(searchTimer.current);
    searchTimer.current = window.setTimeout(() => refresh(value), 250);
  };

  const add = async (flags: { confirmSensitive?: boolean; allowDuplicate?: boolean } = {}) => {
    const value = newValue.trim();
    if (!value) return;
    setError(null);
    setConfirmPrompt(null);
    try {
      await createMemory({ kind: newKind, value, ...flags });
      setNewValue('');
      refresh();
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === 'sensitive_confirmation_required') {
        setConfirmPrompt({ message: err.message, flag: 'confirmSensitive' });
      } else if (err instanceof ApiRequestError && err.code === 'duplicate_memory') {
        setConfirmPrompt({ message: err.message, flag: 'allowDuplicate' });
      } else {
        setError(err instanceof Error ? err.message : 'Could not save the memory.');
      }
    }
  };

  const saveEdit = async (id: string): Promise<void> => {
    try {
      await updateMemory(id, { value: editValue.trim() });
      setEditingId(null);
      refresh();
    } catch {
      setError('Could not update that memory.');
    }
  };

  const forget = async (id: string): Promise<void> => {
    try {
      await archiveMemory(id);
      refresh();
    } catch {
      setError('Could not archive that memory.');
    }
  };

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Saved memories">
      <div className="panel">
        <header>
          <h2>Memory — explicit saved facts</h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close memory panel">
            <X size={14} />
          </button>
        </header>

        <input
          type="search"
          className="command-input"
          placeholder="Search memories…"
          aria-label="Search memories"
          value={query}
          onChange={(e) => onSearch(e.target.value)}
          style={{ marginBottom: 10 }}
        />

        <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
          <input
            className="command-input"
            placeholder="Add something for JARVIS to remember…"
            aria-label="New memory"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void add()}
            style={{ flex: '1 1 240px' }}
          />
          <select
            aria-label="Memory kind"
            value={newKind}
            onChange={(e) => setNewKind(e.target.value as Memory['kind'])}
            className="btn"
          >
            {KIND_OPTIONS.map((k) => (
              <option key={k} value={k}>
                {k.replace('_', ' ')}
              </option>
            ))}
          </select>
          <button type="button" className="btn primary" onClick={() => void add()}>
            Save
          </button>
        </div>

        {confirmPrompt && (
          <div className="error-banner" role="alertdialog" style={{ marginBottom: 10 }}>
            <span>{confirmPrompt.message}</span>
            <button
              type="button"
              className="btn"
              onClick={() => void add({ [confirmPrompt.flag]: true })}
            >
              Save anyway
            </button>
            <button type="button" className="btn" onClick={() => setConfirmPrompt(null)}>
              Don't save
            </button>
          </div>
        )}
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        {memories === null ? (
          <p>Loading…</p>
        ) : memories.length === 0 ? (
          <p style={{ color: 'var(--text-dim)' }}>
            {query.trim()
              ? 'No memories match that search.'
              : 'Nothing saved yet. Say or type “Remember that …” and it will appear here after it is actually persisted.'}
          </p>
        ) : (
          <ul className="memory-list">
            {memories.map((memory) => (
              <li key={memory.id} className="memory-item">
                <span className="kind">{memory.kind.replace('_', ' ')}</span>
                {editingId === memory.id ? (
                  <>
                    <input
                      className="command-input"
                      aria-label="Edit memory value"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && void saveEdit(memory.id)}
                      style={{ flex: 1 }}
                    />
                    <button type="button" className="btn" onClick={() => void saveEdit(memory.id)}>
                      Save
                    </button>
                    <button type="button" className="btn" onClick={() => setEditingId(null)}>
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <span style={{ flex: 1 }}>
                      {memory.value}
                      <span style={{ display: 'block', fontSize: 10, color: 'var(--text-dim)' }}>
                        {memory.source.replace('_', ' ')}
                        {memory.sourceDetail ? ` · ${memory.sourceDetail}` : ''} ·{' '}
                        {memory.createdAt.slice(0, 10)}
                        {memory.sensitive ? ' · sensitive (owner-confirmed)' : ''}
                      </span>
                    </span>
                    <button
                      type="button"
                      className="btn"
                      onClick={() => {
                        setEditingId(memory.id);
                        setEditValue(memory.value);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn forget"
                      onClick={() => void forget(memory.id)}
                    >
                      Forget
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
