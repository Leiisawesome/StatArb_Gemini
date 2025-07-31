#!/usr/bin/env python3
"""
Test Case 1: Technical Momentum Strategy with Historical Data
Tests MultiFactorEnsembleStrategy using EnhancedBacktestingEngine with ClickHouse data
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
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class TechnicalMomentumHistoricalTest:
    """Test technical momentum strategy with historical data"""
    
    def __init__(self):
        self.config_manager = EnhancedConfigManager()
        self.engine = EnhancedBacktestingEngine()
        self.results = {}
        
    def run_test(self):
        """Run comprehensive historical backtesting test"""
        
        logger.info("Starting Technical Momentum Historical Test")
        
        # Step 1: Create configuration
        logger.info("Step 1: Creating configuration...")
        config = self.config_manager.create_step1_backtesting_config(
            strategy_name="technical_momentum",
            training_start="2023-01-01",
            training_end="2024-12-31",
            validation_start="2025-01-01",
            validation_end="2025-06-30"
        )
        
        # Set the configuration in the engine
        self.engine.config = config
        
        # Step 2: Load historical data
        logger.info("Step 2: Loading historical data...")
        # Use symbols from the strategy configuration instead of hardcoded values
        symbols = config.strategy.symbols
        logger.info(f"Loading data for {len(symbols)} symbols from configuration: {symbols[:10]}...")  # Show first 10 symbols
        
        # For testing purposes, if we need to limit symbols due to data availability,
        # we can use a subset but should document this clearly
        if len(symbols) > 20:  # If we have the full 50+1 symbol list
            # Use first 20 symbols for testing (can be expanded later)
            test_symbols = symbols[:20]
            logger.info(f"Using subset of {len(test_symbols)} symbols for testing: {test_symbols}")
            symbols = test_symbols
        
        self.engine.load_data(symbols, "2023-01-01", "2025-06-30")
        
        # Step 3: Initialize strategy
        logger.info("Step 3: Initializing strategy...")
        # Pass the complete configuration to the engine
        strategy_config = {
            'name': 'technical_momentum',
            'version': '2.0.0',
            'parameters': config.strategy.parameters
        }
        self.engine.initialize_strategy(strategy_config)
        
        # Step 4: Run backtest
        logger.info("Step 4: Running backtest...")
        results = self.engine.run_backtest()
        
        # Step 5: Save results
        logger.info("Step 5: Saving results...")
        self.save_results(results, "technical_momentum_historical")
        
        # Step 6: Generate analysis
        logger.info("Step 6: Generating analysis...")
        analysis = self.generate_analysis(results)
        
        logger.info("Historical test completed successfully!")
        return results, analysis
    
    def save_results(self, results, test_name):
        """Save test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/{test_name}_{timestamp}.json"
        
        # Ensure results directory exists
        os.makedirs("results", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")
    
    def generate_analysis(self, results):
        """Generate comprehensive analysis of results"""
        analysis = {
            'test_summary': {
                'test_name': 'Technical Momentum Historical Test',
                'test_date': datetime.now().isoformat(),
                'data_period': '2023-01-01 to 2025-06-30',
                'training_period': '2023-01-01 to 2024-12-31',
                'trading_period': '2025-01-01 to 2025-06-30'
            },
            'performance_metrics': results.get('performance_metrics', {}),
            'factor_analysis': self._analyze_factors(results),
            'technical_indicators_analysis': self._analyze_technical_indicators(results),
            'risk_metrics': self._analyze_risk_metrics(results),
            'recommendations': self._generate_recommendations(results)
        }
        
        # Save analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_filename = f"results/technical_momentum_historical_analysis_{timestamp}.json"
        
        with open(analysis_filename, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Analysis saved to {analysis_filename}")
        return analysis
    
    def _analyze_factors(self, results):
        """Analyze factor performance"""
        factor_analysis = {}
        
        # Extract factor signals if available
        if hasattr(self.engine.strategy, 'factor_signals'):
            for symbol, signals in self.engine.strategy.factor_signals.items():
                factor_analysis[symbol] = {
                    'technical_signal': signals.get('technical', 0),
                    'momentum_signal': signals.get('momentum', 0),
                    'mean_reversion_signal': signals.get('mean_reversion', 0),
                    'volatility_signal': signals.get('volatility', 0)
                }
        
        return factor_analysis
    
    def _analyze_technical_indicators(self, results):
        """Analyze technical indicators performance"""
        technical_analysis = {
            'rsi_performance': 'To be calculated from actual signals',
            'macd_performance': 'To be calculated from actual signals',
            'bollinger_bands_performance': 'To be calculated from actual signals',
            'signal_quality': 'To be assessed from backtest results'
        }
        
        return technical_analysis
    
    def _analyze_risk_metrics(self, results):
        """Analyze risk metrics"""
        risk_metrics = {
            'max_drawdown': results.get('performance_metrics', {}).get('max_drawdown', 0),
            'volatility': results.get('performance_metrics', {}).get('volatility', 0),
            'var_95': results.get('performance_metrics', {}).get('var_95', 0),
            'sharpe_ratio': results.get('performance_metrics', {}).get('sharpe_ratio', 0),
            'sortino_ratio': results.get('performance_metrics', {}).get('sortino_ratio', 0)
        }
        
        return risk_metrics
    
    def _generate_recommendations(self, results):
        """Generate recommendations based on results"""
        recommendations = []
        
        # Analyze performance metrics
        performance = results.get('performance_metrics', {})
        sharpe_ratio = performance.get('sharpe_ratio', 0)
        max_drawdown = performance.get('max_drawdown', 0)
        
        if sharpe_ratio > 1.5:
            recommendations.append("✅ Excellent Sharpe ratio achieved - strategy performing well")
        elif sharpe_ratio > 1.0:
            recommendations.append("✅ Good Sharpe ratio - consider parameter optimization")
        else:
            recommendations.append("⚠️ Low Sharpe ratio - review factor weights and thresholds")
        
        if max_drawdown < 0.10:
            recommendations.append("✅ Low maximum drawdown - good risk management")
        elif max_drawdown < 0.15:
            recommendations.append("⚠️ Moderate drawdown - consider tighter risk controls")
        else:
            recommendations.append("❌ High drawdown - implement stricter risk management")
        
        recommendations.append("📊 Consider expanding to full 50-symbol universe for better diversification")
        recommendations.append("🔄 Implement dynamic factor weighting based on market conditions")
        recommendations.append("📈 Add regime detection for adaptive strategy parameters")
        
        return recommendations

def main():
    """Main execution function"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    test = TechnicalMomentumHistoricalTest()
    results, analysis = test.run_test()
    
    # Print summary
    print("\n" + "="*80)
    print("TECHNICAL MOMENTUM HISTORICAL TEST RESULTS")
    print("="*80)
    
    performance = results.get('performance_metrics', {})
    print(f"Sharpe Ratio: {performance.get('sharpe_ratio', 'N/A'):.3f}")
    print(f"Max Drawdown: {performance.get('max_drawdown', 'N/A'):.3f}")
    print(f"Total Return: {performance.get('total_return', 'N/A'):.3f}")
    print(f"Volatility: {performance.get('volatility', 'N/A'):.3f}")
    
    print("\nRECOMMENDATIONS:")
    for rec in analysis.get('recommendations', []):
        print(f"  {rec}")
    
    print("\nTest completed successfully!")
    print("Check results/ directory for detailed reports.")

if __name__ == "__main__":
    main() 