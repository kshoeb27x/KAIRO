import fs from 'node:fs';
import path from 'node:path';
import {
  tradingReportSchema,
  type TradingAssessment,
  type TradingMonitorAdapter,
  type TradingReport,
  type TradingStatus,
} from './types';

/**
 * Reads a bot-written JSON report file (see docs/TRADING_MONITOR_INTERFACE.md).
 * Read-only, bounded, validated; a missing or malformed file is reported
 * honestly with setup instructions instead of fake data.
 */

const MAX_REPORT_BYTES = 1024 * 1024;
const STALE_AFTER_MS = 15 * 60 * 1000;
/** Below this many closed trades, profitability statements are refused. */
export const MIN_TRADES_FOR_CLAIMS = 20;

const SETUP_MESSAGE =
  'No trading bot is connected. Point TRADING_REPORT_PATH in .env at the JSON status ' +
  'report your bot writes (format: docs/TRADING_MONITOR_INTERFACE.md), then restart JARVIS.';

export function createFileTradingAdapter(reportPath: string | null): TradingMonitorAdapter {
  return {
    id: 'file_report',
    label: 'Trading report file',
    describeSource() {
      return reportPath ? `JSON report at ${reportPath}` : 'not configured';
    },
    async fetchStatus(): Promise<TradingStatus> {
      if (!reportPath) {
        return { connected: false, setupMessage: SETUP_MESSAGE, report: null, assessment: null };
      }
      if (!path.isAbsolute(reportPath)) {
        return {
          connected: false,
          setupMessage: 'TRADING_REPORT_PATH must be an absolute file path.',
          report: null,
          assessment: null,
        };
      }
      let raw: string;
      try {
        const stat = fs.statSync(reportPath);
        if (stat.size > MAX_REPORT_BYTES) {
          return {
            connected: false,
            setupMessage: `The trading report is larger than ${MAX_REPORT_BYTES / 1024} KB — refusing to read it.`,
            report: null,
            assessment: null,
          };
        }
        raw = fs.readFileSync(reportPath, 'utf8');
      } catch {
        return {
          connected: false,
          setupMessage: `The trading report file was not found or is unreadable: ${reportPath}. ${SETUP_MESSAGE}`,
          report: null,
          assessment: null,
        };
      }
      let report: TradingReport;
      try {
        report = tradingReportSchema.parse(JSON.parse(raw));
      } catch {
        return {
          connected: false,
          setupMessage:
            'The trading report file exists but does not match the documented format ' +
            '(docs/TRADING_MONITOR_INTERFACE.md). JARVIS will not guess at trading data.',
          report: null,
          assessment: null,
        };
      }
      return { connected: true, setupMessage: null, report, assessment: assess(report) };
    },
  };
}

export function assess(report: TradingReport, now: Date = new Date()): TradingAssessment {
  const insufficientData = (report.performance?.sampleTrades ?? 0) < MIN_TRADES_FOR_CLAIMS;
  const generated = Date.parse(report.generatedAt);
  const stale = !Number.isFinite(generated) || now.getTime() - generated > STALE_AFTER_MS;

  const attention: string[] = [];
  if (report.mode === 'live') attention.push('The bot reports LIVE trading with real money.');
  if (!report.running) attention.push('The bot reports that it is not running.');
  if (stale) attention.push('The report is stale — data may be out of date.');
  for (const error of report.errors.slice(0, 5)) attention.push(`Bot error: ${error}`);
  for (const warning of report.warnings.slice(0, 5)) attention.push(`Bot warning: ${warning}`);
  if ((report.account?.riskExposurePct ?? 0) > 25) {
    attention.push(`Risk exposure is ${report.account!.riskExposurePct}% of equity.`);
  }
  if (insufficientData) {
    attention.push(
      `Only ${report.performance?.sampleTrades ?? 0} closed trades — far too few to judge profitability.`,
    );
  }
  if (report.strategyChanges.length > 0) {
    attention.push(`Strategy changed recently: ${report.strategyChanges[0]!.summary}`);
  }

  const modeLabel =
    report.mode === 'live'
      ? 'LIVE trading (real money)'
      : report.mode === 'paper'
        ? 'Paper trading (real prices, no real money)'
        : 'Simulated (backtest/synthetic data)';

  const perf = report.performance;
  const headline = perf
    ? `${report.bot.name} (${report.bot.strategyVersion}) is ${report.running ? 'running' : 'stopped'} in ${modeLabel}. ` +
      (insufficientData
        ? 'Not enough closed trades yet to make any profitability claim.'
        : `Period PnL ${perf.pnlPeriod >= 0 ? '+' : ''}${perf.pnlPeriod}, total ${perf.pnlTotal >= 0 ? '+' : ''}${perf.pnlTotal}, ` +
          `max drawdown ${perf.maxDrawdownPct}%, win rate ${perf.winRatePct}% over ${perf.sampleTrades} trades.`)
    : `${report.bot.name} is ${report.running ? 'running' : 'stopped'} in ${modeLabel}; no performance data was reported.`;

  return { headline, modeLabel, insufficientData, stale, attention };
}
