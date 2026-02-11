# Golden Trace Baselines

This directory contains "golden" baseline snapshots of pipeline trace summaries.
These baselines are used for regression detection: if a code change alters the
pipeline behavior (different checkpoint counts, PnL, fill counts), the
regression test will flag it.

## Files

- `smoke_test_mom_baseline.json` -- Baseline from BT MOM smoke test
  (TSLA, 2024-12-18 to 2024-12-20, momentum strategy)

## Updating Baselines

After intentional behavioral changes, regenerate baselines by running:

```bash
python -m pytest tests/trace/test_pipeline_plumbing.py -s --update-golden
```

Or manually run the smoke test with tracing and capture the funnel summary.
