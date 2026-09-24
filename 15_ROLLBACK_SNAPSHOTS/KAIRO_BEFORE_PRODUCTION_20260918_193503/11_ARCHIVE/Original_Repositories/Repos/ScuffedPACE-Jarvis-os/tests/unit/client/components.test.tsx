// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActivityRail } from '../../../src/client/features/activity/ActivityRail';
import { LeftNav } from '../../../src/client/components/LeftNav';
import { ApprovalCard } from '../../../src/client/features/permissions/ApprovalCard';
import type { PendingAction, ProviderStatus } from '../../../src/shared/types';

afterEach(cleanup);

const railDefaults = {
  events: [],
  serverHealthy: true,
  speechRecognitionSupported: true,
  speechSynthesisSupported: true,
  schemaVersion: 1,
};

describe('ActivityRail provider truthfulness', () => {
  it('labels the mock provider as Demo — never as Claude connected', () => {
    const provider: ProviderStatus = {
      mode: 'mock',
      label: 'Demo Provider (no real model connected)',
      configured: true,
      configurationError: null,
      fastModel: 'demo-fast',
      deepModel: 'demo-deep-simulated',
    };
    render(<ActivityRail {...railDefaults} provider={provider} />);
    expect(screen.getByText('Demo Provider')).toBeInTheDocument();
    expect(screen.queryByText(/Claude \(/)).not.toBeInTheDocument();
  });

  it('shows Not configured for anthropic mode without credentials', () => {
    const provider: ProviderStatus = {
      mode: 'anthropic',
      label: 'Anthropic Claude',
      configured: false,
      configurationError: 'ANTHROPIC_API_KEY is not set.',
      fastModel: null,
      deepModel: null,
    };
    render(<ActivityRail {...railDefaults} provider={provider} />);
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });
});

describe('LeftNav planned labeling', () => {
  it('disables unimplemented areas and marks them Planned', () => {
    render(
      <LeftNav view="home" onNavigate={() => undefined} appState="idle" voiceStatusLabel="ready" />,
    );
    const files = screen.getByRole('button', { name: /Files/ });
    expect(files).toBeDisabled();
    expect(screen.getAllByText('Planned').length).toBe(2); // Files, Research
    expect(screen.getByRole('button', { name: /Research/ })).toBeDisabled();
    for (const name of ['Home', 'Mail', 'Calendar', 'Projects', 'Tasks', 'Trading', 'Settings']) {
      expect(screen.getByRole('button', { name: new RegExp(name) })).toBeEnabled();
    }
  });
});

describe('ApprovalCard', () => {
  const action: PendingAction = {
    id: '3b241101-e2bb-4255-8caf-4136c566a962',
    requestId: '3b241101-e2bb-4255-8caf-4136c566a963',
    toolName: 'mock_mail',
    actionType: 'simulated_send',
    payload: { to: 'collaborator@example.com', subject: 'Update', body: 'Ready tomorrow.' },
    summary: 'Record a simulated send of "Update" to collaborator@example.com',
    target: 'Simulated mail (no real account connected)',
    reason: 'You asked JARVIS to draft this email.',
    consequences: 'Nothing is actually sent in this prototype.',
    status: 'pending',
    expiresAt: new Date(Date.now() + 60000).toISOString(),
    createdAt: new Date().toISOString(),
    decidedAt: null,
    decidedBy: null,
    executedAt: null,
    executionError: null,
  };

  it('shows the stored draft, is labeled simulated, and records decisions', async () => {
    const onDecide = vi.fn().mockResolvedValue(undefined);
    render(<ApprovalCard action={action} onDecide={onDecide} />);
    expect(screen.getAllByText(/collaborator@example.com/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Ready tomorrow/)).toBeInTheDocument();
    expect(screen.getAllByText(/simulated/i).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('button', { name: /Approve simulated send/ }));
    expect(onDecide).toHaveBeenCalledWith('approve');
  });

  it('surfaces decision failures without pretending success', async () => {
    const onDecide = vi.fn().mockRejectedValue(new Error('This action was already decided'));
    render(<ApprovalCard action={action} onDecide={onDecide} />);
    await userEvent.click(screen.getByRole('button', { name: /Cancel/ }));
    expect(await screen.findByText(/already decided/)).toBeInTheDocument();
  });
});
