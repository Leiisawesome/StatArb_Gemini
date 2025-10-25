"""
Phase 4 Strategy Refactoring Tests

This directory contains tests for the Phase 4 pipeline refactoring initiative,
which ensures all strategies consume enriched data from ProcessingPipelineOrchestrator
instead of calculating their own indicators.

Test Files:
- test_momentum_refactoring.py: Momentum strategy refactoring tests (15 tests)
- test_mean_reversion_refactoring.py: Mean Reversion strategy tests (17 tests)
- test_statistical_arbitrage_refactoring.py: Statistical Arbitrage tests (15 tests)
- test_remaining_strategies.py: Tests for remaining 7 strategies (15 tests)

Total: 62 tests validating Rule 3 compliance

See: docs/03_compliance_audits/PHASE4.*.md for detailed documentation
"""

