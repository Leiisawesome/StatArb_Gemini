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

from papertest.engine.papertest_engine import PapertestEngine
from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class SmokeTest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Smoke test: single symbol streaming replay + basic pipeline wiring"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)

        try:
            engine = PapertestEngine(self.config)
            await engine.initialize()
            result = await engine.run()

            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="smoke_test",
                experiment_type="papertest_smoke",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=result.engine_stats,
                replay_stats=result.replay_stats,
                custom_metrics={"bridge_stats": result.bridge_stats},
                success=True,
            )

        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="smoke_test",
                experiment_type="papertest_smoke",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )


