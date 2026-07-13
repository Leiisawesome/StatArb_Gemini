# Paper-Trading Qualification Runbook

This runbook is the next phase after the automated release-candidate tests. Its
purpose is to collect operational evidence from the real Massive, IBKR paper,
network, workstation, and market-hours environment. It does not authorize live
capital.

## Exit criteria

The campaign is complete only when all of the following are true:

1. the clean-install test suite, daemon preflight, and `trading-qualify` pass;
2. ten trailing regular-hours paper sessions pass `trading-paper-qualify`;
3. the same Git commit, production configuration, symbol universe, and promoted
   model remain fixed for all ten counted sessions;
4. external recovery drills have evidence from the IBKR paper environment; and
5. no ledger, artifact, or report has been manually edited.

A failed, missing, prematurely stopped, or unfinalized session resets the
trailing streak. Do not force trades merely to produce activity: a no-order day
may pass if framework activity and every other safety check are complete.

## Campaign separation

Use two configurations and two SQLite databases:

- `config/production.json` and `var/trading.sqlite3` for the ten counted sessions;
- `config/production.drill.json` and `var/paper-drills.sqlite3` for disruptive
  restart, disconnect, stale-feed, and flatten drills.

Never run a deliberate failure drill against `var/trading.sqlite3`. A runtime
halt is correctly treated as a failed counted session.

## One-time setup

The examples below use PowerShell from the repository root.

1. Install exactly the locked environment and verify the code:

   ```powershell
   $env:UV_LINK_MODE = "copy" # Recommended when the repository is under OneDrive
   uv sync --locked --extra dev
   uv run pytest -q
   uv run trading-qualify
   ```

   Stop if any command fails. `trading-qualify` must report all five scenarios
   as `passed` and return exit code `0`.

2. Store the Massive and console secrets through the supplied secret command:

   ```powershell
   uv run trading-secret MASSIVE_API_KEY
   uv run trading-secret TRADING_CONSOLE_TOKEN
   ```

3. Copy `config/production.example.json` to the ignored
   `config/production.json`. For the first campaign, use one symbol, normally
   `AAPL`, and one validation-approved run id:

   ```powershell
   Copy-Item config\production.example.json config\production.json
   uv run l1-microstructure list-runs `
     --artifact-root var/artifacts `
     --symbol AAPL `
     --passing-only
   ```

4. In `config/production.json`, verify:

   - `mode` is exactly `paper`;
   - `symbols` contains only the intended first symbol;
   - `promoted_run_ids` pins the chosen passing run;
   - `database_path` is `var/trading.sqlite3`;
   - `api_host` remains localhost;
   - shorting and leverage remain disabled;
   - session times remain 09:30, 15:50, 15:58, and 16:00 New York time; and
   - risk fractions are deliberately conservative for the paper account.

5. Verify the broker configuration selects IBKR paper mode:

   ```text
   ACTIVE_BROKER=interactive_brokers
   IBKR_HOST=127.0.0.1
   IBKR_PORT=4002
   IBKR_CLIENT_ID=<dedicated client id>
   IBKR_ACCOUNT_ID=<paper account id>
   IBKR_PAPER_TRADING=true
   IBKR_OUTSIDE_RTH=false
   ```

   Confirm the port against the running TWS or Gateway configuration. Do not
   proceed if the account or application identifies itself as live.

6. Start TWS or IBKR Gateway in paper mode and run the real preflight:

   ```powershell
   uv run trading-daemon --config config/production.json --preflight
   if ($LASTEXITCODE -ne 0) { throw "Paper preflight failed" }
   ```

   Every check must be `passed`, including the promoted artifact, broker mode,
   secrets, database location, and retry policies.

7. Before the counted campaign, run external smokes deliberately against the
   paper account. These tests contact Massive and the IBKR routed smoke may
   submit and cancel an order:

   ```powershell
   uv run pytest --run-external -m external `
     tests/integration/l1_state_machine -q
   ```

   Confirm the IBKR account is paper immediately before running this command.

## Choose counted sessions

Use full regular US market days only. Do not count weekends, exchange holidays,
or scheduled early-close days because the configured close is 16:00 ET. The
qualification date is always the New York market date, not the workstation's
local date.

With the default 30-minute warmup, start the daemon by 09:00 ET. In Shanghai,
this is normally 21:00 during US daylight-saving time or 22:00 during US
standard time; confirm the conversion on each session date.

Record the following before session 1 and keep it unchanged:

```powershell
git rev-parse HEAD
(Get-FileHash config\production.json -Algorithm SHA256).Hash
```

```text
Git commit:
Production-config SHA-256:
Symbol:
Promoted run id:
IBKR paper account:
IBKR client id:
Massive subscription/account:
Qualification database:
Campaign start date:
```

If code, configuration, risk limits, symbol universe, broker account, or promoted
model changes, start a new ten-session campaign with a new database.

## Daily counted-session procedure

### 1. Pre-open

At least 35 minutes before the open:

1. verify the workstation clock, network, power, and disk space;
2. start TWS or Gateway and confirm the paper account banner;
3. confirm there are no unexpected broker positions or open orders;
4. run preflight and save its JSON output; and
5. start the daemon, then the console.

```powershell
$sessionDate = "YYYY-MM-DD" # New York market date
New-Item -ItemType Directory -Force var\evidence | Out-Null

uv run trading-daemon --config config/production.json --preflight |
  Tee-Object -FilePath "var\evidence\$sessionDate-preflight.json"
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not count this session" }

uv run trading-daemon --config config/production.json
```

Open a second PowerShell terminal:

```powershell
uv run trading-console
```

Do not start a second daemon against the same database or broker client id.

### 2. Warmup and open

Before treating the session as operational, confirm in the console:

- mode is `PAPER`;
- broker is connected;
- kill switch is clear;
- lifecycle progresses from `WARMING` to `RUNNING`;
- every configured symbol completes warmup;
- market data remains fresh; and
- there are no unexplained positions, open orders, or alerts.

If readiness does not become healthy after the configured warmup, stop the
campaign for that day. Do not clear a kill switch or resume after a reconciliation
failure merely to preserve the streak.

### 3. During the session

Keep the daemon and console supervised. Record the time and response for every
warning, disconnect, pause, halt, manual flatten, or workstation interruption.

Immediately treat the session as failed if any of these occurs:

- the daemon enters `HALTED` or `ERROR`;
- broker and ledger positions or orders disagree;
- the feed becomes stale or disconnect retries exhaust;
- an order remains ambiguous or cannot be reconciled;
- the workstation or daemon restarts unexpectedly; or
- an operator must bypass the normal close sequence.

Safety takes priority over the streak. Use `HALT` or `FLATTEN` when required and
retain the resulting failed evidence.

### 4. Normal close

With the default policy, entries stop at 15:50 ET and flattening begins at
15:58 ET. Keep the daemon running until all of the following are visible:

- lifecycle is `STOPPED`;
- strategy positions are empty;
- open orders are empty; and
- no flatten-timeout or runtime-halt alert occurred.

Do not terminate the daemon before this sequence completes. An early manual
flatten is an emergency action and may not produce the regular-close marker
needed for a passing session.

After `STOPPED` is confirmed, close the console and stop the daemon with
`Ctrl+C`.

### 5. Finalize the New York session date

Run exactly one normal finalization after the daemon has stopped:

```powershell
$json = uv run trading-paper-qualify `
  --database var/trading.sqlite3 `
  --finalize $sessionDate
$qualificationExit = $LASTEXITCODE
$json | Set-Content -Encoding utf8 "var\evidence\$sessionDate-qualification.json"
$report = $json | ConvertFrom-Json
$session = $report.sessions |
  Where-Object session_date -eq $sessionDate |
  Select-Object -Last 1

$session | ConvertTo-Json -Depth 8
"trailing=$($report.trailing_passing_sessions) qualified=$($report.qualified) exit=$qualificationExit"
```

For sessions 1 through 9, global exit code `2` is expected even when the day's
session status is `passed`; the campaign is not qualified yet. The daily result
is acceptable only when `$session.status` is `passed` and every individual check
has `passed: true`.

After session 10, require all three:

```text
qualified = true
trailing_passing_sessions >= 10
process exit code = 0
```

Run the read-only report at any time without `--finalize`:

```powershell
uv run trading-paper-qualify --database var/trading.sqlite3
```

Do not repeatedly finalize a failed day hoping to change the result. Diagnose
the failed check, preserve the ledger and report, correct the cause, and begin a
new trailing streak on the next eligible session.

### 6. Preserve evidence

After finalization and after all processes using the database have exited, copy
the ledger and the daily reports to a protected backup location. Retain:

- the SQLite ledger;
- preflight and qualification JSON;
- daemon and TWS/Gateway logs;
- the frozen production configuration and its SHA-256;
- the Git commit and promoted run id;
- broker executions, orders, and end-of-day positions; and
- an operator note for every alert or intervention.

Do not edit the SQLite database. If evidence is wrong, retain it as a failed
attempt.

## External paper recovery drills

Run these with `config/production.drill.json` and `var/paper-drills.sqlite3`, not
the counted-session ledger. Use one symbol, minimal paper exposure, and a second
IBKR client id. For every drill, record the expected lifecycle, alert code,
broker state, ledger state, restart result, and proof that no duplicate order was
submitted.

| Drill | Action in the paper environment | Required result |
| --- | --- | --- |
| Restart with no order | Restart after reconciliation with no positions or orders | Reconciliation succeeds; no order is submitted |
| Restart with submitted order | Restart while a known paper order is open | Order is rehydrated once; no duplicate mutation occurs |
| Restart after partial fill | Restart with a partially filled paper order if IBKR paper simulation produces one | Filled quantity and remaining order reconcile without replaying the fill |
| Broker disconnected | Stop TWS/Gateway or disconnect the broker session | Runtime halts, records the incident, and does not route |
| Stale feed | Interrupt the Massive feed in a controlled drill | Runtime halts with stale-data evidence and does not route |
| Flatten timeout | Make the paper router unavailable during a controlled flatten | Runtime halts and preserves unresolved position/order evidence |

Do not manufacture a partial fill or daily account loss in a live account. If the
IBKR paper simulator cannot produce a partial fill deterministically, record that
limitation and keep the deterministic offline drill as the automated evidence.
After each disruptive drill, reconcile the broker manually before the next one.

## Final review

Before declaring the paper phase complete, have a second reviewer verify:

1. ten trailing sessions are present and all checks pass;
2. every session used the frozen commit, configuration, model, symbol, and paper
   account;
3. broker end-of-day records agree with the ledger;
4. external drill evidence contains no duplicate or ambiguous mutation;
5. all sessions closed flat with no open order; and
6. no live-capital acknowledgement or live broker mode was enabled.

Passing this runbook means the system may be considered for a separate
live-capital readiness review. It does not itself approve live trading.
