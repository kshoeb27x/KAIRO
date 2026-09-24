import { expect, type Page } from '@playwright/test';

export interface ConsoleGuard {
  errors: string[];
}

/** Collects console errors and page errors so tests can assert a clean console. */
export function attachConsoleGuard(page: Page): ConsoleGuard {
  const guard: ConsoleGuard = { errors: [] };
  page.on('console', (message) => {
    if (message.type() === 'error') guard.errors.push(message.text());
  });
  page.on('pageerror', (error) => guard.errors.push(error.message));
  return guard;
}

export async function openApp(page: Page): Promise<ConsoleGuard> {
  const guard = attachConsoleGuard(page);
  // Auto-speak off during automated runs: headless synthesis never fires
  // events, and the tests assert state transitions, not audio.
  await page.request.put('/api/settings', { data: { autoSpeak: false } });
  await page.goto('/');
  await expect(page.getByText(/GOOD (MORNING|AFTERNOON|EVENING), FARHAN/i)).toBeVisible();
  return guard;
}

export async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const el = document.scrollingElement ?? document.documentElement;
    return el.scrollWidth - el.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(0);
}

export async function submitCommand(page: Page, text: string): Promise<void> {
  const input = page.getByLabel('Command input');
  await input.fill(text);
  await input.press('Enter');
}
