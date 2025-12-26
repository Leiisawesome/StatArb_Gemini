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
        
        # Determine simulation window
        eval_cfg = self.config.get('evaluation', {})
        rolling_days = eval_cfg.get('rolling_days', 1)
        end_date_str = eval_cfg.get('end_date')
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now() - timedelta(days=1)
            while end_date.weekday() >= 5:
                end_date -= timedelta(days=1)

        dates = []
        curr = end_date
        while len(dates) < rolling_days:
            if curr.weekday() < 5:
                dates.append(curr)
            curr -= timedelta(days=1)
        dates.reverse() # Chronological order

        logger.info(f"Starting rolling evaluation for {len(dates)} days...")
        
        results = []
        all_symbols_picked = []
        
        for sim_date in dates:
            logger.info(f"--- Evaluating {sim_date.strftime('%Y-%m-%d')} ---")
            
            # 1. Run Symbol Picker for this date
            picker = SymbolPickerRunner("symbolpicker/config.yaml")
            try:
                artifact_path = await picker.run(sim_date)
            except Exception as e:
                logger.error(f"Picker failed for {sim_date}: {e}")
                continue

            if not artifact_path or not os.path.exists(artifact_path):
                logger.error(f"Artifact not found for {sim_date}")
                continue
                
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)
            
            symbols = list(artifact.get('symbols', {}).keys())
            trade_date_str = artifact.get('trade_date')
            all_symbols_picked.extend(symbols)
            
            if not symbols or not trade_date_str:
                logger.warning(f"No symbols or trade_date for {sim_date}")
                continue

            # 2. Run Papertest for the TRADE DATE
            trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d')
            
            # Update config for this day
            day_config = self.config.copy()
            if 'papertest' not in day_config: day_config['papertest'] = {}
            if 'polygon' not in day_config['papertest']: day_config['papertest']['polygon'] = {}
            
            day_config['papertest']['polygon']['symbols'] = symbols
            # Assuming papertest engine handles start/end dates
            day_config['papertest']['session'] = day_config['papertest'].get('session', {})
            day_config['papertest']['session']['start_date'] = trade_date_str
            day_config['papertest']['session']['end_date'] = trade_date_str
            
            from papertest.engine.papertest_engine import PapertestEngine
            engine = PapertestEngine(day_config)
            await engine.initialize()
            day_stats = await engine.run()
            results.append(day_stats)

        # 3. Aggregate Results
        total_pnl = sum(r.get('total_pnl', 0.0) for r in results) if results else 0.0
        success = len(results) == len(dates)
        
        return PapertestResult(
            experiment_name="Symbol Picker Rolling Test",
            experiment_type="rolling_integration",
            run_timestamp=start_time,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            success=success,
            total_pnl=total_pnl,
            custom_metrics={
                "days_evaluated": len(results),
                "total_symbols_picked": len(set(all_symbols_picked)),
                "avg_symbols_per_day": len(all_symbols_picked) / len(results) if results else 0
            }
        )

