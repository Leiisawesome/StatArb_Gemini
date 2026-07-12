# Production Operator Guide

This runbook covers the supervised macOS workstation deployment. The production
runtime supports Massive L1 data, IBKR paper or explicitly acknowledged live
routing, and at most 25 US equity symbols.

## Safety model

The daemon fails closed. It will not enable entries until promoted artifacts are
loaded, IBKR is connected, persisted orders and positions match the broker, every
symbol has rebuilt its configured market context, and the persistent kill switch
is clear.

Default controls are:

1. 1% daily net-liquidation loss halt.
2. 25% maximum gross exposure.
3. 3% maximum exposure per symbol.
4. No leverage or new short positions.
5. New entries stop at 15:50 ET.
6. Open orders are cancelled and positions are flattened from 15:58 ET.
7. Unresolved positions or orders halt the runtime.

## Installation

Use Python 3.12 or 3.13 and the committed lockfile:

```bash
uv sync --locked --extra dev
```

Store secrets interactively in macOS Keychain:

```bash
.venv/bin/trading-secret MASSIVE_API_KEY
.venv/bin/trading-secret TRADING_CONSOLE_TOKEN
```

Copy `config/production.example.json` to the ignored
`config/production.json`, set the symbol universe, and pin one validated run id
for every symbol. Model changes are only accepted while stopped or halted.

## Operation

Start IBKR Gateway or TWS in paper mode, then run:

```bash
.venv/bin/trading-daemon --config config/production.json
.venv/bin/trading-console
```

The terminal console can pause entries, resume after reconciliation, activate the
durable kill switch, and flatten strategy positions. Halt and flatten operations
require confirmation at the API boundary. Closing the console does not stop the
daemon.

The daemon writes its SQLite/WAL ledger under `var/` by default. Back up the
database only with a SQLite-aware backup process while the daemon is running.
Do not edit the ledger manually.

For `launchd`, replace every `REPLACE_WITH_REPOSITORY_PATH` value in
`ops/macos/com.statarb-gemini.daemon.plist`, create `var/log`, and install the
plist under the operator's `~/Library/LaunchAgents` directory.

## Recovery

After a process, data-feed, or broker interruption, the daemon reconnects and
reconciles. It automatically resumes only when broker positions, open orders,
net liquidation, durable order records, and promoted models agree. Ambiguous
in-flight orders or position differences remain halted for operator review.

The kill switch survives process and workstation restarts. Clearing it does not
bypass reconciliation.

## Artifact migration

New artifacts are canonical JSON with SHA-256 corruption detection. Legacy
pickle artifacts are rejected during normal loading. Migrate only artifacts
created by a trusted local workflow:

```bash
.venv/bin/artifact-migrate \
  --artifact-root var/artifacts \
  --trusted-local-artifacts \
  <artifact-id> [<artifact-id> ...]
```

## Qualification

Before live routing, complete at least ten consecutive regular-hours paper
sessions with:

1. no duplicate submissions or unreconciled fills;
2. no unresolved position at 16:00 ET;
3. successful restart drills during no-order, submitted, partial-fill, and
   disconnected states;
4. verified stale-feed, broker-loss, daily-loss, and flatten-timeout halts; and
5. an immutable audit record for every decision, order, fill, control, incident,
   and model promotion.

Live mode additionally requires `IBKR_PAPER_TRADING=false` and the exact JSON
value `"live_risk_acknowledgement": "I_ACCEPT_LIVE_CAPITAL_RISK"`. Begin with
one symbol and an account-level notional cap before expanding the universe.

External smoke tests can contact Massive and submit IBKR paper orders. They run
only when explicitly requested:

```bash
pytest --run-external -m external
```
