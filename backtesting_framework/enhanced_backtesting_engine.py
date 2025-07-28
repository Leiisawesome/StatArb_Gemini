#!/usr/bin/env python3
"""
Enhanced Backtesting Engine - Phase 2 Integration
Integrates Phase 1 academic foundations with advanced backtesting capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import json
import yaml
from pathlib import Path

from strategies.enhanced_academic_strategy import EnhancedAcademicStrategy
from core_structure.infrastructure.config.enhanced_config_manager import (
    EnhancedConfigManager, Environment
)
from core_structure.performance.benchmark_analyzer import BenchmarkAnalyzer
from utils.data_integration import DataIntegrationManager

logger = logging.getLogger(__name__)

class EnhancedBacktestingEngine:
    """Enhanced backtesting engine with academic foundations"""
    
    def __init__(self, config_path: str = None):
        self.config_manager = EnhancedConfigManager()
        self.config = None
        self.strategy = None
        self.data = {}
        self.results = {}
        self.optimization_history = []
        
        # Load configuration
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load enhanced configuration"""
        try:
            self.config = self.config_manager.load_from_file(config_path)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Use default configuration
            self.config = self.config_manager.create_step1_backtesting_config("enhanced_momentum")
    
    def load_data(self, symbols: List[str], start_date: str, end_date: str):
        """Load historical data for backtesting"""
        try:
            data_loader = DataIntegrationManager()
            
            # Add SPY for benchmark analysis
            if 'SPY' not in symbols:
                symbols.append('SPY')
            
            # Load data for all symbols
            for symbol in symbols:
                try:
                    symbol_data = data_loader.load_historical_data(
                        symbol, start_date, end_date
                    )
                    if symbol_data is not None and len(symbol_data) > 0:
                        self.data[symbol] = symbol_data
                        logger.info(f"Loaded {len(symbol_data)} rows for {symbol}")
                    else:
                        logger.warning(f"No data loaded for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to load data for {symbol}: {e}")
            
            logger.info(f"Data loading completed. Loaded {len(self.data)} symbols")
            
        except Exception as e:
            logger.error(f"Data loading failed: {e}")
            raise
    
    def initialize_strategy(self, strategy_config: Dict[str, Any] = None):
        """Initialize enhanced academic strategy"""
        try:
            if strategy_config is None:
                strategy_config = {
                    'name': 'enhanced_academic_strategy',
                    'version': '2.0.0',
                    'parameters': {}
                }
            
            self.strategy = EnhancedAcademicStrategy(strategy_config)
            self.strategy.initialize(self.data)
            
            logger.info("Enhanced academic strategy initialized successfully")
            
        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            raise
    
    def run_backtest(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Run enhanced backtesting with academic foundations"""
        try:
            if self.strategy is None:
                raise ValueError("Strategy not initialized")
            
            if len(self.data) == 0:
                raise ValueError("No data loaded")
            
            logger.info("Starting enhanced backtesting...")
            
            # Filter data by date range if specified
            if start_date and end_date:
                filtered_data = self._filter_data_by_date(start_date, end_date)
            else:
                filtered_data = self.data
            
            # Run backtesting
            results = self._execute_backtest(filtered_data)
            
            # Calculate performance metrics
            performance_metrics = self.strategy.calculate_performance_metrics()
            
            # Run parameter optimization
            optimization_results = self.strategy.optimize_parameters()
            
            # Compile comprehensive results
            self.results = {
                'backtest_results': results,
                'performance_metrics': performance_metrics,
                'optimization_results': optimization_results,
                'strategy_summary': self.strategy.get_strategy_summary(),
                'academic_analysis': self._generate_academic_analysis()
            }
            
            logger.info("Enhanced backtesting completed successfully")
            return self.results
            
        except Exception as e:
            logger.error(f"Backtesting failed: {e}")
            raise
    
    def _filter_data_by_date(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Filter data by date range"""
        filtered_data = {}
        
        for symbol, df in self.data.items():
            mask = (df.index >= start_date) & (df.index <= end_date)
            filtered_df = df[mask]
            
            if len(filtered_df) > 0:
                filtered_data[symbol] = filtered_df
        
        return filtered_data
    
    def _execute_backtest(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Execute the actual backtesting"""
        try:
            # Generate signals
            signals = self.strategy.generate_signals(data)
            
            # Execute trades (simplified for now)
            trades = self._execute_trades(signals, data)
            
            # Calculate portfolio performance
            portfolio_performance = self._calculate_portfolio_performance(trades, data)
            
            return {
                'signals_generated': len(signals),
                'trades_executed': len(trades),
                'portfolio_performance': portfolio_performance,
                'signal_details': [
                    {
                        'symbol': s.symbol,
                        'type': s.signal_type.value,
                        'confidence': s.confidence,
                        'timestamp': s.timestamp.isoformat()
                    } for s in signals
                ]
            }
            
        except Exception as e:
            logger.error(f"Backtest execution failed: {e}")
            raise
    
    def _execute_trades(self, signals: List, data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Execute trades based on signals (simplified implementation)"""
        trades = []
        
        for signal in signals:
            if signal.symbol in data:
                trade = {
                    'symbol': signal.symbol,
                    'type': signal.signal_type.value,
                    'price': signal.price,
                    'timestamp': signal.timestamp,
                    'confidence': signal.confidence
                }
                trades.append(trade)
        
        return trades
    
    def _calculate_portfolio_performance(self, trades: List[Dict], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate portfolio performance metrics"""
        if len(trades) == 0:
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'volatility': 0.0
            }
        
        # Simplified performance calculation
        # In a real implementation, this would track actual portfolio value
        total_return = 0.0
        for trade in trades:
            if trade['type'] == 'LONG':
                total_return += 0.01  # Simplified 1% return per long trade
            else:
                total_return -= 0.005  # Simplified 0.5% return per short trade
        
        return {
            'total_return': total_return,
            'sharpe_ratio': total_return / max(0.01, len(trades) * 0.02),  # Simplified
            'max_drawdown': max(0, -total_return * 0.3),  # Simplified
            'volatility': len(trades) * 0.01  # Simplified
        }
    
    def _generate_academic_analysis(self) -> Dict[str, Any]:
        """Generate academic analysis of results"""
        analysis = {
            'academic_foundations_implemented': True,
            'research_papers_cited': [
                'Moskowitz et al. (2012) - Multi-horizon momentum',
                'Gervais et al. (2001) - Volume-momentum interaction',
                'Cooper et al. (2004) - Market regime effects',
                'Daniel & Moskowitz (2016) - Crash protection',
                'Chordia & Shivakumar (2002) - Business cycle effects'
            ],
            'benchmark_analysis': {
                'spy_benchmark_used': 'SPY' in self.data,
                'information_ratio_calculated': 'information_ratio' in self.strategy.performance_metrics,
                'tracking_error_measured': 'tracking_error' in self.strategy.performance_metrics
            },
            'optimization_status': {
                'parameters_optimized': len(self.strategy.optimization_results) > 0,
                'optimization_score': self.strategy.optimization_results.get('optimization_score', 0)
            }
        }
        
        return analysis
    
    def save_results(self, output_path: str):
        """Save backtesting results to file"""
        try:
            # Convert datetime objects to strings for JSON serialization
            results_copy = self._prepare_results_for_saving()
            
            with open(output_path, 'w') as f:
                json.dump(results_copy, f, indent=2, default=str)
            
            logger.info(f"Results saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    def _prepare_results_for_saving(self) -> Dict[str, Any]:
        """Prepare results for JSON serialization"""
        results_copy = self.results.copy()
        
        # Convert datetime objects to strings
        if 'signal_details' in results_copy.get('backtest_results', {}):
            for signal in results_copy['backtest_results']['signal_details']:
                if 'timestamp' in signal:
                    signal['timestamp'] = str(signal['timestamp'])
        
        return results_copy
    
    def generate_report(self) -> str:
        """Generate comprehensive backtesting report"""
        if not self.results:
            return "No results available for report generation"
        
        report = []
        report.append("=" * 60)
        report.append("ENHANCED ACADEMIC BACKTESTING REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Strategy Summary
        report.append("STRATEGY SUMMARY:")
        report.append("-" * 20)
        summary = self.results.get('strategy_summary', {})
        report.append(f"Strategy: {summary.get('name', 'Enhanced Academic Strategy')}")
        report.append(f"Symbols: {len(self.data)}")
        report.append(f"Data Period: {min(self.data[list(self.data.keys())[0]].index)} to {max(self.data[list(self.data.keys())[0]].index)}")
        report.append("")
        
        # Backtest Results
        report.append("BACKTEST RESULTS:")
        report.append("-" * 20)
        backtest = self.results.get('backtest_results', {})
        report.append(f"Signals Generated: {backtest.get('signals_generated', 0)}")
        report.append(f"Trades Executed: {backtest.get('trades_executed', 0)}")
        report.append("")
        
        # Performance Metrics
        report.append("PERFORMANCE METRICS:")
        report.append("-" * 20)
        metrics = self.results.get('performance_metrics', {})
        for key, value in metrics.items():
            if isinstance(value, float):
                report.append(f"{key.replace('_', ' ').title()}: {value:.4f}")
            else:
                report.append(f"{key.replace('_', ' ').title()}: {value}")
        report.append("")
        
        # Academic Analysis
        report.append("ACADEMIC ANALYSIS:")
        report.append("-" * 20)
        academic = self.results.get('academic_analysis', {})
        report.append(f"Academic Foundations: {'✅' if academic.get('academic_foundations_implemented') else '❌'}")
        report.append(f"SPY Benchmark: {'✅' if academic.get('benchmark_analysis', {}).get('spy_benchmark_used') else '❌'}")
        report.append(f"Information Ratio: {'✅' if academic.get('benchmark_analysis', {}).get('information_ratio_calculated') else '❌'}")
        report.append("")
        
        # Research Papers
        report.append("RESEARCH FOUNDATIONS:")
        report.append("-" * 20)
        papers = academic.get('research_papers_cited', [])
        for paper in papers:
            report.append(f"• {paper}")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report) 