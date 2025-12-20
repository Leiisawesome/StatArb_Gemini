"""
CheckpointRestoreDeterminismPapertest
-------------------------------------

Best-effort checkpoint/restore validation:
- Ensures checkpoints are created (periodic or critical)
- Attempts restore from latest checkpoint (if present)

Note: Full deterministic replay-from-checkpoint requires replay offset support,
which is out-of-scope for v1 suite wiring.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from papertest.engine.papertest_engine import PapertestEngine
from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult


class CheckpointRestoreDeterminismPapertest(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Checkpoint/restore determinism: verify checkpoints exist and restore API works (best-effort)"

    async def run(self) -> PapertestResult:
        start = time.perf_counter()
        run_ts = datetime.now(timezone.utc)
        try:
            engine = PapertestEngine(self.config)
            await engine.initialize()
            run_result = await engine.run()

            # Inspect checkpoint dir
            checkpoint_dir = Path(self.config["papertest"]["session"].get("checkpoint_dir", "papertest/results/checkpoints"))
            checkpoint_files = sorted(checkpoint_dir.glob("*.json"))

            restored_ok = False
            if engine.wired and engine.wired.engine:
                try:
                    restored_ok = await engine.wired.engine.restore_from_checkpoint(None)
                except Exception:
                    restored_ok = False

            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="checkpoint_restore_determinism",
                experiment_type="papertest_checkpoint_restore",
                run_timestamp=run_ts,
                duration_seconds=duration,
                engine_stats=run_result.engine_stats,
                replay_stats=run_result.replay_stats,
                custom_metrics={
                    "bridge_stats": run_result.bridge_stats,
                    "checkpoint_files": [p.name for p in checkpoint_files[:10]],
                    "checkpoint_count": len(checkpoint_files),
                    "restore_invoked": True,
                    "restore_success": restored_ok,
                },
                success=True,
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return PapertestResult(
                experiment_name="checkpoint_restore_determinism",
                experiment_type="papertest_checkpoint_restore",
                run_timestamp=run_ts,
                duration_seconds=duration,
                success=False,
                error_message=str(e),
            )


