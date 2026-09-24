import { expect, test } from '@playwright/test';
import { expectNoHorizontalOverflow, openApp, submitCommand } from './helpers';

test('layout stays usable without horizontal overflow', async ({ page }) => {
  const guard = await openApp(page);
  await expectNoHorizontalOverflow(page);
  // Core controls remain reachable and functional at this viewport.
  await expect(page.getByLabel('Command input')).toBeVisible();
  await submitCommand(page, 'What are we building today?');
  await expect(page.locator('.msg.assistant').last()).toContainText('JARVIS OS');
  await expectNoHorizontalOverflow(page);
  expect(guard.errors).toEqual([]);
});
