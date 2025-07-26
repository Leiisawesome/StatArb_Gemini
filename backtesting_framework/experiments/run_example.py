#!/usr/bin/env python3
"""
Example script demonstrating the backtesting framework

This script shows how to:
1. Run a simple backtest with default configuration
2. Run a backtest from a configuration file
3. Analyze and display results
"""

import sys
import os
from pathlib import Path

# Add the backtesting framework to the path
sys.path.append(str(Path(__file__).parent.parent))

from experiments.experiment_runner import ExperimentRunner, ExperimentConfig
from strategies.pairs_trading import PairsTradingStrategy, PairsTradingConfig

def run_simple_example():
    """Run a simple backtest with default configuration"""
    print("=== Running Simple Example ===")
    
    # Create a simple configuration
    config = ExperimentConfig(
        name="Simple Pairs Trading Example",
        symbols=["AAPL", "MSFT"],
        start_date="2023-01-01",
        end_date="2023-12-31",
        strategy_class="PairsTradingStrategy",
        initial_capital=100000.0,
        output_dir="results/simple_example"
    )
    
    # Run the experiment
    runner = ExperimentRunner()
    result = runner.run_experiment(config)
    
    # Display results
    print(f"\nResults for {config.name}:")
    print(f"Total Return: {result.strategy_metrics.get('total_return', 0):.2%}")
    print(f"Annualized Return: {result.strategy_metrics.get('annualized_return', 0):.2%}")
    print(f"Sharpe Ratio: {result.strategy_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {result.strategy_metrics.get('max_drawdown', 0):.2%}")
    print(f"Total Trades: {len(result.trades)}")
    print(f"Win Rate: {result.strategy_metrics.get('win_rate', 0):.2%}")
    
    return result

def run_from_config_file():
    """Run a backtest from a configuration file"""
    print("\n=== Running from Config File ===")
    
    config_file = "config/strategies/pairs_trading.yaml"
    
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found. Skipping this example.")
        return None
    
    # Run the experiment from config file
    runner = ExperimentRunner()
    result = runner.run_experiment_from_file(config_file)
    
    # Display results
    print(f"\nResults for {result.config.name}:")
    print(f"Total Return: {result.strategy_metrics.get('total_return', 0):.2%}")
    print(f"Annualized Return: {result.strategy_metrics.get('annualized_return', 0):.2%}")
    print(f"Sharpe Ratio: {result.strategy_metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {result.strategy_metrics.get('max_drawdown', 0):.2%}")
    print(f"Total Trades: {len(result.trades)}")
    print(f"Win Rate: {result.strategy_metrics.get('win_rate', 0):.2%}")
    
    return result

def compare_with_benchmark(result):
    """Compare strategy performance with benchmark"""
    if result.benchmark_metrics:
        print(f"\n=== Benchmark Comparison ===")
        print(f"Strategy Alpha: {result.strategy_metrics.get('alpha', 0):.2%}")
        print(f"Strategy Beta: {result.strategy_metrics.get('beta', 0):.2f}")
        print(f"Information Ratio: {result.strategy_metrics.get('information_ratio', 0):.2f}")
        print(f"Benchmark Return: {result.benchmark_metrics.get('total_return', 0):.2%}")
        print(f"Benchmark Sharpe: {result.benchmark_metrics.get('sharpe_ratio', 0):.2f}")

def main():
    """Main function to run examples"""
    print("StatArb Backtesting Framework - Example Runner")
    print("=" * 50)
    
    try:
        # Run simple example
        result1 = run_simple_example()
        
        # Run from config file
        result2 = run_from_config_file()
        
        # Compare with benchmark
        if result1:
            compare_with_benchmark(result1)
        
        print(f"\n=== Summary ===")
        print("Examples completed successfully!")
        print("Check the 'results/' directory for detailed outputs.")
        print("Generated files include:")
        print("- Configuration files (JSON)")
        print("- Results summary (JSON)")
        print("- Trade history (CSV)")
        print("- Signal history (CSV)")
        print("- Performance plots (PNG)")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure you have:")
        print("1. Installed all required dependencies")
        print("2. Set up the core system properly")
        print("3. Have access to market data")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 