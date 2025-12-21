"""
RegimeTransitionPapertest
-------------------------

Runs a replay window intended to include regime transitions and ensures
the engine completes without errors (regime stats are best-effort).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class RegimeTransitionPapertest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Regime transition papertest: run and validate stable execution during regime changes"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)
        try:
            run_result = await self._run_engine()

            duration = time.perf_counter() - start
            stats = run_result.engine_stats or {}
            return PapertestResult(
                experiment_name="regime_transition",
                experiment_type="papertest_regime_transition",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=run_result.engine_stats,
                replay_stats=run_result.replay_stats,
                custom_metrics={
                    "bridge_stats": run_result.bridge_stats,
                    "bars_processed": stats.get("bars_processed"),
                    "signals_generated": stats.get("signals_generated"),
                },
                success=True,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="regime_transition",
                experiment_type="papertest_regime_transition",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )


