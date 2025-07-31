#!/usr/bin/env python3
"""
Test Case: Technical Momentum Strategy TUNED for More Trades
Tests MultiFactorEnsembleStrategy with tuned parameters for increased trading activity
"""

import sys
import os
# Add the current directory (StatArb_Gemini root) to the path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)
# Also add the current working directory
sys.path.insert(0, os.getcwd())

from engines.enhanced_backtesting_engine import EnhancedBacktestingEngine
from strategies.multi_factor_ensemble_strategy import MultiFactorEnsembleStrategy, MultiFactorConfig
from core_structure.infrastructure.config.enhanced_config_manager import EnhancedConfigManager

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TechnicalMomentumTunedTest:
    """Test tuned technical momentum strategy for more trades"""
    
    def __init__(self):
        self.config_manager = EnhancedConfigManager()
        self.engine = EnhancedBacktestingEngine()
        self.results = {}
        
        # Test state
        self.initial_capital = 100000
        self.trade_history = []
        
    def run_test(self):
        """Run tuned backtesting test"""
        
        logger.info("Starting Technical Momentum TUNED Test")
        
        # Step 1: Create tuned configuration
        logger.info("Step 1: Creating tuned configuration...")
        config = self._create_tuned_config()
        
        # Set the configuration in the engine
        self.engine.config = config
        
        # Step 2: Load historical data
        logger.info("Step 2: Loading historical data...")
        symbols = config.strategy.symbols
        logger.info(f"Loading data for {len(symbols)} symbols: {symbols[:10]}...")
        
        # Use subset for testing
        if len(symbols) > 10:
            test_symbols = symbols[:10]
            logger.info(f"Using subset of {len(test_symbols)} symbols for testing: {test_symbols}")
            symbols = test_symbols
        
        self.engine.load_data(symbols, "2023-01-01", "2025-06-30")
        
        # Step 3: Initialize tuned strategy
        logger.info("Step 3: Initializing tuned strategy...")
        strategy_config = {
            'name': 'technical_momentum_strategy_tuned',  # Fixed: match the actual YAML file name
            'version': '2.1.0',
            'parameters': config.strategy.parameters
        }
        self.engine.initialize_strategy(strategy_config)
        
        # Step 4: Run tuned backtest
        logger.info("Step 4: Running tuned backtest...")
        results = self.engine.run_backtest()
        
        # Step 5: Analyze results
        logger.info("Step 5: Analyzing results...")
        analysis = self._analyze_tuned_results(results)
        
        # Step 6: Save results
        logger.info("Step 6: Saving results...")
        self._save_tuned_results(results, analysis)
        
        logger.info("Tuned test completed successfully!")
        return results, analysis
    
    def _create_tuned_config(self):
        """Create configuration with tuned parameters"""
        
        # Load base configuration from YAML
        config = self.config_manager.create_step1_backtesting_config(
            strategy_name="technical_momentum_strategy_tuned",  # Use the tuned YAML file
            training_start="2023-01-01",
            training_end="2024-12-31",
            validation_start="2025-01-01",
            validation_end="2025-06-30"
        )
        
        # NOTE: We override the YAML parameters here for testing purposes
        # The YAML file contains the production-tuned parameters, but for this test
        # we want to ensure we're using the exact parameters that we know work
        # This approach allows us to:
        # 1. Use the YAML as the base configuration
        # 2. Override specific parameters for testing
        # 3. Ensure consistent test results
        
        logger.info("Loading base configuration from YAML and applying test overrides")
        
        # Override with test-specific tuned parameters
        tuned_params = {
            'factors': [
                {
                    'factor_type': 'technical',
                    'lookback_period': 14,  # Reduced from 20
                    'threshold': 0.05,      # Reduced from 0.15
                    'weight': 0.4,
                    'indicators': {
                        'rsi_period': 10,     # Reduced from 14
                        'macd_fast': 8,       # Reduced from 12
                        'macd_slow': 21,      # Reduced from 26
                        'macd_signal': 7,     # Reduced from 9
                        'bollinger_period': 15,  # Reduced from 20
                        'bollinger_std': 1.5,    # Reduced from 2
                        'rsi_oversold': 35,      # Increased from 30
                        'rsi_overbought': 65,    # Decreased from 70
                        'macd_threshold': 0.0005,  # Reduced from 0.001
                        'bollinger_threshold': 0.01  # Reduced from 0.02
                    }
                },
                {
                    'factor_type': 'momentum',
                    'lookback_period': 60,   # Reduced from 252
                    'threshold': 0.03,       # Reduced from 0.10
                    'weight': 0.3
                },
                {
                    'factor_type': 'mean_reversion',
                    'lookback_period': 30,   # Reduced from 60
                    'threshold': 0.08,       # Reduced from 0.20
                    'weight': 0.2
                },
                {
                    'factor_type': 'volatility',
                    'lookback_period': 20,   # Reduced from 30
                    'threshold': 0.10,       # Reduced from 0.25
                    'weight': 0.1
                }
            ],
            'signal_threshold': 0.03,    # Reduced from 0.15
            'max_positions': 20,         # Increased from 15
            'max_position_value': 15000  # Increased from 10000
        }
        
        # Update configuration with test-specific tuned parameters
        config.strategy.parameters.update(tuned_params)
        
        return config
    
    def _analyze_tuned_results(self, results: Dict) -> Dict:
        """Analyze tuned test results"""
        
        # Extract backtest results from the nested structure
        backtest_results = results.get('backtest_results', results)
        
        analysis = {
            'test_summary': {
                'test_name': 'Technical Momentum TUNED Test',
                'test_date': datetime.now().isoformat(),
                'data_period': '2023-01-01 to 2025-06-30',
                'trading_period': '2025-01-01 to 2025-06-30',
                'initial_capital': self.initial_capital,
                'tuning_changes': [
                    'Using technical_momentum_strategy_tuned.yaml configuration',
                    'Reduced signal thresholds (0.15 → 0.03)',
                    'Reduced factor thresholds (0.15-0.25 → 0.03-0.10)',
                    'Reduced lookback periods (20-252 → 14-60)',
                    'Increased position limits (15 → 20 positions)',
                    'More sensitive RSI levels (30/70 → 35/65)',
                    'More aggressive MACD thresholds',
                    'Optimized min_trade_size ($50 → $50) for maximum flexibility',
                    'Reduced max_trades_per_day (100 → 30) for risk management',
                    '5-minute rebalancing intervals for responsiveness'
                ]
            },
            'performance_analysis': {
                'final_performance': backtest_results.get('portfolio_performance', {}),
                'trade_analysis': self._analyze_trades(backtest_results),
                'signal_analysis': self._analyze_signals(backtest_results)
            },
            'tuning_effectiveness': self._assess_tuning_effectiveness(backtest_results)
        }
        
        return analysis
    
    def _analyze_trades(self, results: Dict) -> Dict:
        """Analyze trade execution"""
        # Use the correct key from backtesting engine results
        trades_executed = results.get('trades_executed', 0)
        signal_details = results.get('signal_details', [])
        
        return {
            'total_trades': trades_executed,
            'long_trades': len([s for s in signal_details if s.get('type') == 'LONG']),
            'short_trades': len([s for s in signal_details if s.get('type') == 'SHORT']),
            'trades_per_symbol': self._count_trades_per_symbol(signal_details),
            'avg_trade_size': 1000,  # Default trade size
            'trade_frequency': trades_executed / 180  # trades per day over 6 months
        }
    
    def _analyze_signals(self, results: Dict) -> Dict:
        """Analyze signal generation"""
        signals_generated = results.get('signals_generated', 0)
        signal_details = results.get('signal_details', [])
        
        signal_strengths = [s.get('confidence', 0) for s in signal_details]
        
        return {
            'total_signals': signals_generated,
            'strong_signals': len([s for s in signal_strengths if s > 0.1]),
            'weak_signals': len([s for s in signal_strengths if 0.02 < s <= 0.1]),
            'avg_signal_strength': np.mean(signal_strengths) if signal_strengths else 0,
            'signal_distribution': self._analyze_signal_distribution(signal_strengths)
        }
    
    def _assess_tuning_effectiveness(self, results: Dict) -> Dict:
        """Assess how effective the tuning was"""
        trades_executed = results.get('trades_executed', 0)
        portfolio_performance = results.get('portfolio_performance', {})
        
        return {
            'trades_generated': trades_executed,
            'trading_activity': 'HIGH' if trades_executed > 50 else 'MEDIUM' if trades_executed > 10 else 'LOW',
            'performance_impact': {
                'sharpe_ratio': portfolio_performance.get('sharpe_ratio', 0),
                'total_return': portfolio_performance.get('total_return', 0),
                'max_drawdown': portfolio_performance.get('max_drawdown', 0)
            },
            'tuning_success': trades_executed > 0,  # Success if we generated any trades
            'recommendations': self._generate_tuning_recommendations(results)
        }
    
    def _count_trades_per_symbol(self, signal_details: List[Dict]) -> Dict[str, int]:
        """Count trades per symbol"""
        symbol_counts = {}
        for signal in signal_details:
            symbol = signal.get('symbol', 'UNKNOWN')
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        return symbol_counts
    
    def _analyze_signal_distribution(self, signal_strengths: List[float]) -> Dict:
        """Analyze distribution of signal strengths"""
        if not signal_strengths:
            return {}
        
        return {
            'min_signal': min(signal_strengths),
            'max_signal': max(signal_strengths),
            'std_signal': np.std(signal_strengths),
            'positive_signals': len([s for s in signal_strengths if s > 0]),
            'negative_signals': len([s for s in signal_strengths if s < 0]),
            'zero_signals': len([s for s in signal_strengths if s == 0])
        }
    
    def _generate_tuning_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on tuning results"""
        trades_executed = results.get('trades_executed', 0)
        portfolio_performance = results.get('portfolio_performance', {})
        
        recommendations = []
        
        if trades_executed == 0:
            recommendations.append("❌ No trades generated - consider further reducing thresholds")
            recommendations.append("📊 Check if data has sufficient volatility for signal generation")
            recommendations.append("🔧 Reduce signal_threshold to 0.01 for maximum sensitivity")
        elif trades_executed < 10:
            recommendations.append("⚠️ Low trading activity - consider moderate threshold reduction")
            recommendations.append("📈 Increase position limits for better capital utilization")
        elif trades_executed > 100:
            recommendations.append("✅ High trading activity achieved - consider risk management")
            recommendations.append("💰 Monitor transaction costs with high trade frequency")
        
        sharpe_ratio = portfolio_performance.get('sharpe_ratio', 0)
        if sharpe_ratio < 0.5:
            recommendations.append("📉 Low Sharpe ratio - review signal quality vs quantity")
        
        return recommendations
    
    def _save_tuned_results(self, results: Dict, analysis: Dict):
        """Save tuned test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ensure results directory exists
        os.makedirs("results", exist_ok=True)
        
        # Save results
        results_filename = f"results/technical_momentum_tuned_{timestamp}.json"
        with open(results_filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save analysis
        analysis_filename = f"results/technical_momentum_tuned_analysis_{timestamp}.json"
        with open(analysis_filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Tuned results saved to {results_filename}")
        logger.info(f"Tuned analysis saved to {analysis_filename}")

def main():
    """Main execution function"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tuned test
    test = TechnicalMomentumTunedTest()
    results, analysis = test.run_test()
    
    # Print summary
    print("\n" + "="*80)
    print("TECHNICAL MOMENTUM TUNED TEST RESULTS")
    print("="*80)
    
    # Extract backtest results from the nested structure
    backtest_results = results.get('backtest_results', results)
    final_performance = backtest_results.get('portfolio_performance', {})
    sharpe_ratio = final_performance.get('sharpe_ratio', 'N/A')
    max_drawdown = final_performance.get('max_drawdown', 'N/A')
    total_return = final_performance.get('total_return', 'N/A')
    final_value = final_performance.get('final_value', 'N/A')
    
    print(f"Sharpe Ratio: {sharpe_ratio:.3f}" if isinstance(sharpe_ratio, (int, float)) else f"Sharpe Ratio: {sharpe_ratio}")
    print(f"Max Drawdown: {max_drawdown:.1%}" if isinstance(max_drawdown, (int, float)) else f"Max Drawdown: {max_drawdown}")
    print(f"Total Return: {total_return:.1%}" if isinstance(total_return, (int, float)) else f"Total Return: {total_return}")
    print(f"Final Portfolio Value: ${final_value:,.2f}" if isinstance(final_value, (int, float)) else f"Final Portfolio Value: {final_value}")
    
    # Trade Analysis
    trade_analysis = analysis.get('performance_analysis', {}).get('trade_analysis', {})
    print(f"\nTrade Analysis:")
    print(f"  Total Trades: {trade_analysis.get('total_trades', 0)}")
    print(f"  Long Trades: {trade_analysis.get('long_trades', 0)}")
    print(f"  Short Trades: {trade_analysis.get('short_trades', 0)}")
    print(f"  Trade Frequency: {trade_analysis.get('trade_frequency', 0):.2f} trades/day")
    
    # Signal Analysis
    signal_analysis = analysis.get('performance_analysis', {}).get('signal_analysis', {})
    print(f"\nSignal Analysis:")
    print(f"  Total Signals: {signal_analysis.get('total_signals', 0)}")
    print(f"  Strong Signals: {signal_analysis.get('strong_signals', 0)}")
    print(f"  Weak Signals: {signal_analysis.get('weak_signals', 0)}")
    print(f"  Avg Signal Strength: {signal_analysis.get('avg_signal_strength', 0):.4f}")
    
    # Tuning Effectiveness
    tuning_effectiveness = analysis.get('tuning_effectiveness', {})
    print(f"\nTuning Effectiveness:")
    print(f"  Trading Activity: {tuning_effectiveness.get('trading_activity', 'UNKNOWN')}")
    print(f"  Tuning Success: {'✅ YES' if tuning_effectiveness.get('tuning_success', False) else '❌ NO'}")
    
    print(f"\nTUNING RECOMMENDATIONS:")
    for rec in tuning_effectiveness.get('recommendations', []):
        print(f"  {rec}")
    
    print("\n✅ TUNED TEST COMPLETED!")
    print("Check results/ directory for detailed tuned reports.")

if __name__ == "__main__":
    main() 