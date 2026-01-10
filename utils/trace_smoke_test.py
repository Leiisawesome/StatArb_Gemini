#!/usr/bin/env python3
"""
Trace Smoke Test Utility
========================

Chronological trace of all signals (generated, rejected, and approved)
across strategy logic, ADS queue, and central risk management.

Usage:
    python utils/trace_smoke_test.py
"""

import sys
import os
import asyncio
import pandas as pd
import logging
import re
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import unittest.mock

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from backtest.utils.config_loader import load_config
from backtest.experiments.smoke_test import SmokeTest
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import EnhancedMeanReversionStrategy
from core_engine.system.central_risk_manager import CentralRiskManager, TradingDecisionRequest, AuthorizationLevel
from core_engine.alpha.ads_components import PendingSignalQueue, PendingSignalContext
from core_engine.type_definitions.strategy import SignalType
from core_engine.trading.strategies.manager import StrategyManager

# --- TRACE COLLECTION ENGINE ---

class SignalTrace:
    def __init__(self, timestamp, bar_index, category, symbol, price, action, outcome, reason, details=None):
        self.timestamp = timestamp
        self.bar_index = bar_index
        self.category = category
        self.symbol = symbol
        self.price = price
        self.action = action
        self.outcome = outcome
        self.reason = reason
        self.details = details or {}

class TraceCollector:
    def __init__(self):
        self.traces: List[SignalTrace] = []
        self.current_bar_time = None
        self.current_bar_index = 0

    def add(self, category, symbol, action, outcome, reason, price=None, details=None):
        # Prevent duplicate identical traces in same bar
        for t in self.traces:
            if (t.timestamp == self.current_bar_time and 
                t.category == category and 
                t.symbol == symbol and 
                t.action == action and 
                t.outcome == outcome and 
                t.reason == reason):
                return
                
        trace = SignalTrace(
            self.current_bar_time, 
            self.current_bar_index, 
            category, 
            symbol, 
            price,
            action, 
            outcome, 
            reason, 
            details
        )
        self.traces.append(trace)

collector = TraceCollector()

# --- LOG INTERCEPTOR ---

class TraceLogHandler(logging.Handler):
    """Intercepts logs from strategy, manager and risk manager to extract details."""
    def emit(self, record):
        msg = record.getMessage()
        
        # Strategy Manager filtering
        if "StrategyManager" in record.name:
            if "❌ Filtered" in msg:
                # ❌ Filtered MR_Simple TSLA SignalType.BUY: already long position
                match = re.search(r'Filtered \w+ (\w+) (\w+\.\w+): (.+)', msg)
                if match:
                    sym, sig_type, reason = match.groups()
                    collector.add('STRATEGY_MGR', sym, sig_type, 'FILTERED', reason, details={'log': msg})
            elif "✅ Passed filter" in msg:
                # ✅ Passed filter: MR_Simple TSLA SignalType.BUY (confidence: 0.8553)
                match = re.search(r'Passed filter: \w+ (\w+) (\w+\.\w+) \(confidence: ([\d.]+)\)', msg)
                if match:
                    sym, sig_type, conf = match.groups()
                    collector.add('STRATEGY_MGR', sym, sig_type, 'PASSED', 'Filter criteria met', details={'confidence': conf, 'log': msg})

        # Strategy logic rejections/stops
        if "EnhancedMeanReversion" in record.name:
            if "REJECTED" in msg:
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                reason = msg.split('REJECTED: ')[1] if 'REJECTED: ' in msg else msg
                collector.add('STRATEGY', sym, 'SIGNAL', 'REJECTED', reason, details={'log': msg})
            elif "PROACTIVE STOP-LOSS" in msg:
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                collector.add('STRATEGY', sym, 'EXIT', 'PROACTIVE', 'Stop Loss Triggered', details={'log': msg})
            elif "Signal matured" in msg:
                # ✅ Signal matured: TSLA_BUY SMS=0.745
                match = re.search(r'Signal matured: (\w+)_(\w+) SMS=([\d.]+)', msg)
                if match:
                    sym, side, sms = match.groups()
                    collector.add('ADS_QUEUE', sym, side, 'MATURED', f'Reached threshold (SMS={sms})', details={'sms': sms, 'log': msg})

        # Risk Manager rejections
        if "CentralRiskManager" in record.name:
            if "FAILED" in msg:
                sym_match = re.search(r'FAILED: (\w+)', msg)
                pct_match = re.search(r'Position %: ([\d.]+)%', msg)
                limit_match = re.search(r'Limit: ([\d.]+)%', msg)
                sym = sym_match.group(1) if sym_match else '?'
                reason = f"Position Limit ({pct_match.group(1)}% > {limit_match.group(1)}%)" if pct_match and limit_match else "Risk Limit FAILED"
                collector.add('RISK', sym, '?', 'REJECTED', reason, details={'log': msg})
            elif "below minimum" in msg:
                match = re.search(r'confidence ([\d.]+) below minimum ([\d.]+)', msg)
                reason = f"Confidence {match.group(1)} < {match.group(2)}" if match else "Low Confidence"
                collector.add('RISK', '?', '?', 'REJECTED', reason, details={'log': msg})

# --- METHOD HOOKS ---

# Hook into Strategy generate_signals (ASYNC)
original_generate_signals = EnhancedMeanReversionStrategy.generate_signals
async def traced_generate_signals(self, enriched_data, position_details=None):
    result = await original_generate_signals(self, enriched_data, position_details)
    if result:
        for signal in result:
            price = getattr(signal, 'signal_price', None) or getattr(signal, 'entry_price', None)
            if price is None and hasattr(signal, 'additional_data'):
                price = signal.additional_data.get('entry_price')
            
            collector.add(
                'STRATEGY', 
                signal.symbol, 
                str(signal.signal_type), 
                'EMITTED', 
                'Strategy filters passed',
                price=price,
                details={'confidence': f"{signal.confidence:.2%}", 'strength': f"{getattr(signal, 'strength', 0.5):.2f}"}
            )
    return result

# Hook into PendingSignalQueue.add
original_queue_add = PendingSignalQueue.add
def traced_queue_add(self, ctx: PendingSignalContext):
    collector.add(
        'ADS_QUEUE',
        ctx.symbol,
        ctx.side,
        'QUEUED',
        'Initial conditions met, awaiting maturation',
        price=ctx.entry_price,
        details={'initial_sms': f"{ctx.sms.compute('normal'):.3f}"}
    )
    return original_queue_add(self, ctx)

# Hook into PendingSignalQueue.tick_all to show baking process
original_queue_tick_all = PendingSignalQueue.tick_all
def traced_queue_tick_all(self):
    removed_keys = original_queue_tick_all(self)
    for key, ctx in self.pending.items():
        sms_val = ctx.sms.compute('normal')
        collector.add(
            'ADS_QUEUE',
            ctx.symbol,
            ctx.side,
            'BAKING',
            f'Maturing in queue (SMS={sms_val:.3f})',
            price=ctx.entry_price,
            details={
                'exhaustion': f"{ctx.sms.exhaustion:.3f}",
                'p_rev': f"{ctx.sms.reversal_prob:.3f}",
                'vc': f"{ctx.sms.vol_compression:.3f}",
                'bars': ctx.sms.pending_bars
            }
        )
    for key in removed_keys:
        sym, side = key.split('_')
        collector.add('ADS_QUEUE', sym, side, 'REMOVED', 'Signal discarded (stale)')
    return removed_keys

# Hook into Risk Manager (ASYNC)
original_authorize = CentralRiskManager.authorize_trading_decision
async def traced_authorize(self, request: TradingDecisionRequest):
    result = await original_authorize(self, request)
    outcome = 'AUTHORIZED' if result.authorization_level != AuthorizationLevel.REJECTED else 'REJECTED'
    reason = result.rejection_reason or ('Risk limits passed' if outcome == 'AUTHORIZED' else 'Rejected by Risk Manager')
    
    collector.add(
        'RISK',
        request.symbol,
        f"{request.side} ({request.decision_type.name})",
        outcome,
        reason,
        price=request.current_price,
        details={
            'requested_qty': f"{request.quantity:.2f}",
            'authorized_qty': f"{result.authorized_quantity:.2f}",
            'confidence': f"{request.confidence:.2%}"
        }
    )
    return result

# --- RUNNER ---

async def run_trace():
    config_path = 'core_engine/config/catalog/suites/smoke_test_mr.yaml'
    base_config_path = 'backtest/configs/base_config.yaml'
    
    print(f"\033[1m🚀 Initializing Smoke Test Trace...\033[0m")
    
    config_dict = load_config(config_path, base_config_path)
    # FORCE Higher maturity threshold to show baking if possible
    for strat in config_dict.get('papertest', {}).get('strategies', []):
        if strat.get('name') == 'MR_Simple':
            # This won't work easily since it's hardcoded in some places, 
            # but we'll try to intercept it in the hooks if needed.
            pass

    smoke_test_exp = SmokeTest(config_dict)
    backtest_config = smoke_test_exp._create_backtest_config()
    engine = InstitutionalBacktestEngine(backtest_config)
    
    # Setup log interception
    trace_handler = TraceLogHandler()
    trace_handler.setLevel(logging.DEBUG)
    for name in ["core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion", 
                 "core_engine.system.central_risk_manager",
                 "core_engine.trading.strategies.manager",
                 "core_engine.alpha.ads_components"]:
        l = logging.getLogger(name)
        l.addHandler(trace_handler)
        l.setLevel(logging.DEBUG)

    # Apply monkey patches
    patches = [
        unittest.mock.patch.object(EnhancedMeanReversionStrategy, 'generate_signals', traced_generate_signals),
        unittest.mock.patch.object(CentralRiskManager, 'authorize_trading_decision', traced_authorize),
        unittest.mock.patch.object(PendingSignalQueue, 'add', traced_queue_add),
        unittest.mock.patch.object(PendingSignalQueue, 'tick_all', traced_queue_tick_all)
    ]
    
    for p in patches: p.start()
        
    original_process_single_bar = engine._process_single_bar
    async def traced_process_single_bar(self, bar, timestamp, bar_index, pre_calc_index=0):
        collector.current_bar_time = timestamp
        collector.current_bar_index = bar_index
        return await original_process_single_bar(bar, timestamp, bar_index, pre_calc_index)
    
    try:
        await engine.initialize()
        with unittest.mock.patch.object(InstitutionalBacktestEngine, '_process_single_bar', traced_process_single_bar):
            print(f"📈 Running Backtest Engine (2024-12-20)...")
            logging.getLogger('backtest.engine').setLevel(logging.ERROR)
            await engine.run_backtest()
    finally:
        try: await engine.shutdown()
        except: pass
        for p in patches: p.stop()

    # --- REPORTING ---
    
    print("\n" + "═"*160)
    print(f"\033[1m📊 SIGNAL TRACE REPORT: SMOKE TEST MR (DETAILED ADS FLOW)\033[0m")
    print("═"*160)
    print(f"{'TIMESTAMP':<20} | {'CAT':<12} | {'SYMBOL':<6} | {'PRICE':<10} | {'ACTION':<18} | {'OUTCOME':<12} | {'REASON / DETAILS'}")
    print("─"*160)
    
    sorted_traces = sorted(collector.traces, key=lambda x: (x.timestamp, x.bar_index))
    
    for t in sorted_traces:
        ts_str = t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else 'N/A'
        color_start = ""
        color_end = "\033[0m"
        if t.outcome in ['REJECTED', 'REMOVED', 'FILTERED']: color_start = "\033[91m"
        elif t.outcome in ['AUTHORIZED', 'MATURED', 'PASSED']: color_start = "\033[92m"
        elif t.outcome in ['QUEUED', 'EMITTED']: color_start = "\033[94m"
        elif t.outcome in ['PROACTIVE', 'BAKING']: color_start = "\033[93m"
        
        price_str = f"${t.price:,.2f}" if t.price is not None else "N/A"
        print(f"{ts_str:<20} | {t.category:<12} | {t.symbol:<6} | {price_str:<10} | {t.action:<18} | {color_start}{t.outcome:<12}{color_end} | {t.reason}")
        if t.details:
            detail_str = ", ".join([f"{k}={v}" for k, v in t.details.items() if k != 'log'])
            if detail_str:
                print(f"{'':<20} | {'':<12} | {'':<6} | {'':<10} | {'':<18} | {'':<12} |   └─ {detail_str}")

    print("═"*160 + "\n")

if __name__ == "__main__":
    asyncio.run(run_trace())
