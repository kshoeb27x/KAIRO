import { expect, test, type Page } from '@playwright/test';
import { attachConsoleGuard } from './helpers';

/**
 * Browser-level voice pipeline verification with mocked Web Speech APIs.
 * Covers everything that does not require a physical microphone or speaker:
 * hold-to-talk lifecycle, exactly-one automatic submission, spoken replies,
 * rate settings, interruption, permission denial, and the sensitive-speech
 * guard. Real audio capture and audible quality remain owner-only checks.
 */

declare global {
  interface Window {
    __rec: {
      onresult: ((event: unknown) => void) | null;
      onend: (() => void) | null;
      onerror: ((event: { error: string }) => void) | null;
    } | null;
    __spoken: Array<{ text: string; rate: number }>;
    __cancelCalls: number;
    __holdSpeech: boolean;
  }
}

async function installSpeechMocks(page: Page, options: { denyMic?: boolean } = {}): Promise<void> {
  await page.addInitScript(({ denyMic }) => {
    // --- SpeechRecognition mock (test drives events via window.__rec) ---
    window.__rec = null;
    class FakeRecognition {
      lang = '';
      continuous = false;
      interimResults = false;
      maxAlternatives = 1;
      onresult: ((event: unknown) => void) | null = null;
      onerror: ((event: { error: string }) => void) | null = null;
      onend: (() => void) | null = null;
      start(): void {
        window.__rec = this as unknown as Window['__rec'];
      }
      stop(): void {
        setTimeout(() => this.onend?.(), 10);
      }
      abort(): void {
        this.onresult = null;
        this.onerror = null;
        this.onend = null;
      }
    }
    // Chromium exposes both the unprefixed and webkit-prefixed constructors;
    // the app prefers the unprefixed one, so both must point at the fake.
    (window as unknown as Record<string, unknown>).SpeechRecognition = FakeRecognition;
    (window as unknown as Record<string, unknown>).webkitSpeechRecognition = FakeRecognition;

    // --- Microphone / metering mocks ---
    const fakeStream = { getTracks: () => [{ stop: () => undefined }] };
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: () =>
          denyMic
            ? Promise.reject(new Error('denied'))
            : Promise.resolve(fakeStream as unknown as MediaStream),
      },
    });
    class FakeAudioContext {
      createMediaStreamSource(): { connect: () => void } {
        return { connect: () => undefined };
      }
      createAnalyser(): { fftSize: number; getByteTimeDomainData: (a: Uint8Array) => void } {
        return { fftSize: 512, getByteTimeDomainData: () => undefined };
      }
      close(): Promise<void> {
        return Promise.resolve();
      }
    }
    (window as unknown as Record<string, unknown>).AudioContext = FakeAudioContext;

    // --- speechSynthesis mock ---
    window.__spoken = [];
    window.__cancelCalls = 0;
    window.__holdSpeech = false;
    class FakeUtterance {
      text: string;
      rate = 1;
      voice: unknown = null;
      onstart: (() => void) | null = null;
      onboundary: (() => void) | null = null;
      onend: (() => void) | null = null;
      onerror: ((e: { error: string }) => void) | null = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    (window as unknown as Record<string, unknown>).SpeechSynthesisUtterance = FakeUtterance;
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: {
        speaking: false,
        pending: false,
        paused: false,
        getVoices: () => [],
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        resume: () => undefined,
        cancel(): void {
          window.__cancelCalls += 1;
        },
        speak(utterance: InstanceType<typeof FakeUtterance>): void {
          window.__spoken.push({ text: utterance.text, rate: utterance.rate });
          setTimeout(() => utterance.onstart?.(), 0);
          if (!window.__holdSpeech) setTimeout(() => utterance.onend?.(), 60);
        },
      },
    });
  }, { denyMic: options.denyMic ?? false });
}

async function openVoiceApp(page: Page, autoSpeak = true) {
  const guard = attachConsoleGuard(page);
  await page.request.put('/api/settings', { data: { autoSpeak, speechRate: 1 } });
  await page.goto('/');
  await expect(page.getByText(/GOOD (MORNING|AFTERNOON|EVENING), FARHAN/i)).toBeVisible();
  return guard;
}

function emitResult(page: Page, transcript: string, isFinal: boolean): Promise<void> {
  return page.evaluate(
    ({ transcript, isFinal }) => {
      window.__rec?.onresult?.({
        results: [Object.assign([{ transcript }], { isFinal })],
      });
    },
    { transcript, isFinal },
  );
}

test.describe('voice pipeline (mocked speech APIs)', () => {
  test('hold-to-talk transcribes, auto-submits exactly once, and speaks the reply', async ({
    page,
  }) => {
    await installSpeechMocks(page);
    const guard = await openVoiceApp(page);
    const userMessagesBefore = await page.locator('.msg.user').count();

    const mic = page.locator('button.mic');
    await mic.dispatchEvent('pointerdown', { pointerId: 1 });
    await expect(page.getByText('Listening…').first()).toBeVisible();

    await emitResult(page, 'what are we building', false);
    await expect(page.locator('.transcript-live')).toContainText('what are we building');
    await emitResult(page, 'what are we building today', true);
    await mic.dispatchEvent('pointerup', { pointerId: 1 });

    // Exactly one user message, no Send click, and a routed reply.
    await expect(page.locator('.msg.assistant').nth(0)).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.msg.user')).toHaveCount(userMessagesBefore + 1);
    await expect(page.locator('.msg.user').last()).toContainText('what are we building today');

    // The reply was spoken exactly once at the configured rate.
    await expect
      .poll(async () => page.evaluate(() => window.__spoken.length), { timeout: 5000 })
      .toBe(1);
    const spoken = await page.evaluate(() => window.__spoken[0]);
    expect(spoken!.rate).toBe(1);
    await expect(page.getByText('State: idle')).toBeVisible();
    expect(guard.errors).toEqual([]);
  });

  test('Esc interrupts an active spoken reply and returns to ready', async ({ page }) => {
    await installSpeechMocks(page);
    await openVoiceApp(page);
    await page.evaluate(() => {
      window.__holdSpeech = true; // keep the utterance "speaking"
    });
    const input = page.getByLabel('Command input');
    await input.fill('What are we building today?');
    await input.press('Enter');
    await expect(page.getByText('State: speaking')).toBeVisible({ timeout: 15000 });

    const cancelsBefore = await page.evaluate(() => window.__cancelCalls);
    await page.keyboard.press('Escape');
    await expect(page.getByText('State: idle')).toBeVisible();
    const cancelsAfter = await page.evaluate(() => window.__cancelCalls);
    expect(cancelsAfter).toBeGreaterThan(cancelsBefore);
    // No stuck speaking state and nothing extra was spoken.
    expect(await page.evaluate(() => window.__spoken.length)).toBe(1);
  });

  test('replies that look sensitive are never spoken aloud', async ({ page }) => {
    await installSpeechMocks(page);
    await openVoiceApp(page);
    const input = page.getByLabel('Command input');
    // The demo provider echoes the input, so the reply contains the password.
    await input.fill('The wifi password is hunter2, what do you think?');
    await input.press('Enter');
    await expect(page.locator('.msg.assistant').last()).toContainText('hunter2', {
      timeout: 15000,
    });
    await expect(page.getByText(/didn't read that reply aloud/i)).toBeVisible();
    expect(await page.evaluate(() => window.__spoken.length)).toBe(0);
  });

  test('auto-speak off means nothing is spoken', async ({ page }) => {
    await installSpeechMocks(page);
    await openVoiceApp(page, false);
    const input = page.getByLabel('Command input');
    await input.fill('Good evening');
    await input.press('Enter');
    await expect(page.locator('.msg.assistant').last()).toBeVisible({ timeout: 15000 });
    expect(await page.evaluate(() => window.__spoken.length)).toBe(0);
  });

  test('microphone denial shows an honest, recoverable error and typing still works', async ({
    page,
  }) => {
    await installSpeechMocks(page, { denyMic: true });
    await openVoiceApp(page);
    const mic = page.locator('button.mic');
    await mic.dispatchEvent('pointerdown', { pointerId: 1 });
    await expect(page.getByText(/Microphone access was denied/)).toBeVisible();
    await page.getByRole('button', { name: 'Recover' }).click();
    const input = page.getByLabel('Command input');
    await input.fill('typing still works');
    await input.press('Enter');
    await expect(page.locator('.msg.user').last()).toContainText('typing still works');
  });

  test('speech-rate setting changes the spoken rate and preview works', async ({ page }) => {
    await installSpeechMocks(page);
    await openVoiceApp(page);
    await page.getByRole('button', { name: /Settings/ }).click();
    const slider = page.getByLabel('Speaking rate');
    await slider.fill('1.5');
    await expect(page.getByText('1.5×')).toBeVisible();
    await page.getByRole('button', { name: 'Preview' }).click();
    await expect
      .poll(async () => page.evaluate(() => window.__spoken.at(-1)?.rate))
      .toBe(1.5);
    await page.getByRole('button', { name: 'Close settings panel' }).click();

    const input = page.getByLabel('Command input');
    await input.fill('What are we building today?');
    await input.press('Enter');
    await expect
      .poll(async () => page.evaluate(() => window.__spoken.at(-1)?.text), { timeout: 15000 })
      .toContain('building');
    expect(await page.evaluate(() => window.__spoken.at(-1)?.rate)).toBe(1.5);
  });
});
