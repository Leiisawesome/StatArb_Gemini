#!/usr/bin/env python3
"""
Advanced Momentum Backtest Examples
===================================

Examples of how to run the advanced momentum backtest with different configurations.
Demonstrates the flexible configuration system for easy testing of different
trading periods, symbols, and parameters.

Usage Examples:
  python run_backtest_examples.py --quick              # Quick single-day test
  python run_backtest_examples.py --comprehensive      # Full week test  
  python run_backtest_examples.py --custom AAPL MSFT   # Custom symbols
  python run_backtest_examples.py --scenario quick_test # Predefined scenario
"""

import asyncio
import argparse
import sys
import os
from typing import List, Dict, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testing_framework.advanced_momentum_backtest import (
    main as run_backtest,
    run_custom_test,
    run_scenario_test
)
from testing_framework.config.config_manager import TestConfigManager

def print_available_configs():
    """Print all available configurations"""
    try:
        config_manager = TestConfigManager()
        
        print("🔧 AVAILABLE CONFIGURATIONS")
        print("=" * 50)
        
        print("\n📈 Trading Periods:")
        periods = config_manager.list_available_periods()
        for period in periods:
            period_config = config_manager.get_trading_period(period)
            print(f"  • {period}: {period_config.start_date} to {period_config.end_date} ({period_config.description})")
        
        print("\n🎯 Strategies:")
        strategies = config_manager.list_available_strategies()
        for strategy in strategies:
            strategy_config = config_manager.get_strategy_config(strategy)
            print(f"  • {strategy}: {strategy_config.template} - {strategy_config.symbols}")
        
        print("\n🎬 Scenarios:")
        scenarios = config_manager.list_available_scenarios()
        for scenario in scenarios:
            scenario_config = config_manager.get_scenario_config(scenario)
            print(f"  • {scenario}: {scenario_config.get('description', 'No description')}")
        
        print("\n🌐 Universe Categories:")
        universe = config_manager.get_universe()
        for category, symbols in universe.categories.items():
            print(f"  • {category}: {symbols}")
            
    except Exception as e:
        print(f"❌ Error loading configurations: {e}")

async def run_quick_example():
    """Run quick single-day momentum test"""
    print("🚀 Running Quick Test (Single Day)")
    print("=" * 40)
    await run_backtest("advanced_momentum")

async def run_comprehensive_example():
    """Run comprehensive multi-day test"""
    print("🚀 Running Comprehensive Test (One Week)")
    print("=" * 45)
    
    # Custom configuration for comprehensive test
    custom_config = {
        'strategy': {
            'symbols': ['TSLA', 'AAPL']
        },
        'trading_period': {
            'period': 'one_week'
        }
    }
    await run_backtest("advanced_momentum", custom_config)

async def run_custom_symbols_example(symbols: List[str]):
    """Run test with custom symbols"""
    print(f"🚀 Running Custom Symbols Test: {symbols}")
    print("=" * 50)
    
    custom_config = {
        'strategy': {
            'symbols': symbols
        }
    }
    await run_backtest("advanced_momentum", custom_config)

async def run_different_timeframes_example():
    """Run tests with different timeframes"""
    timeframes = [
        ('1min', 'High-frequency 1-minute'),
        ('5min', 'Medium-frequency 5-minute'),
        ('15min', 'Lower-frequency 15-minute')
    ]
    
    for interval, description in timeframes:
        print(f"🚀 Running {description} Test")
        print("=" * 40)
        
        custom_config = {
            'data': {
                'interval': interval
            }
        }
        await run_backtest("advanced_momentum", custom_config)
        print()

async def run_risk_parameter_tests():
    """Test different risk management parameters"""
    risk_configs = [
        {
            'name': 'Conservative',
            'config': {
                'strategy': {
                    'parameters': {
                        'max_position_size': 0.05,  # 5% max position
                        'momentum_threshold': 0.8   # Higher threshold
                    }
                }
            }
        },
        {
            'name': 'Aggressive', 
            'config': {
                'strategy': {
                    'parameters': {
                        'max_position_size': 0.20,  # 20% max position
                        'momentum_threshold': 0.4   # Lower threshold
                    }
                }
            }
        }
    ]
    
    for risk_config in risk_configs:
        print(f"🚀 Running {risk_config['name']} Risk Test")
        print("=" * 40)
        await run_backtest("advanced_momentum", risk_config['config'])
        print()

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Advanced Momentum Backtest Examples')
    parser.add_argument('--quick', action='store_true', help='Run quick single-day test')
    parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive week test')
    parser.add_argument('--custom', nargs='+', help='Run with custom symbols')
    parser.add_argument('--scenario', help='Run predefined scenario')
    parser.add_argument('--timeframes', action='store_true', help='Test different timeframes')
    parser.add_argument('--risk-tests', action='store_true', help='Test different risk parameters')
    parser.add_argument('--list-configs', action='store_true', help='List all available configurations')
    
    args = parser.parse_args()
    
    if args.list_configs:
        print_available_configs()
        return
    
    try:
        if args.quick:
            asyncio.run(run_quick_example())
        elif args.comprehensive:
            asyncio.run(run_comprehensive_example())
        elif args.custom:
            asyncio.run(run_custom_symbols_example(args.custom))
        elif args.scenario:
            run_scenario_test(args.scenario)
        elif args.timeframes:
            asyncio.run(run_different_timeframes_example())
        elif args.risk_tests:
            asyncio.run(run_risk_parameter_tests())
        else:
            # Default: show available options
            print("🎯 ADVANCED MOMENTUM BACKTEST EXAMPLES")
            print("=" * 50)
            print("\nAvailable options:")
            print("  --quick              Quick single-day test")
            print("  --comprehensive      Comprehensive week test")
            print("  --custom SYMBOLS     Test with custom symbols (e.g., AAPL MSFT)")
            print("  --scenario NAME      Run predefined scenario")
            print("  --timeframes         Test different timeframes")
            print("  --risk-tests         Test different risk parameters")
            print("  --list-configs       Show all available configurations")
            print("\nExample:")
            print("  python run_backtest_examples.py --custom AAPL MSFT GOOGL")
            print("  python run_backtest_examples.py --scenario quick_test")
            print("\nFor detailed configuration, edit testing_framework/config/test_config.yaml")
            
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()
