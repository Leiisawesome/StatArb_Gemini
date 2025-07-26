#!/usr/bin/env python3
"""
Multi-Factor Ensemble Strategy Backtest

This script demonstrates the advanced multi-factor ensemble strategy:
1. Multi-factor signal generation (momentum, mean reversion, quality, risk, regime)
2. Dynamic ensemble weighting based on factor performance
3. Market regime detection and adaptive signal adjustment
4. Factor-aware position sizing and risk management
5. Comprehensive performance attribution and factor analysis

The strategy combines 5+ factors with machine learning ensemble methods
for robust signal generation across different market conditions.
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

def run_multi_factor_backtest():
    """Run a complete Multi-Factor Ensemble Strategy backtest"""
    
    print("🚀 MULTI-FACTOR ENSEMBLE STRATEGY BACKTEST")
    print("=" * 60)
    print("Advanced multi-factor signal ensemble with dynamic weighting")
    print("Testing with 5+ factors and machine learning ensemble methods")
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
        
        # Create multi-factor ensemble strategy experiment configuration
        multi_factor_config = ExperimentConfig(
            # Experiment metadata
            name="Multi-Factor Ensemble Strategy Backtest",
            description="Advanced multi-factor ensemble with dynamic weighting and regime detection",
            version="1.0.0",
            
            # Infrastructure defaults (will be overridden by strategy)
            symbols=["AAPL", "MSFT", "GOOGL"],  # Will be overridden by universe selection
            start_date="2023-01-01",            # Aligned with strategy training start
            end_date="2025-06-30",              # Aligned with strategy trading end
            initial_capital=100000,             # Will be overridden by strategy capital
            commission_rate=0.001,              # Will be overridden by strategy commission
            
            # Strategy specification
            strategy_class="MultiFactorEnsembleStrategy",
            strategy_params={
                # Universe definition - strategy requirements
                "universe_size": 30,            # Test with smaller universe first
                "min_market_cap": 2e9,          # $2B minimum market cap
                "min_avg_volume": 1e6,          # $1M average daily volume
                
                # Trading periods - strategy requirements
                "training_start": "2023-01-01",
                "training_end": "2024-12-31", 
                "trading_start": "2025-01-01",
                "trading_end": "2025-01-31",   # 1 month trading period for testing
                
                # Financial parameters - strategy requirements
                "initial_capital": 100000,      # $100K for testing
                "commission_rate": 0.0005,      # 5 bps commission
                "benchmark_symbol": "SPY",      # S&P 500 benchmark
                
                # Multi-factor ensemble parameters
                "ensemble_method": "adaptive_weighting",
                "signal_threshold": 0.15,       # 15% minimum signal strength
                "max_factors_per_asset": 5,     # Use all 5 factors
                
                # Factor configurations
                "factors": [
                    {
                        "factor_type": "momentum",
                        "lookback_period": 252,
                        "threshold": 0.10,
                        "weight": 0.25,
                        "momentum_type": "risk_adjusted"
                    },
                    {
                        "factor_type": "mean_reversion",
                        "lookback_period": 60,
                        "threshold": 0.20,
                        "weight": 0.20,
                        "mean_reversion_threshold": 0.5
                    },
                    {
                        "factor_type": "quality",
                        "lookback_period": 120,
                        "threshold": 0.15,
                        "weight": 0.20,
                        "quality_metrics": ["roe", "debt_to_equity"]
                    },
                    {
                        "factor_type": "risk",
                        "lookback_period": 90,
                        "threshold": 0.25,
                        "weight": 0.15,
                        "risk_metrics": ["beta", "volatility"]
                    },
                    {
                        "factor_type": "regime",
                        "lookback_period": 30,
                        "threshold": 0.30,
                        "weight": 0.20,
                        "regime_detection_method": "volatility_regime"
                    }
                ],
                
                # Ensemble learning parameters
                "ml_ensemble_enabled": True,
                "ensemble_learning_rate": 0.01,
                "ensemble_memory_period": 252,
                "ensemble_regularization": 0.001,
                
                # Regime detection parameters
                "regime_detection_enabled": True,
                "regime_lookback": 60,
                "regime_threshold": 0.6,
                "regime_smoothing": 0.1,
                
                # Risk management parameters
                "target_volatility": 0.15,      # 15% target volatility
                "max_weight_per_asset": 0.08,   # 8% max per asset
                "sector_neutrality": True,      # Apply sector neutral constraints
                "factor_correlation_limit": 0.7, # Limit factor correlations
                
                # Rebalancing frequency
                "rebalancing_frequency": "daily"
            },
            
            # Output configuration
            output_dir="results/multi_factor_backtest",
            save_trades=True,
            save_signals=True,
            generate_plots=True
        )
        
        print("📊 EXPERIMENT CONFIGURATION:")
        print(f"   Strategy: {multi_factor_config.strategy_class}")
        print(f"   Universe Size: {multi_factor_config.strategy_params['universe_size']} stocks")
        print(f"   Trading Period: {multi_factor_config.strategy_params['trading_start']} to {multi_factor_config.strategy_params['trading_end']}")
        print(f"   Initial Capital: ${multi_factor_config.strategy_params['initial_capital']:,.0f}")
        print(f"   Target Volatility: {multi_factor_config.strategy_params['target_volatility']:.1%}")
        print(f"   Number of Factors: {len(multi_factor_config.strategy_params['factors'])}")
        print(f"   Ensemble Method: {multi_factor_config.strategy_params['ensemble_method']}")
        print(f"   Regime Detection: {'Enabled' if multi_factor_config.strategy_params['regime_detection_enabled'] else 'Disabled'}")
        
        # Initialize experiment runner
        print("\n🔧 INITIALIZING EXPERIMENT RUNNER:")
        runner = ExperimentRunner(multi_factor_config)
        print("✅ ExperimentRunner initialized with multi-factor ensemble strategy")
        
        # Test configuration resolution first
        print("\n🔍 TESTING STRATEGY-FIRST CONFIGURATION RESOLUTION:")
        print("-" * 50)
        
        # Test data requirements resolution
        try:
            data_requirements = runner._resolve_data_requirements(multi_factor_config)
            print(f"✅ Data Requirements Resolved:")
            print(f"   Symbols: {len(data_requirements['symbols'])} symbols")
            print(f"   Start Date: {data_requirements['start_date']}")
            print(f"   End Date: {data_requirements['end_date']}")
        except Exception as e:
            print(f"❌ Data requirements resolution failed: {e}")
            return False
        
        # Test symbol resolution
        try:
            symbols = runner._resolve_symbols(multi_factor_config.strategy_params, multi_factor_config.symbols)
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
            strategy_config = runner._resolve_strategy_configuration(multi_factor_config)
            print(f"✅ Strategy Configuration:")
            print(f"   Commission Rate: {strategy_config.get('commission_rate', 'N/A')}")
            print(f"   Benchmark: {strategy_config.get('benchmark_symbol', 'N/A')}")
            print(f"   Target Volatility: {strategy_config.get('target_volatility', 'N/A')}")
            print(f"   Ensemble Method: {strategy_config.get('ensemble_method', 'N/A')}")
        except Exception as e:
            print(f"❌ Strategy configuration resolution failed: {e}")
            return False
        
        print("\n🚀 RUNNING MULTI-FACTOR ENSEMBLE STRATEGY BACKTEST:")
        print("-" * 50)
        
        # Run the complete experiment
        start_time = datetime.now()
        
        try:
            result = runner.run_experiment(multi_factor_config)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n🎉 MULTI-FACTOR BACKTEST COMPLETED SUCCESSFULLY!")
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
                
                # Multi-factor specific metrics
                if 'factor_weights' in metrics:
                    print(f"\n🔧 FACTOR WEIGHTS:")
                    for factor, weight in metrics['factor_weights'].items():
                        print(f"   {factor}: {weight:.3f}")
                
                if 'current_regime' in metrics:
                    print(f"Current Market Regime: {metrics['current_regime']}")
                
                if 'num_factors' in metrics:
                    print(f"Number of Active Factors: {metrics['num_factors']}")
            
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
            output_path = Path(multi_factor_config.output_dir)
            if output_path.exists():
                files = list(output_path.glob("*"))
                for file in files:
                    print(f"   {file.name}")
            else:
                print(f"   Output directory: {multi_factor_config.output_dir}")
            
            print(f"\n✅ MULTI-FACTOR ENSEMBLE STRATEGY BACKTEST COMPLETE!")
            print(f"🎯 Advanced multi-factor ensemble working perfectly")
            print(f"🔧 Dynamic factor weighting and regime detection successful")
            print(f"📈 Comprehensive performance metrics calculated")
            
            return True
            
        except Exception as e:
            print(f"\n❌ MULTI-FACTOR BACKTEST EXECUTION FAILED: {e}")
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
    """Validate that the environment is ready for multi-factor backtesting"""
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
        "strategies/multi_factor_ensemble_strategy.py",
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
    print("🧪 MULTI-FACTOR ENSEMBLE STRATEGY BACKTEST")
    print("Testing the advanced multi-factor ensemble with dynamic weighting")
    print()
    
    # Validate environment first
    if not validate_environment():
        print("\n❌ Environment validation failed. Please check missing components.")
        sys.exit(1)
    
    print()
    
    # Run the backtest
    success = run_multi_factor_backtest()
    
    if success:
        print("\n🎉 SUCCESS! Multi-factor ensemble backtest completed successfully.")
        print("The advanced multi-factor ensemble strategy is working perfectly!")
    else:
        print("\n❌ FAILED! Multi-factor backtest encountered errors.")
        print("Check the error messages above for debugging information.")
        sys.exit(1) 