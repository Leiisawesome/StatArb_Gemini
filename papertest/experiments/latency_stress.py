"""
LatencyStressPapertest
----------------------

Runs papertest under higher simulated paper broker latency.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from papertest.engine.papertest_engine import PapertestEngine
from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class LatencyStressPapertest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Latency stress papertest: elevated simulated broker latency"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)
        try:
            engine = PapertestEngine(self.config)
            await engine.initialize()
            run_result = await engine.run()

            duration = time.perf_counter() - start
            stats = run_result.engine_stats or {}
            return PapertestResult(
                experiment_name="latency_stress",
                experiment_type="papertest_latency_stress",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=run_result.engine_stats,
                replay_stats=run_result.replay_stats,
                custom_metrics={
                    "bridge_stats": run_result.bridge_stats,
                    "bars_processed": stats.get("bars_processed"),
                    "orders_submitted": stats.get("orders_submitted"),
                    "fills_received": stats.get("fills_received"),
                },
                success=True,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="latency_stress",
                experiment_type="papertest_latency_stress",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )


