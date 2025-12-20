"""
ExecutionQualityPapertest
-------------------------

Runs a papertest and reports best-effort execution statistics.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from papertest.engine.papertest_engine import PapertestEngine
from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class ExecutionQualityPapertest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Execution quality papertest: best-effort execution stats / TCA"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)
        try:
            engine = PapertestEngine(self.config)
            await engine.initialize()
            run_result = await engine.run()

            duration = time.perf_counter() - start

            # Best-effort extraction: rely on engine_stats keys we maintain
            stats = run_result.engine_stats or {}
            custom = {
                "bridge_stats": run_result.bridge_stats,
                "orders_submitted": stats.get("orders_submitted"),
                "fills_received": stats.get("fills_received"),
            }
            return PapertestResult(
                experiment_name="execution_quality",
                experiment_type="papertest_execution_quality",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=run_result.engine_stats,
                replay_stats=run_result.replay_stats,
                custom_metrics=custom,
                success=True,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="execution_quality",
                experiment_type="papertest_execution_quality",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )


