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

# --- TRACE COLLECTION ENGINE ---

class SignalTrace:
    def __init__(self, timestamp, bar_index, category, symbol, action, outcome, reason, details=None):
        self.timestamp = timestamp
        self.bar_index = bar_index
        self.category = category
        self.symbol = symbol
        self.action = action
        self.outcome = outcome
        self.reason = reason
        self.details = details or {}

class TraceCollector:
    def __init__(self):
        self.traces: List[SignalTrace] = []
        self.current_bar_time = None
        self.current_bar_index = 0

    def add(self, category, symbol, action, outcome, reason, details=None):
        trace = SignalTrace(
            self.current_bar_time, 
            self.current_bar_index, 
            category, 
            symbol, 
            action, 
            outcome, 
            reason, 
            details
        )
        self.traces.append(trace)

collector = TraceCollector()

# --- LOG INTERCEPTOR ---

class TraceLogHandler(logging.Handler):
    """Intercepts logs from strategy and risk manager to extract rejections."""
    def emit(self, record):
        msg = record.getMessage()
        
        # Strategy rejections
        if "EnhancedMeanReversion" in record.name:
            if "REJECTED" in msg:
                # [TSLA] Signal long_entry REJECTED: Confidence 0.82 <= 0.85
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                reason = msg.split('REJECTED: ')[1] if 'REJECTED: ' in msg else msg
                collector.add('STRATEGY', sym, 'SIGNAL', 'REJECTED', reason, {'log': msg})
            elif "PROACTIVE STOP-LOSS TRIGGERED" in msg:
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                collector.add('STRATEGY', sym, 'EXIT', 'PROACTIVE', 'Stop Loss Triggered', {'log': msg})
            elif "RSI overbought but still rising - HOLD" in msg:
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                collector.add('STRATEGY', sym, 'EXIT', 'REJECTED', 'Momentum Rising', {'log': msg})
            elif "RSI oversold but still falling - HOLD" in msg:
                sym_match = re.search(r'\[(\w+)\]', msg)
                sym = sym_match.group(1) if sym_match else '?'
                collector.add('STRATEGY', sym, 'EXIT', 'REJECTED', 'Momentum Falling', {'log': msg})
        
        # Risk Manager rejections
        if "CentralRiskManager" in record.name:
            if "FAILED" in msg:
                # Extract details using regex
                sym_match = re.search(r'FAILED: (\w+)', msg)
                pct_match = re.search(r'Position %: ([\d.]+)%', msg)
                limit_match = re.search(r'Limit: ([\d.]+)%', msg)
                conc_match = re.search(r'Concentration: ([\d.]+)%', msg)
                
                sym = sym_match.group(1) if sym_match else '?'
                reason = "Risk Limit"
                if pct_match and limit_match:
                    reason = f"Position Limit ({pct_match.group(1)}% > {limit_match.group(1)}%)"
                elif conc_match and limit_match:
                    reason = f"Concentration Limit ({conc_match.group(1)}% > {limit_match.group(1)}%)"
                
                collector.add('RISK', sym, '?', 'REJECTED', reason, {'log': msg})
            elif "Signal confidence" in msg and "below minimum" in msg:
                # Signal confidence 0.82 below minimum 0.85
                conf_match = re.search(r'confidence ([\d.]+)', msg)
                min_match = re.search(r'minimum ([\d.]+)', msg)
                reason = "Confidence < Threshold"
                if conf_match and min_match:
                    reason = f"Confidence {conf_match.group(1)} < {min_match.group(1)}"
                collector.add('RISK', '?', '?', 'REJECTED', reason, {'log': msg})
            elif "Insufficient cash" in msg:
                # 🔒 BUY rejected: Insufficient cash. Need $10,000.00, have $5,000.00
                need_match = re.search(r'Need \$([\d,.]+)', msg)
                have_match = re.search(r'have \$([\d,.]+)', msg)
                reason = "Insufficient Cash"
                if need_match and have_match:
                    reason = f"Insufficient Cash (Need ${need_match.group(1)}, Have ${have_match.group(1)})"
                collector.add('RISK', '?', '?', 'REJECTED', reason, {'log': msg})

# Setup log interception
trace_handler = TraceLogHandler()
trace_handler.setLevel(logging.DEBUG)
for name in ["core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion", 
             "core_engine.system.central_risk_manager"]:
    l = logging.getLogger(name)
    l.addHandler(trace_handler)
    l.setLevel(logging.DEBUG)

# --- METHOD HOOKS ---

# Hook into Strategy generate_signals
original_generate_signals = EnhancedMeanReversionStrategy.generate_signals
async def traced_generate_signals(self, enriched_data, position_details=None):
    result = await original_generate_signals(self, enriched_data, position_details)
    if result:
        for signal in result:
            collector.add(
                'STRATEGY', 
                signal.symbol, 
                signal.signal_type.value, 
                'EMITTED', 
                'Strategy filters passed',
                {'confidence': f"{signal.confidence:.2%}", 'strength': f"{getattr(signal, 'strength', 0.5):.2f}"}
            )
    return result

# Hook into Risk Manager
original_authorize = CentralRiskManager.authorize_trading_decision
async def traced_authorize(self, request: TradingDecisionRequest):
    result = await original_authorize(self, request)
    outcome = 'AUTHORIZED' if result.authorization_level != AuthorizationLevel.REJECTED else 'REJECTED'
    
    # Extract more granular rejection reason
    reason = result.rejection_reason
    if not reason:
        if outcome == 'AUTHORIZED':
            reason = 'Risk limits passed'
        else:
            reason = 'Unknown risk rejection'
    
    # Check if we already have a more detailed RISK trace from logs for this symbol/timestamp
    has_detailed = any(t.timestamp == collector.current_bar_time and t.category == 'RISK' and t.symbol == request.symbol and '(' in t.reason for t in collector.traces)
    
    if outcome == 'AUTHORIZED' or not has_detailed:
        # If it's a rejection and we already have a detailed one, update the existing one's action
        detailed_trace = next((t for t in collector.traces if t.timestamp == collector.current_bar_time and t.category == 'RISK' and t.symbol == request.symbol), None)
        if detailed_trace:
            detailed_trace.action = f"{request.side} ({request.decision_type.name})"
            detailed_trace.details.update({
                'requested_qty': f"{request.quantity:.2f}",
                'authorized_qty': f"{result.authorized_quantity:.2f}",
                'confidence': f"{request.confidence:.2%}"
            })
        else:
            collector.add(
                'RISK',
                request.symbol,
                f"{request.side} ({request.decision_type.name})",
                outcome,
                reason,
                {
                    'requested_qty': f"{request.quantity:.2f}",
                    'authorized_qty': f"{result.authorized_quantity:.2f}",
                    'confidence': f"{request.confidence:.2%}"
                }
            )
    return result

# Hook into ADS Queue
original_queue_add = PendingSignalQueue.add
def traced_queue_add(self, ctx: PendingSignalContext):
    # regime might not be available directly on ctx if it's an older version
    regime = getattr(ctx, 'regime', 'UNKNOWN')
    sms_val = ctx.sms.compute(regime) if hasattr(ctx.sms, 'compute') else 0.0
    
    collector.add(
        'ADS_QUEUE',
        ctx.symbol,
        ctx.side,
        'QUEUED',
        f'Awaiting maturation (SMS={sms_val:.3f})',
        {'entry_price': f"${ctx.entry_price:.2f}"}
    )
    return original_queue_add(self, ctx)

original_queue_mature = PendingSignalQueue.get_mature_signals
def traced_queue_mature(self, threshold, regime):
    result = original_queue_mature(self, threshold, regime)
    for ctx in result:
        sms_val = ctx.sms.compute(regime) if hasattr(ctx.sms, 'compute') else 0.0
        collector.add(
            'ADS_QUEUE',
            ctx.symbol,
            ctx.side,
            'MATURED',
            f'Maturation complete (SMS={sms_val:.3f} >= {threshold})'
        )
    return result

# --- RUNNER ---

async def run_trace():
    config_path = 'core_engine/config/catalog/suites/smoke_test_mr.yaml'
    base_config_path = 'backtest/configs/base_config.yaml'
    
    print(f"\033[1m🚀 Initializing Smoke Test Trace...\033[0m")
    
    # Check if config exists
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return

    config_dict = load_config(config_path, base_config_path)
    
    # Use SmokeTest class to create proper BacktestConfig
    smoke_test_exp = SmokeTest(config_dict)
    backtest_config = smoke_test_exp._create_backtest_config()
    
    engine = InstitutionalBacktestEngine(backtest_config)
    
    # Apply monkey patches
    patches = [
        unittest.mock.patch.object(EnhancedMeanReversionStrategy, 'generate_signals', traced_generate_signals),
        unittest.mock.patch.object(CentralRiskManager, 'authorize_trading_decision', traced_authorize),
        unittest.mock.patch.object(PendingSignalQueue, 'add', traced_queue_add),
        unittest.mock.patch.object(PendingSignalQueue, 'get_mature_signals', traced_queue_mature)
    ]
    
    for p in patches:
        p.start()
        
    # Hook _process_single_bar to update collector time
    original_process_single_bar = engine._process_single_bar
    async def traced_process_single_bar(self, bar, timestamp, bar_index, pre_calc_index=0):
        collector.current_bar_time = timestamp
        collector.current_bar_index = bar_index
        return await original_process_single_bar(bar, timestamp, bar_index, pre_calc_index)
    
    try:
        # Also need to hook initialize to set initial time
        await engine.initialize()
        
        with unittest.mock.patch.object(InstitutionalBacktestEngine, '_process_single_bar', traced_process_single_bar):
            print(f"📈 Running Backtest Engine ({backtest_config.start_date} to {backtest_config.end_date})...")
            # Set engine logger to ERROR to prevent console noise
            logging.getLogger('backtest.engine').setLevel(logging.ERROR)
            await engine.run_backtest()
    finally:
        for p in patches:
            try:
                p.stop()
            except:
                pass

    # --- REPORTING ---
    
    print("\n" + "═"*140)
    print(f"\033[1m📊 SIGNAL TRACE REPORT: SMOKE TEST MR\033[0m")
    print("═"*140)
    print(f"{'TIMESTAMP':<20} | {'CAT':<10} | {'SYMBOL':<6} | {'ACTION':<18} | {'OUTCOME':<12} | {'REASON / DETAILS'}")
    print("─"*140)
    
    if not collector.traces:
        print(f"{' '*50}NO SIGNALS GENERATED DURING THIS RUN")
    
    # Sort traces by timestamp and bar index
    sorted_traces = sorted(collector.traces, key=lambda x: (x.timestamp, x.bar_index))
    
    last_ts = None
    for t in sorted_traces:
        ts_str = t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else 'N/A'
        
        # Add visual separator for new bars
        if last_ts and ts_str != last_ts:
            # print("-" * 140)
            pass
        last_ts = ts_str
        
        color_start = ""
        color_end = "\033[0m"
        if t.outcome == 'REJECTED': color_start = "\033[91m" # Red
        elif t.outcome == 'AUTHORIZED' or t.outcome == 'MATURED': color_start = "\033[92m" # Green
        elif t.outcome == 'QUEUED' or t.outcome == 'EMITTED': color_start = "\033[94m" # Blue
        elif t.outcome == 'PROACTIVE': color_start = "\033[93m" # Yellow
        
        print(f"{ts_str:<20} | {t.category:<10} | {t.symbol:<6} | {t.action:<18} | {color_start}{t.outcome:<12}{color_end} | {t.reason}")
        if t.details:
            detail_str = ", ".join([f"{k}={v}" for k, v in t.details.items() if k != 'log'])
            if detail_str:
                print(f"{'':<20} | {'':<10} | {'':<6} | {'':<18} | {'':<12} |   └─ {detail_str}")

    print("═"*140 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(run_trace())
    except KeyboardInterrupt:
        print("\n👋 Trace interrupted by user.")
    except Exception as e:
        print(f"❌ Error during trace: {e}")
        import traceback
        traceback.print_exc()
