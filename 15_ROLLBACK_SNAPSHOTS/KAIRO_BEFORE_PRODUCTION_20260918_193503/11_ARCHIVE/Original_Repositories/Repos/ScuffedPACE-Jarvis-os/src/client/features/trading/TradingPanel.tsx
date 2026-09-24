import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X } from 'lucide-react';

interface TradingPanelProps {
  onClose: () => void;
}

interface TradingStatus {
  connected: boolean;
  setupMessage: string | null;
  report: {
    bot: { name: string; strategyVersion: string };
    mode: string;
    running: boolean;
    generatedAt: string;
    account: { equity: number; currency: string; riskExposurePct: number } | null;
    performance: {
      pnlTotal: number;
      pnlPeriod: number;
      maxDrawdownPct: number;
      winRatePct: number;
      sampleTrades: number;
    } | null;
    recentTrades: Array<{
      time: string;
      symbol: string;
      side: string;
      pnl: number | null;
      reason?: string;
    }>;
    recentDecisions: Array<{ time: string; summary: string }>;
  } | null;
  assessment: {
    headline: string;
    modeLabel: string;
    insufficientData: boolean;
    stale: boolean;
    attention: string[];
  } | null;
}

/**
 * Trading-bot monitor: read-only, honest about connection state, staleness,
 * and data sufficiency. JARVIS cannot trade — no execution path exists.
 */
export function TradingPanel({ onClose }: TradingPanelProps) {
  const [status, setStatus] = useState<TradingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback((): void => {
    fetch('/api/trading/status')
      .then(async (r) => setStatus((await r.json()) as TradingStatus))
      .catch(() => setError('Could not load the trading status.'));
  }, []);
  useEffect(refresh, [refresh]);

  return (
    <div className="panel-overlay" role="dialog" aria-modal="true" aria-label="Trading monitor">
      <div className="panel">
        <header>
          <h2>Trading monitor — read-only</h2>
          <button type="button" className="btn" onClick={refresh} aria-label="Refresh trading status">
            <RefreshCw size={13} />
          </button>
          <button type="button" className="btn" onClick={onClose} aria-label="Close trading panel">
            <X size={14} />
          </button>
        </header>
        {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

        {status === null ? (
          <p>Loading…</p>
        ) : !status.connected ? (
          <p style={{ color: 'var(--text-dim)' }}>{status.setupMessage}</p>
        ) : (
          <>
            <p>
              <strong>{status.assessment?.headline}</strong>
            </p>
            <p style={{ fontSize: 12 }}>
              <span className="kind">{status.assessment?.modeLabel}</span>{' '}
              {status.assessment?.stale && <span className="kind">stale data</span>}{' '}
              <span style={{ color: 'var(--text-dim)' }}>
                report from {status.report?.generatedAt.replace('T', ' ').slice(0, 16)}
              </span>
            </p>
            {status.assessment && status.assessment.attention.length > 0 && (
              <div className="error-banner" role="status">
                <span>
                  {status.assessment.attention.map((a) => (
                    <span key={a} style={{ display: 'block' }}>
                      • {a}
                    </span>
                  ))}
                </span>
              </div>
            )}
            {status.report?.account && (
              <p style={{ fontSize: 12 }}>
                Equity {status.report.account.equity} {status.report.account.currency} · risk
                exposure {status.report.account.riskExposurePct}%
              </p>
            )}
            {status.report && status.report.recentDecisions.length > 0 && (
              <>
                <h3 style={{ fontSize: 13 }}>Recent decisions</h3>
                <ul style={{ fontSize: 12, paddingLeft: 18 }}>
                  {status.report.recentDecisions.slice(0, 8).map((d) => (
                    <li key={`${d.time}-${d.summary}`}>
                      {d.time.replace('T', ' ').slice(0, 16)} — {d.summary}
                    </li>
                  ))}
                </ul>
              </>
            )}
            {status.report && status.report.recentTrades.length > 0 && (
              <>
                <h3 style={{ fontSize: 13 }}>Recent trades</h3>
                <ul style={{ fontSize: 12, paddingLeft: 18 }}>
                  {status.report.recentTrades.slice(0, 8).map((t) => (
                    <li key={`${t.time}-${t.symbol}`}>
                      {t.time.replace('T', ' ').slice(0, 16)} — {t.side} {t.symbol}
                      {t.pnl !== null ? ` (PnL ${t.pnl >= 0 ? '+' : ''}${t.pnl})` : ''}
                      {t.reason ? ` — ${t.reason}` : ''}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              JARVIS can explain this data in chat (ask about your trading bot). It can never
              place, modify, or cancel trades — no execution path exists.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
