"""
Debug Script: Check Indicator Calculation in Backtest Engine
=============================================================

Temporary diagnostic tool to understand why signals aren't being generated.
This will be deleted after we identify the issue.
"""

import asyncio
import logging
import pandas as pd
from datetime import datetime
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

async def debug_indicators():
    """Debug indicator calculation"""
    
    config_dict = {
        'backtest_name': 'Debug_Indicators',
        'symbols': ['TSLA'],
        'interval': '1min',
        'start_date': '2024-12-20',
        'end_date': '2024-12-20',
        'initial_capital': 100000,
        'strategies': [{
            'type': 'mean_reversion',
            'name': 'MR_Debug',
            'allocation_pct': 1.0,
            'parameters': {
                'lookback': 20,
                'zscore_entry_threshold': 2.0,
                'zscore_exit_threshold': 0.5,
                'scan_all_bars': False,
                'enable_regime_filter': False
            }
        }]
    }
    
    print("="*80)
    print("🔍 DIAGNOSTIC: Indicator Calculation in Backtest Engine")
    print("="*80)
    
    config = BacktestConfig(**config_dict)
    engine = InstitutionalBacktestEngine(config)
    
    # Initialize (loads data and pre-calculates indicators)
    print("\n1️⃣ Initializing engine...")
    await engine.initialize()
    
    # Check historical data
    print(f"\n2️⃣ Historical Data:")
    print(f"   Shape: {engine.historical_data.shape}")
    print(f"   Columns: {engine.historical_data.columns.tolist()}")
    
    # Check pre-calculated indicators
    print(f"\n3️⃣ Pre-calculated Indicators:")
    if engine.pre_calculated_indicators is not None:
        print(f"   Shape: {engine.pre_calculated_indicators.shape}")
        print(f"   Columns ({len(engine.pre_calculated_indicators.columns)}):")
        for col in sorted(engine.pre_calculated_indicators.columns):
            print(f"     - {col}")
        
        # Check for required indicators
        print(f"\n4️⃣ Checking Required Indicators:")
        required = ['zscore', 'rsi', 'bb_upper', 'bb_lower', 'bb_middle', 'bb_position']
        for col in required:
            if col in engine.pre_calculated_indicators.columns:
                recent = engine.pre_calculated_indicators[col].iloc[-50:]
                non_nan = recent.dropna()
                if len(non_nan) > 0:
                    print(f"   ✅ {col:<20} [min: {non_nan.min():.2f}, max: {non_nan.max():.2f}, last: {non_nan.iloc[-1]:.2f}]")
                else:
                    print(f"   ⚠️  {col:<20} ALL NaN!")
            else:
                print(f"   ❌ {col:<20} MISSING!")
    else:
        print("   ❌ pre_calculated_indicators is None!")
    
    # Check pre-calculated features
    print(f"\n5️⃣ Pre-calculated Features:")
    if engine.pre_calculated_features is not None:
        print(f"   Shape: {engine.pre_calculated_features.shape}")
        print(f"   Has zscore: {'zscore' in engine.pre_calculated_features.columns}")
        print(f"   Has rsi: {'rsi' in engine.pre_calculated_features.columns}")
        print(f"   Has bb_position: {'bb_position' in engine.pre_calculated_features.columns}")
    else:
        print("   ❌ pre_calculated_features is None!")
    
    # Analyze last 10 bars for signal potential
    if engine.pre_calculated_features is not None:
        print(f"\n6️⃣ Last 10 Bars Analysis:")
        df = engine.pre_calculated_features.iloc[-10:].copy()
        
        # Check if required columns exist
        has_zscore = 'zscore' in df.columns
        has_rsi = 'rsi' in df.columns
        has_bb = 'bb_position' in df.columns
        
        print(f"   Has zscore: {has_zscore}")
        print(f"   Has rsi: {has_rsi}")
        print(f"   Has bb_position: {has_bb}")
        
        if has_zscore and has_rsi and has_bb:
            # Check entry conditions
            df['buy_zscore'] = df['zscore'] < -2.0
            df['buy_rsi'] = df['rsi'] < 30
            df['buy_bb'] = df['bb_position'] < 0.2
            df['buy_all'] = df['buy_zscore'] & df['buy_rsi'] & df['buy_bb']
            
            print(f"\n   Entry Criteria (Last 10 Bars):")
            print(f"   Bars with z < -2.0:       {df['buy_zscore'].sum()}")
            print(f"   Bars with rsi < 30:       {df['buy_rsi'].sum()}")
            print(f"   Bars with bb_pos < 0.2:   {df['buy_bb'].sum()}")
            print(f"   Bars meeting ALL 3:       {df['buy_all'].sum()}")
            
            if df['buy_all'].sum() > 0:
                print(f"\n   ✅ LAST 10 BARS INCLUDE VALID SIGNALS!")
                sample = df[df['buy_all']].iloc[0]
                print(f"   Example at index {sample.name}:")
                print(f"     Close: ${sample.get('close', 0):.2f}")
                print(f"     Z-score: {sample['zscore']:.2f}")
                print(f"     RSI: {sample['rsi']:.2f}")
                print(f"     BB Position: {sample['bb_position']:.2f}")
            else:
                print(f"\n   ⚠️  Last 10 bars don't meet criteria")
                print(f"\n   Last bar values:")
                last = df.iloc[-1]
                print(f"     Z-score: {last['zscore']:.2f} (need < -2.0)")
                print(f"     RSI: {last['rsi']:.2f} (need < 30)")
                print(f"     BB Position: {last['bb_position']:.2f} (need < 0.2)")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(debug_indicators())

