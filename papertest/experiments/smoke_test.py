"""
SmokeTest (Papertest)
---------------------

Single-symbol, short replay window sanity check:
- replay->dispatcher wiring works
- warmup succeeds
- event loop runs
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class SmokeTest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Smoke test: single symbol streaming replay + basic pipeline wiring"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)

        try:
            result = await self._run_engine()

            duration = time.perf_counter() - start
            return PapertestResult(
                # Match backtest smoke_test output layout / naming
                experiment_name="Smoke_Test",
                experiment_type="smoke_test",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=result.engine_stats,
                replay_stats=result.replay_stats,
                execution_stats={
                    "execution_history": result.execution_history,
                    "account_info": result.account_info,
                },
                custom_metrics={"bridge_stats": result.bridge_stats},
                success=True,
            )

        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="Smoke_Test",
                experiment_type="smoke_test",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )

    def print_summary(self, result: PapertestResult) -> None:
        # Render the same console layout as backtest smoke_test
        return super().print_summary_backtest_style(result)


