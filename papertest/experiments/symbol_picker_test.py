"""
End-to-end test for Symbol Picker -> Papertest flow.
"""
from __future__ import annotations
import logging
import asyncio
from datetime import datetime
import json
import os
from typing import Any, Dict, Optional

from papertest.experiments.base_experiment import BasePapertestExperiment, PapertestResult
from symbolpicker.runner import SymbolPickerRunner

logger = logging.getLogger(__name__)

class SymbolPickerTestExperiment(BasePapertestExperiment):
    def get_description(self) -> str:
        return "Runs Symbol Picker offline, then executes a papertest sim on the picked universe."

    async def run(self) -> PapertestResult:
        start_time = datetime.now()
        
        # 1. Run Symbol Picker
        logger.info("Step 1: Running Symbol Picker...")
        # Use default config path
        picker = SymbolPickerRunner("symbolpicker/config.yaml")
        
        try:
            # Run picker to generate artifact
            artifact_path = await picker.run()
        except Exception as e:
            logger.error(f"Symbol Picker execution failed: {e}", exc_info=True)
            return PapertestResult(
                experiment_name="Symbol Picker Test",
                experiment_type="integration",
                run_timestamp=start_time,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error_message=f"Symbol Picker execution failed: {str(e)}"
            )
        
        if not artifact_path or not os.path.exists(artifact_path):
            return PapertestResult(
                experiment_name="Symbol Picker Test",
                experiment_type="integration",
                run_timestamp=start_time,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error_message="Symbol Picker failed to generate artifact"
            )
            
        logger.info(f"Step 2: Loaded Universe from {artifact_path}")
        
        # 2. Configure Papertest with Picked Symbols
        try:
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)
                
            symbols = list(artifact.get('symbols', {}).keys())
            logger.info(f"Picked {len(symbols)} symbols: {symbols}")
            
            if not symbols:
                 return PapertestResult(
                    experiment_name="Symbol Picker Test",
                    experiment_type="integration",
                    run_timestamp=start_time,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    success=False,
                    error_message="Symbol Picker generated empty universe"
                )

            # Inject symbols into config
            # Handle config structure (nested vs flat)
            if 'papertest' in self.config:
                if 'polygon' in self.config['papertest']:
                    self.config['papertest']['polygon']['symbols'] = symbols
                else:
                    logger.warning("Config 'papertest' missing 'polygon' section, trying to inject anyway")
                    self.config['papertest']['polygon'] = {'symbols': symbols}
            elif 'polygon' in self.config:
                 self.config['polygon']['symbols'] = symbols
            else:
                 logger.warning("Config structure unknown (no 'papertest' or 'polygon' keys), assuming flat structure")
                 self.config['polygon'] = {'symbols': symbols}
                 
        except Exception as e:
            return PapertestResult(
                experiment_name="Symbol Picker Test",
                experiment_type="integration",
                run_timestamp=start_time,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error_message=f"Failed to configure from artifact: {str(e)}"
            )

        # 3. Run Engine
        logger.info("Step 3: Running Papertest Engine...")
        try:
            stats = await self._run_engine()
            success = True
            err = None
        except Exception as e:
            logger.error(f"Engine failed: {e}", exc_info=True)
            success = False
            err = str(e)
            stats = {}

        return PapertestResult(
            experiment_name="Symbol Picker Test",
            experiment_type="integration",
            run_timestamp=start_time,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            engine_stats=stats,
            success=success,
            error_message=err,
            custom_metrics={
                "universe_count": len(symbols),
                "regime_label": artifact.get('regime', {}).get('label', 'N/A')
            }
        )

