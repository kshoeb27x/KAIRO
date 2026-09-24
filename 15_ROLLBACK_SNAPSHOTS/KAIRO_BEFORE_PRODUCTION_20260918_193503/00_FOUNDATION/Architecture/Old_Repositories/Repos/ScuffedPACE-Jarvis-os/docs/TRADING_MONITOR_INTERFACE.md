# Trading Monitor Interface

JARVIS can **read and explain** a trading bot's state. It can **never trade**:
the `trade_execute` action type is reserved with no registered executor, so
even an explicitly approved trade request fails honestly. A future execution
integration would have to be built deliberately and would sit behind the same
single-use approval system as everything else.

## How a bot connects

Write a JSON status report to a file on this machine, atomically (write to a
temp file, then rename), as often as you like. Then set in `.env`:

```
TRADING_REPORT_PATH=C:\path\to\your\bot\status.json
```

Restart JARVIS (`npm run jarvis`). The report is read-only, capped at 1 MB,
validated against the schema below, and considered **stale after 15 minutes**
(JARVIS says so rather than presenting old numbers as current).

A working example lives at [`data/trading-sample.json`](../data/trading-sample.json).

## Report schema (version 1)

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-07-14T12:00:00Z",     // ISO timestamp of this report
  "bot": { "name": "MyBot", "strategyVersion": "v1.3" },
  "mode": "simulated" | "paper" | "live",     // never blurred in the UI
  "running": true,
  "account": {                                 // or null
    "equity": 10000,
    "currency": "USD",
    "riskExposurePct": 8.5                     // open exposure as % of equity
  },
  "performance": {                             // or null
    "pnlTotal": 142.5,
    "pnlPeriod": 12.25,
    "maxDrawdownPct": 4.2,
    "winRatePct": 54,
    "sampleTrades": 13                         // closed trades behind the stats
  },
  "recentTrades": [
    { "time": "...", "symbol": "BTC-USD", "side": "long", "quantity": 0.01,
      "entry": 64200.5, "exit": 64510.0, "pnl": 3.1, "reason": "signal name" }
  ],
  "recentDecisions": [ { "time": "...", "summary": "why the bot did/skipped something" } ],
  "errors":   [ "strings" ],
  "warnings": [ "strings" ],
  "strategyChanges": [ { "time": "...", "summary": "what changed in the strategy" } ]
}
```

## Honesty rules JARVIS applies

- **Modes are never blurred**: simulated, paper, and live are labeled
  distinctly, and live mode is always flagged for attention.
- **No profitability claims from thin data**: below 20 closed trades JARVIS
  refuses to state a win rate or call the bot profitable.
- **Stale, missing, or malformed reports** produce a clear message — never
  invented numbers.
- Errors, warnings, a stopped bot, risk exposure above 25% of equity, and
  recent strategy changes are surfaced as attention items.

## Other transports

The `TradingMonitorAdapter` interface (`src/server/trading/types.ts`) is the
boundary: a future adapter can read SQLite, a local HTTP API, or WebSocket
events without changing JARVIS core — it just has to return the same
`TradingStatus` shape.
