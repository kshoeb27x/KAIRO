import { z } from 'zod';

/**
 * Interchange format a future trading bot writes for JARVIS to read.
 * JARVIS only ever *reads* this data — there is no execution path: the
 * 'trade_execute' action type is reserved with NO registered executor, so
 * even an approved trade request fails honestly until the owner explicitly
 * builds and enables one.
 */

export const TRADE_EXECUTION_ACTION_TYPE = 'trade_execute';

export const tradingModeSchema = z.enum(['simulated', 'paper', 'live']);

export const tradingReportSchema = z.object({
  schemaVersion: z.literal(1),
  generatedAt: z.string(),
  bot: z.object({
    name: z.string(),
    strategyVersion: z.string(),
  }),
  mode: tradingModeSchema,
  running: z.boolean(),
  account: z
    .object({
      equity: z.number(),
      currency: z.string(),
      riskExposurePct: z.number().min(0),
    })
    .nullable(),
  performance: z
    .object({
      pnlTotal: z.number(),
      pnlPeriod: z.number(),
      maxDrawdownPct: z.number(),
      winRatePct: z.number().min(0).max(100),
      sampleTrades: z.number().int().nonnegative(),
    })
    .nullable(),
  recentTrades: z
    .array(
      z.object({
        time: z.string(),
        symbol: z.string(),
        side: z.enum(['buy', 'sell', 'long', 'short']),
        quantity: z.number(),
        entry: z.number().nullable(),
        exit: z.number().nullable(),
        pnl: z.number().nullable(),
        reason: z.string().optional(),
      }),
    )
    .max(100)
    .default([]),
  recentDecisions: z.array(z.object({ time: z.string(), summary: z.string() })).max(100).default([]),
  errors: z.array(z.string()).max(50).default([]),
  warnings: z.array(z.string()).max(50).default([]),
  strategyChanges: z.array(z.object({ time: z.string(), summary: z.string() })).max(50).default([]),
});

export type TradingReport = z.infer<typeof tradingReportSchema>;
export type TradingMode = z.infer<typeof tradingModeSchema>;

/** What the UI and JARVIS receive. Honest about connection and data quality. */
export interface TradingStatus {
  connected: boolean;
  /** Human setup instructions when not connected. */
  setupMessage: string | null;
  report: TradingReport | null;
  assessment: TradingAssessment | null;
}

export interface TradingAssessment {
  headline: string;
  modeLabel: string;
  /** Fewer than this many trades → profitability claims are refused. */
  insufficientData: boolean;
  /** Report older than the staleness window. */
  stale: boolean;
  attention: string[];
}

/** Adapter boundary so a real bot (files, SQLite, HTTP, WebSocket) can plug in later. */
export interface TradingMonitorAdapter {
  id: string;
  label: string;
  describeSource(): string;
  fetchStatus(): Promise<TradingStatus>;
}
