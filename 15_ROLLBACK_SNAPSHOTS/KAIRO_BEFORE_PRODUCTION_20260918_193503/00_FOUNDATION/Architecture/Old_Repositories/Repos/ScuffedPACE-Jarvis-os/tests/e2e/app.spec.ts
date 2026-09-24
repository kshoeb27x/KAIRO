import { expect, test } from '@playwright/test';
import { expectNoHorizontalOverflow, openApp, submitCommand } from './helpers';

test.describe('JARVIS OS demo flows (1440x900)', () => {
  test('dashboard loads with honest status and no console errors', async ({ page }) => {
    const guard = await openApp(page);
    await expect(page.getByText('JARVIS OS', { exact: true })).toBeVisible();
    await expect(page.getByText('Demo Provider (no real model)')).toBeVisible();
    await expect(page.getByText('Demo Provider', { exact: true })).toBeVisible();
    // Planned areas are visibly disabled, not pretending to work.
    await expect(page.getByRole('button', { name: /Files/ })).toBeDisabled();
    await expectNoHorizontalOverflow(page);
    expect(guard.errors).toEqual([]);
  });

  test('text request produces a routed, honest response', async ({ page }) => {
    const guard = await openApp(page);
    await submitCommand(page, 'What are we building today?');
    await expect(page.getByText(/Routed to project specialist/)).toBeVisible();
    await expect(page.locator('.msg.assistant').last()).toContainText('JARVIS OS');
    await expect(page.getByText('State: idle')).toBeVisible();
    expect(guard.errors).toEqual([]);
  });

  test('deep reasoning routing is shown and labeled simulated on the demo provider', async ({
    page,
  }) => {
    const guard = await openApp(page);
    await submitCommand(page, 'Evaluate whether this architecture will scale to multiple businesses.');
    await expect(page.getByText(/Routed to deep reasoning/)).toBeVisible();
    await expect(page.locator('.msg.assistant').last()).toContainText(/simulated/i);
    expect(guard.errors).toEqual([]);
  });

  test('mail flow requires approval; approve records a simulated send', async ({ page }) => {
    const guard = await openApp(page);
    await submitCommand(
      page,
      'Draft an email telling my collaborator the prototype will be ready tomorrow.',
    );
    const dialog = page.getByRole('dialog', { name: 'Approval required' });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Simulated');
    await expect(dialog).toContainText('collaborator@example.com');
    await dialog.getByRole('button', { name: 'Approve simulated send' }).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByText(/simulated send approved/i)).toBeVisible();
    expect(guard.errors).toEqual([]);
  });

  test('mail flow cancel records cancellation', async ({ page }) => {
    const guard = await openApp(page);
    await submitCommand(page, 'Draft an email to my collaborator saying the demo moved.');
    const dialog = page.getByRole('dialog', { name: 'Approval required' });
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(page.getByText(/Cancelled — nothing was sent or changed/)).toBeVisible();
    expect(guard.errors).toEqual([]);
  });

  test('memory saves, survives reload with the conversation, and can be inspected', async ({
    page,
  }) => {
    const guard = await openApp(page);
    await submitCommand(page, 'Remember that I prefer approval before any external action.');
    await expect(page.getByText('Preference saved')).toBeVisible();
    await expect(page.locator('.msg.assistant').last()).toContainText(/Saved/);

    // Refresh: conversation, project, and memory must survive.
    await page.reload();
    await expect(page.getByText(/GOOD (MORNING|AFTERNOON|EVENING), FARHAN/i)).toBeVisible();
    await expect(
      page.locator('.msg.user', {
        hasText: 'Remember that I prefer approval before any external action.',
      }),
    ).toBeVisible();
    await expect(page.getByText('JARVIS OS', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Memory' }).click();
    const panel = page.getByRole('dialog', { name: 'Saved memories' });
    await expect(panel).toContainText('I prefer approval before any external action');

    // Forget archives the memory.
    await panel.getByRole('button', { name: 'Forget' }).click();
    await expect(panel).toContainText('Nothing saved yet');
    expect(guard.errors).toEqual([]);
  });

  test('a failing request shows an understandable, recoverable error', async ({ page }) => {
    await openApp(page);
    await page.route('**/api/assistant/stream', (route) => route.abort());
    await submitCommand(page, 'Hello there');
    const banner = page.getByRole('alert');
    await expect(banner).toBeVisible();
    await page.unroute('**/api/assistant/stream');
    await banner.getByRole('button', { name: 'Recover' }).click();
    await expect(page.getByText('State: idle')).toBeVisible();
    // The app still works after recovery.
    await submitCommand(page, 'Good evening');
    await expect(page.locator('.msg.assistant').last()).toContainText(/Demo Provider/i);
  });
});
