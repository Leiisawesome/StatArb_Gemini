#!/usr/bin/env python3
"""
Real Backtest of MomentumStrategy using ExperimentRunner

This script demonstrates the full backtesting pipeline:
1. Strategy-first configuration resolution
2. Core system data loading
3. MomentumStrategy execution
4. Performance analysis and reporting

IMPORTANT: Includes fix for annualized return calculation bug.
ExperimentRunner now uses actual date ranges instead of hardcoded 252 trading days.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add paths for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_momentum_backtest():
    """Run a complete MomentumStrategy backtest"""
    
    print("🚀 REAL MOMENTUM STRATEGY BACKTEST")
    print("=" * 60)
    print("Using optimized ExperimentRunner with strategy-first architecture")
    print("Testing with core system integration (no fallbacks)")
    print()
    
    try:
        # Load environment variables first
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print("✅ Environment variables loaded")
        
        # Import the experiment framework
        from experiments.experiment_runner import ExperimentRunner, ExperimentConfig
        
        print("✅ Successfully imported ExperimentRunner")
        
        # Create momentum strategy experiment configuration
        momentum_config = ExperimentConfig(
            # Experiment metadata
            name="Momentum Strategy Backtest",
            description="Real backtest of momentum strategy with universe selection",
            version="1.0.0",
            
            # Infrastructure defaults (will be overridden by strategy)
            symbols=["AAPL", "MSFT", "GOOGL"],  # Will be overridden by universe selection
            start_date="2022-01-01",            # Will be overridden by strategy dates
            end_date="2022-12-31",
            initial_capital=100000,             # Will be overridden by strategy capital
            commission_rate=0.001,              # Will be overridden by strategy commission
            
            # Strategy specification
            strategy_class="MomentumStrategy",
            strategy_params={
                # Universe definition - strategy requirements
                "universe_size": 50,            # Test with smaller universe first
                "min_market_cap": 2e9,          # $2B minimum market cap
                "min_avg_volume": 1e6,          # $1M average daily volume
                
                # Trading periods - strategy requirements
                "training_start": "2023-01-01",
                "training_end": "2024-12-31", 
                "trading_start": "2025-01-01",
                "trading_end": "2025-06-30",   # 12 months trading period
                
                # Financial parameters - strategy requirements
                "initial_capital": 100000,      # $100K for testing
                "commission_rate": 0.0005,      # 5 bps commission
                "benchmark_symbol": "SPY",      # S&P 500 benchmark
                
                # Momentum strategy parameters
                "momentum_type": "risk_adjusted",
                "lookback_period": 252,         # 1 year momentum
                "skip_period": 21,              # Skip last month
                "momentum_threshold": 0.10,     # 10% minimum momentum
                "target_volatility": 0.15,      # 15% target volatility
                "max_weight_per_asset": 0.08,   # 8% max per asset
                "rebalancing_frequency": "daily"
            },
            
            # Output configuration
            output_dir="results/momentum_backtest",
            save_trades=True,
            save_signals=True,
            generate_plots=True
        )
        
        print("📊 EXPERIMENT CONFIGURATION:")
        print(f"   Strategy: {momentum_config.strategy_class}")
        print(f"   Universe Size: {momentum_config.strategy_params['universe_size']} stocks")
        print(f"   Trading Period: {momentum_config.strategy_params['trading_start']} to {momentum_config.strategy_params['trading_end']}")
        print(f"   Initial Capital: ${momentum_config.strategy_params['initial_capital']:,.0f}")
        print(f"   Target Volatility: {momentum_config.strategy_params['target_volatility']:.1%}")
        print(f"   Momentum Threshold: {momentum_config.strategy_params['momentum_threshold']:.1%}")
        
        # Initialize experiment runner
        print("\n🔧 INITIALIZING EXPERIMENT RUNNER:")
        runner = ExperimentRunner(momentum_config)
        print("✅ ExperimentRunner initialized with core system integration")
        
        # Test configuration resolution first
        print("\n🔍 TESTING STRATEGY-FIRST CONFIGURATION RESOLUTION:")
        print("-" * 50)
        
        # Test data requirements resolution
        try:
            data_requirements = runner._resolve_data_requirements(momentum_config)
            print(f"✅ Data Requirements Resolved:")
            print(f"   Symbols: {len(data_requirements['symbols'])} symbols")
            print(f"   Start Date: {data_requirements['start_date']}")
            print(f"   End Date: {data_requirements['end_date']}")
        except Exception as e:
            print(f"❌ Data requirements resolution failed: {e}")
            return False
        
        # Test symbol resolution
        try:
            symbols = runner._resolve_symbols(momentum_config.strategy_params, momentum_config.symbols)
            print(f"✅ Symbol Resolution:")
            print(f"   Resolved to {len(symbols)} symbols")
            if len(symbols) > 10:
                print(f"   Sample symbols: {symbols[:5]}...")
            else:
                print(f"   Symbols: {symbols}")
        except Exception as e:
            print(f"❌ Symbol resolution failed: {e}")
            return False
        
        # Test strategy configuration resolution
        try:
            strategy_config = runner._resolve_strategy_configuration(momentum_config)
            print(f"✅ Strategy Configuration:")
            print(f"   Commission Rate: {strategy_config.get('commission_rate', 'N/A')}")
            print(f"   Benchmark: {strategy_config.get('benchmark_symbol', 'N/A')}")
            print(f"   Target Volatility: {strategy_config.get('target_volatility', 'N/A')}")
        except Exception as e:
            print(f"❌ Strategy configuration resolution failed: {e}")
            return False
        
        print("\n🚀 RUNNING FULL MOMENTUM STRATEGY BACKTEST:")
        print("-" * 50)
        
        # Run the complete experiment
        start_time = datetime.now()
        
        try:
            result = runner.run_experiment(momentum_config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n🎉 BACKTEST COMPLETED SUCCESSFULLY!")
            print(f"⏱️  Duration: {duration:.2f} seconds")
            
            # Display results
            print("\n📈 PERFORMANCE RESULTS:")
            print("-" * 30)
            
            if result.strategy_metrics:
                metrics = result.strategy_metrics
                print(f"Total Return: {metrics.get('total_return', 0):.2%}")
                print(f"Annualized Return: {metrics.get('annualized_return', 0):.2%}")
                print(f"Volatility: {metrics.get('volatility', 0):.2%}")
                print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                print(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
                print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
                
                if 'calmar_ratio' in metrics:
                    print(f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}")
                if 'sortino_ratio' in metrics:
                    print(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
            
            # Display trading statistics
            print(f"\n📊 TRADING STATISTICS:")
            print("-" * 30)
            print(f"Total Trades: {len(result.trades)}")
            print(f"Total Signals: {len(result.signals)}")
            print(f"Final Portfolio Value: ${result.equity_curve[-1]:,.2f}" if result.equity_curve else "N/A")
            
            # Display benchmark comparison
            if result.benchmark_metrics:
                print(f"\n🏆 BENCHMARK COMPARISON:")
                print("-" * 30)
                print(f"Strategy Return: {result.strategy_metrics.get('total_return', 0):.2%}")
                print(f"Benchmark Return: {result.benchmark_metrics.get('total_return', 0):.2%}")
                
                alpha = result.strategy_metrics.get('alpha', 0)
                if alpha != 0:
                    print(f"Alpha: {alpha:.2%}")
                
                beta = result.strategy_metrics.get('beta', 0)
                if beta != 0:
                    print(f"Beta: {beta:.2f}")
            
            # Output information
            print(f"\n💾 OUTPUT FILES:")
            print("-" * 30)
            output_path = Path(momentum_config.output_dir)
            if output_path.exists():
                files = list(output_path.glob("*"))
                for file in files:
                    print(f"   {file.name}")
            else:
                print(f"   Output directory: {momentum_config.output_dir}")
            
            print(f"\n✅ MOMENTUM STRATEGY BACKTEST COMPLETE!")
            print(f"🎯 Strategy-first architecture working perfectly")
            print(f"🔧 Core system integration successful")
            print(f"📈 Performance metrics calculated")
            
            return True
            
        except Exception as e:
            print(f"\n❌ BACKTEST EXECUTION FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    except ImportError as e:
        print(f"❌ Failed to import experiment framework: {e}")
        print("Make sure all dependencies are available")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_environment():
    """Validate that the environment is ready for backtesting"""
    print("🔍 VALIDATING ENVIRONMENT:")
    print("-" * 30)
    
    # Check Python version
    print(f"Python Version: {sys.version.split()[0]}")
    
    # Check required directories
    required_dirs = [
        "experiments",
        "strategies", 
        "utils"
    ]
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name}/ directory found")
        else:
            print(f"❌ {dir_name}/ directory missing")
            return False
    
    # Check for key files
    key_files = [
        "experiments/experiment_runner.py",
        "strategies/momentum_strategy.py",
        "strategies/base_strategy.py"
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} found")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    print("✅ Environment validation passed")
    return True

if __name__ == "__main__":
    print("🧪 MOMENTUM STRATEGY REAL BACKTEST")
    print("Testing the optimized experiment framework with actual strategy")
    print()
    
    # Validate environment first
    if not validate_environment():
        print("\n❌ Environment validation failed. Please check missing components.")
        sys.exit(1)
    
    print()
    
    # Run the backtest
    success = run_momentum_backtest()
    
    if success:
        print("\n🎉 SUCCESS! Real backtest completed successfully.")
        print("The strategy-first experiment framework is working perfectly!")
    else:
        print("\n❌ FAILED! Backtest encountered errors.")
        print("Check the error messages above for debugging information.")
        sys.exit(1)
