import { useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';
import {
  listRegisteredProjects,
  refreshRegisteredProject,
  registerProject,
  unregisterProject,
  type RegisteredProject,
} from '../../services/api';

interface ProjectsPanelProps {
  onClose: () => void;
}

/**
 * Project inspection dashboard. Registered directories are read-only:
 * JARVIS scans them (secrets and build output excluded), profiles them, and
 * can then explain them in chat. Nothing here ever edits project files.
 */
export function ProjectsPanel({ onClose }: ProjectsPanelProps) {
  const [projects, setProjects] = useState<RegisteredProject[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pathInput, setPathInput] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = (): void => {
    listRegisteredProjects()
      .then(setProjects)
      .catch(() => setError('Could not load registered projects.'));
  };
  useEffect(refresh, []);

  const register = async (): Promise<void> => {
    if (!pathInput.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await registerProject(pathInput.trim());
      setPathInput('');
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not register that directory.');
    } finally {
      setBusy(false);
    }
  };

  const reinspect = async (id: string): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await refreshRegisteredProject(id);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not re-inspect that project.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string): Promise<void> => {
    try {
      await unregisterProject(id);
      refresh();
    } catch {
      setError('Could not unregister that project.');
    }
  };

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Projects">
      <div className="panel">
        <header>
          <h2>Projects — read-only inspection</h2>
          <button type="button" className="btn" onClick={onClose} aria-label="Close projects panel">
            <X size={14} />
          </button>
        </header>

        <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
          <input
            className="command-input"
            placeholder="Absolute folder path, e.g. C:\Projects\my-app"
            aria-label="Project directory path"
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void register()}
            style={{ flex: '1 1 260px' }}
          />
          <button type="button" className="btn primary" disabled={busy} onClick={() => void register()}>
            Register
          </button>
        </div>
        <p style={{ color: 'var(--text-dim)', fontSize: 12, marginTop: 0 }}>
          Registered folders are scanned read-only (secrets, .env files, and build output are
          skipped). Ask JARVIS about a project by name — e.g. “What is {`{project}`} and what
          changed recently?” JARVIS never edits project files.
        </p>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        {projects === null ? (
          <p>Loading…</p>
        ) : projects.length === 0 ? (
          <p style={{ color: 'var(--text-dim)' }}>
            No projects registered yet. Add a local folder above to let JARVIS understand it.
          </p>
        ) : (
          <ul className="memory-list">
            {projects.map((project) => (
              <li key={project.id} className="memory-item" style={{ alignItems: 'flex-start' }}>
                <span
                  className="kind"
                  style={{
                    color:
                      project.profile?.health.level === 'good'
                        ? 'var(--ok, #3dd68c)'
                        : project.profile?.health.level === 'attention'
                          ? 'var(--warn, #e8b339)'
                          : 'var(--text-dim)',
                  }}
                >
                  {project.profile?.health.level ?? 'unknown'}
                </span>
                <span style={{ flex: 1 }}>
                  <strong>{project.name}</strong>{' '}
                  <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>
                    {project.profile?.projectType ?? 'Unknown type'}
                    {project.profile?.git.isRepo
                      ? ` · ${project.profile.git.branch ?? 'detached'} · ${project.profile.git.dirtyFiles ?? 0} uncommitted`
                      : ' · no git'}
                    {project.profile ? ` · ${project.profile.fileCount} files` : ''}
                  </span>
                  <span style={{ display: 'block', fontSize: 12 }}>
                    {project.profile?.description ?? 'Not inspected yet.'}
                  </span>
                  {project.profile && project.profile.health.notes.length > 0 && (
                    <span style={{ display: 'block', fontSize: 11, color: 'var(--warn, #e8b339)' }}>
                      {project.profile.health.notes.join(' ')}
                    </span>
                  )}
                  <span style={{ display: 'block', fontSize: 10, color: 'var(--text-dim)' }}>
                    {project.rootPath} · inspected{' '}
                    {project.lastInspectedAt ? project.lastInspectedAt.slice(0, 16).replace('T', ' ') : 'never'}
                  </span>
                </span>
                <button
                  type="button"
                  className="btn"
                  disabled={busy}
                  onClick={() => void reinspect(project.id)}
                  aria-label={`Re-inspect ${project.name}`}
                >
                  <RefreshCw size={13} />
                </button>
                <button type="button" className="btn forget" onClick={() => void remove(project.id)}>
                  Unregister
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
