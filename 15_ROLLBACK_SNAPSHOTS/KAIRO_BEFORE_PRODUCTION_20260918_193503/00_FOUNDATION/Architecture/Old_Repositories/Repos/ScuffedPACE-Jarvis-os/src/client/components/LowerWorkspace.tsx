import type { PendingAction, Project } from '../../shared/types';

interface LowerWorkspaceProps {
  project: Project | null;
  pendingActions: PendingAction[];
  memoryCount: number;
}

/**
 * Context cards. Seeded demonstration content is explicitly labeled "Demo";
 * counts shown here derive from real database state.
 */
export function LowerWorkspace({ project, pendingActions, memoryCount }: LowerWorkspaceProps) {
  return (
    <div className="workspace" aria-label="Workspace overview">
      <div className="card">
        <h3>
          Active project <span className="tag demo">Demo seed</span>
        </h3>
        {project ? (
          <>
            <p className="value">{project.name}</p>
            <p>{project.summary}</p>
          </>
        ) : (
          <p>No active project.</p>
        )}
      </div>
      <div className="card">
        <h3>Pending approvals</h3>
        <p className="value">{pendingActions.length}</p>
        <p>
          {pendingActions.length > 0
            ? 'A simulated action is waiting for your decision.'
            : 'Nothing awaits approval.'}
        </p>
      </div>
      <div className="card">
        <h3>Saved memories</h3>
        <p className="value">{memoryCount}</p>
        <p>Explicit memories you asked JARVIS to keep. Inspect them under Memory.</p>
      </div>
    </div>
  );
}
