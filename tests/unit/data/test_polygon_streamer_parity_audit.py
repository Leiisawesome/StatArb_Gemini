"""Tests for Polygon streamer parity audit utility."""

from core_engine.data.replay.parity_audit import run_parity_audit


def test_parity_audit_strict_mode_has_no_diffs():
    diffs = run_parity_audit(strict_live_parity=True)
    assert all(diff.passed for diff in diffs.values())
    assert all(not diff.type_mismatches for diff in diffs.values())


def test_parity_audit_enriched_mode_reports_expected_extras():
    diffs = run_parity_audit(strict_live_parity=False)

    assert all(not diff.type_mismatches for diff in diffs.values())
    assert "trade_count" in diffs["trade"].extra_keys
    assert "spread" in diffs["quote"].extra_keys
    assert "quote_count" in diffs["quote"].extra_keys
    assert "is_stale" in diffs["quote"].extra_keys
    assert "quote_age_ms" in diffs["quote"].extra_keys
