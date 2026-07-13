# Production Operator Guide

This runbook covers the supervised macOS workstation deployment. The production
runtime supports Massive L1 data, IBKR paper or explicitly acknowledged live
routing, and at most 25 US equity symbols.

## Safety model

`trading-daemon` and `ProductionRuntime` are the canonical operator-facing live
architecture. The lightweight `live-routed` command is limited to paper-account
qualification and embedded testing.

The daemon fails closed. It will not enable entries until promoted artifacts have
both a committed run manifest and a passing validation result, satisfy the configured
`model_quality` thresholds, and are loaded; IBKR is connected; persisted orders and
positions match the broker; every
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

Before creating market-data or broker clients, the daemon runs a read-only
preflight. It verifies required secrets by presence only, promoted artifact
approval and integrity, the database location, broker configuration source and
paper/live mode, and bounded retry policies. Diagnostics contain configuration
metadata but never secret values. Any failed check prevents runtime-thread
startup and broker connectivity.

Run the same gate without starting the daemon:

```bash
.venv/bin/trading-daemon --config config/production.json --preflight
```

This mode writes one redacted JSON report to standard output, returns exit code
`0` when every required check passes, and returns exit code `2` when configuration
loading or any preflight check fails. It does not construct market-data clients,
broker clients, the control API, `ProductionRuntime`, or background threads.

The terminal console can pause entries, resume after reconciliation, activate the
durable kill switch, and flatten strategy positions. Halt and flatten operations
require confirmation at the API boundary. Closing the console does not stop the
daemon.

The daemon writes its SQLite/WAL ledger under `var/` by default. Back up the
database only with a SQLite-aware backup process while the daemon is running.
Do not edit the ledger manually.

The authenticated localhost API separates liveness, trading readiness, and the
detailed operator snapshot. `/health` returns a typed liveness report and remains
HTTP `200` when the daemon can respond, using `degraded` to expose ledger or alert
subsystem failures. `/ready` returns HTTP `200` only when every required safety
check passes and HTTP `503` with stable check codes otherwise. A ready runtime may
report `degraded` when only advisory local-notification delivery has failed.
`/status` provides the detailed lifecycle, positions, orders, broker, and alert
view used by the terminal console. `/events` and `/alerts` expose bounded audit
history.

Readiness requires the running lifecycle, a clear kill switch, loaded promoted
models, complete per-symbol warmup, fresh per-symbol market data, broker
connectivity, and broker/ledger order and position reconciliation. Alert
persistence and notification delivery appear as explicit advisory checks.

Alerts use typed severity and category fields and cover broker disconnects,
reconciliation failures, order rejections, stale market data, strategy risk
halts, and runtime failures. Repeated alerts with the same category, code, and
symbol are suppressed within the deduplication window. Local notification
delivery is fail-safe: a notification error or timeout cannot interrupt runtime
control flow or remove the alert from bounded history. The `/health` response
reports the cumulative delivery-failure count and bounded recent diagnostics
under `alert_delivery`; delivery failures are recorded directly rather than
recursively generating more alerts. Accepted alerts and delivery failures are
also persisted in the SQLite audit ledger. On restart, the daemon restores its
bounded alert history, deduplication timestamps, and cumulative delivery
diagnostics without notifying historical alerts again. Alert-store failures are
non-recursive and appear under `alert_persistence` in `/status`.

For `launchd`, replace every `REPLACE_WITH_REPOSITORY_PATH` value in
`ops/macos/com.statarb-gemini.daemon.plist`, create `var/log`, and install the
plist under the operator's `~/Library/LaunchAgents` directory.

## Recovery

After a process, data-feed, or broker interruption, the daemon reconnects and
reconciles. It automatically resumes only when broker positions, open orders,
net liquidation, durable order records, and promoted models agree. Ambiguous
in-flight orders or position differences remain halted for operator review.

The `retry` configuration defines separate bounded policies for market-data
subscriptions, broker connections, and read-only broker queries. Authentication,
permission, configuration, and validation failures are not retried. Order
submission and cancellation are never automatically repeated; an ambiguous
mutation remains halted until broker and ledger state reconcile.

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

Run the offline safety-drill gate first:

```bash
.venv/bin/trading-qualify
```

It runs deterministic restart fail-closed, broker-disconnect, stale-feed,
order-rejection, and flatten-timeout scenarios through `ProductionRuntime` with
temporary SQLite ledgers and in-process source/router boundaries. The command
contacts no external infrastructure, writes one machine-readable JSON report,
and returns `0` only when every scenario passes (`2` otherwise). Use repeated
`--scenario NAME` options to run a selected subset. This gate complements rather
than replaces external Massive and IBKR smoke checks or regular-hours paper
qualification.

The daemon appends one session-start marker when a regular-hours attempt begins
and a session-close marker only after the flatten path reaches `stopped` with its
closing position and open-order snapshot. After every attempted paper session,
finalize that date:

```bash
.venv/bin/trading-paper-qualify \
  --database var/trading.sqlite3 \
  --finalize YYYY-MM-DD
```

The command appends an immutable evaluation to the same ledger and emits the
complete machine-readable gate report. Re-run it without `--finalize` to inspect
the accumulated result. It returns `0` only after ten trailing evaluations pass;
until then, or whenever the latest attempted session is missing or failed, it
returns `2`. Finalize every attempted date: an automatic start marker without a
recorded evaluation is synthesized as a failed session and breaks the streak.

Each session evaluation requires:

1. matching paper-mode start and regular close markers;
2. recorded framework activity;
3. unique client and external order ids;
4. no nonterminal or open orders at close;
5. every execution report reconciled to a durable order intent;
6. no nonzero strategy position at close;
7. every submitted decision either routed or durably blocked;
8. every route acknowledgement linked to a durable order intent; and
9. no runtime-halt incident during the session.

The ten-session gate complements the offline safety drills. Before live-capital
consideration, also retain successful external paper evidence for restart drills
during no-order, submitted, partial-fill, and disconnected states and verify the
stale-feed, broker-loss, daily-loss, and flatten-timeout controls. The offline
gate covers deterministic safety behavior; external evidence proves the actual
broker and workstation environment.

Live mode additionally requires `IBKR_PAPER_TRADING=false` and the exact JSON
value `"live_risk_acknowledgement": "I_ACCEPT_LIVE_CAPITAL_RISK"`. Begin with
one symbol and an account-level notional cap before expanding the universe.

External smoke tests can contact Massive and submit IBKR paper orders. They run
only when explicitly requested:

```bash
pytest --run-external -m external
```
