import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { assess, createFileTradingAdapter, MIN_TRADES_FOR_CLAIMS } from '../../../src/server/trading/fileAdapter';
import { tradingReportSchema, type TradingReport } from '../../../src/server/trading/types';

const cleanups: Array<() => void> = [];
afterEach(() => {
  while (cleanups.length > 0) cleanups.pop()?.();
});

function tempFile(content: string): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jarvis-trading-'));
  cleanups.push(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'report.json');
  fs.writeFileSync(file, content);
  return file;
}

const sample = fs.readFileSync(path.resolve('data/trading-sample.json'), 'utf8');

function sampleReport(overrides: Partial<TradingReport> = {}): TradingReport {
  return { ...tradingReportSchema.parse(JSON.parse(sample)), ...overrides };
}

describe('trading report schema and sample', () => {
  it('the committed sample matches the documented interface', () => {
    const report = tradingReportSchema.parse(JSON.parse(sample));
    expect(report.bot.name).toBe('SampleBot');
    expect(report.mode).toBe('simulated');
  });
});

describe('file trading adapter', () => {
  it('reports an honest not-connected state with setup instructions', async () => {
    const status = await createFileTradingAdapter(null).fetchStatus();
    expect(status.connected).toBe(false);
    expect(status.setupMessage).toContain('TRADING_REPORT_PATH');
    expect(status.report).toBeNull();
  });

  it('reports a missing file honestly', async () => {
    const status = await createFileTradingAdapter('C:\\missing\\report.json').fetchStatus();
    expect(status.connected).toBe(false);
    expect(status.setupMessage).toContain('not found');
  });

  it('refuses malformed reports instead of guessing', async () => {
    const file = tempFile('{"schemaVersion": 1, "nonsense": true}');
    const status = await createFileTradingAdapter(file).fetchStatus();
    expect(status.connected).toBe(false);
    expect(status.setupMessage).toContain('does not match');
  });

  it('reads and assesses a valid report', async () => {
    const file = tempFile(sample);
    const status = await createFileTradingAdapter(file).fetchStatus();
    expect(status.connected).toBe(true);
    expect(status.report?.bot.name).toBe('SampleBot');
    expect(status.assessment?.modeLabel).toContain('Simulated');
  });
});

describe('trading assessment honesty', () => {
  it('refuses profitability claims below the sample threshold', () => {
    const report = sampleReport();
    expect(report.performance!.sampleTrades).toBeLessThan(MIN_TRADES_FOR_CLAIMS);
    const assessment = assess(report, new Date('2026-07-14T12:05:00Z'));
    expect(assessment.insufficientData).toBe(true);
    expect(assessment.headline).toContain('Not enough closed trades');
    expect(assessment.headline).not.toContain('win rate');
  });

  it('states performance plainly when the sample is sufficient', () => {
    const report = sampleReport({
      performance: {
        pnlTotal: 500,
        pnlPeriod: -20,
        maxDrawdownPct: 6,
        winRatePct: 51,
        sampleTrades: 120,
      },
    });
    const assessment = assess(report, new Date('2026-07-14T12:05:00Z'));
    expect(assessment.insufficientData).toBe(false);
    expect(assessment.headline).toContain('win rate 51%');
    expect(assessment.headline).toContain('-20');
  });

  it('flags live mode, stopped bots, stale data, errors, and high risk', () => {
    const report = sampleReport({
      mode: 'live',
      running: false,
      errors: ['exchange rejected order'],
      account: { equity: 5000, currency: 'USD', riskExposurePct: 40 },
    });
    const assessment = assess(report, new Date('2026-07-15T12:00:00Z'));
    const joined = assessment.attention.join(' | ');
    expect(joined).toContain('LIVE');
    expect(joined).toContain('not running');
    expect(joined).toContain('stale');
    expect(joined).toContain('exchange rejected order');
    expect(joined).toContain('40%');
    expect(assessment.modeLabel).toContain('real money');
  });

  it('distinguishes the three trading modes clearly', () => {
    const now = new Date('2026-07-14T12:05:00Z');
    expect(assess(sampleReport({ mode: 'simulated' }), now).modeLabel).toContain('Simulated');
    expect(assess(sampleReport({ mode: 'paper' }), now).modeLabel).toContain('no real money');
    expect(assess(sampleReport({ mode: 'live' }), now).modeLabel).toContain('real money');
  });
});
