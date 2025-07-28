#!/usr/bin/env python3
"""
Enhanced Academic Strategy - Phase 2 Integration
Integrates Phase 1 academic foundations with backtesting framework
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

from strategies.base_strategy import BaseStrategy, SignalType, TradingSignal, Position, StrategyConfig
from core_structure.signal_generation.enhanced_signal_generator import (
    EnhancedSignalGenerator, AcademicSignalConfig
)
from core_structure.performance.benchmark_analyzer import (
    BenchmarkAnalyzer, BenchmarkConfig
)
from core_structure.infrastructure.config.enhanced_config_manager import (
    EnhancedConfigManager, Environment
)

logger = logging.getLogger(__name__)

class EnhancedAcademicStrategy(BaseStrategy):
    """Enhanced academic strategy with Phase 1 foundations"""
    
    def __init__(self, config: Dict[str, any]):
        # Convert dict config to StrategyConfig
        if isinstance(config, dict):
            strategy_config = StrategyConfig(
                symbols=config.get('symbols', ['SPY', 'AAPL', 'MSFT', 'GOOGL']),
                name=config.get('name', 'enhanced_academic_strategy'),
                version=config.get('version', '2.0.0'),
                initial_capital=config.get('initial_capital', 100000.0),
                position_size=config.get('position_size', 0.1),
                max_positions=config.get('max_positions', 10)
            )
        else:
            strategy_config = config
        
        super().__init__(strategy_config)
        
        # Initialize Phase 1 components
        self.academic_signal_config = AcademicSignalConfig()
        self.signal_generator = EnhancedSignalGenerator(self.academic_signal_config)
        
        # Initialize benchmark analyzer
        self.benchmark_config = BenchmarkConfig()
        self.benchmark_analyzer = BenchmarkAnalyzer(self.benchmark_config)
        
        # Strategy state
        self.spy_data = None
        self.performance_metrics = {}
        self.optimization_results = {}
        
        # Academic parameters (will be optimized)
        self.momentum_weights = {
            'short_term': 0.2,
            'medium_term': 0.3,
            'long_term': 0.3,
            'intermediate': 0.2
        }
        
        self.risk_limits = {
            'max_position_size': 0.1,
            'max_positions': 10,
            'stop_loss': 0.05,
            'take_profit': 0.15
        }
    
    def initialize(self, data: Dict[str, pd.DataFrame]):
        """Initialize strategy with data"""
        # Set data directly
        self.data = data
        
        # Extract SPY data for benchmark analysis
        if 'SPY' in data:
            self.spy_data = data['SPY']
            logger.info("SPY benchmark data loaded for analysis")
        else:
            logger.warning("SPY data not found - benchmark analysis disabled")
        
        # Validate data quality
        self._validate_data_quality(data)
        
        logger.info(f"Enhanced Academic Strategy initialized with {len(data)} symbols")
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """Generate academic momentum signals"""
        signals = []
        
        try:
            # Generate academic momentum signals using Phase 1 components
            academic_signals = self.signal_generator.generate_academic_momentum_signals(
                data, self.spy_data
            )
            
            # Convert academic signals to trading signals
            for symbol, signal_strength in academic_signals.items():
                if symbol not in data:
                    continue
                
                # Apply risk limits and position sizing
                position_size = self._calculate_position_size(signal_strength, symbol)
                
                if abs(position_size) > 0.01:  # Minimum position threshold
                    signal_type = SignalType.LONG if position_size > 0 else SignalType.SHORT
                    
                    signal = TradingSignal(
                        timestamp=datetime.now(),
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=abs(signal_strength),
                        confidence=abs(signal_strength),
                        price=data[symbol]['close'].iloc[-1]
                    )
                    
                    signals.append(signal)
                    
                    logger.debug(f"Generated {signal_type.value} signal for {symbol}: "
                               f"strength={signal_strength:.4f}, size={position_size:.4f}")
            
            logger.info(f"Generated {len(signals)} academic momentum signals")
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return []
        
        return signals
    
    def _calculate_position_size(self, signal_strength: float, symbol: str) -> float:
        """Calculate position size based on signal strength and risk limits"""
        
        # Base position size from signal strength
        base_size = signal_strength * self.risk_limits['max_position_size']
        
        # Apply volatility adjustment
        if symbol in self.data:
            volatility = self.data[symbol]['close'].pct_change().std()
            volatility_adjustment = 1.0 / (1.0 + volatility * 10)  # Reduce size for high volatility
            base_size *= volatility_adjustment
        
        # Apply regime adjustment
        if self.spy_data is not None:
            regime_adjustment = self._get_regime_adjustment()
            base_size *= regime_adjustment
        
        # Apply risk limits
        max_size = self.risk_limits['max_position_size']
        position_size = np.clip(base_size, -max_size, max_size)
        
        return position_size
    
    def _get_regime_adjustment(self) -> float:
        """Get position size adjustment based on market regime"""
        try:
            # Simple regime detection based on SPY volatility
            spy_returns = self.spy_data['close'].pct_change()
            volatility = spy_returns.rolling(20).std().iloc[-1]
            
            if volatility > 0.03:  # High volatility
                return 0.7  # Reduce position sizes
            elif volatility < 0.01:  # Low volatility
                return 1.2  # Increase position sizes
            else:
                return 1.0  # Normal regime
                
        except Exception as e:
            logger.warning(f"Regime adjustment failed: {e}")
            return 1.0
    
    def _validate_data_quality(self, data: Dict[str, pd.DataFrame]):
        """Validate data quality for academic analysis"""
        for symbol, df in data.items():
            if len(df) < 252:  # Need at least 1 year of data
                logger.warning(f"Insufficient data for {symbol}: {len(df)} rows")
                continue
            
            if df['close'].isna().sum() > len(df) * 0.05:  # More than 5% missing
                logger.warning(f"Too many missing values in {symbol}: {df['close'].isna().sum()}")
                continue
            
            if (df['close'] <= 0).any():
                logger.warning(f"Invalid prices found in {symbol}")
                continue
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics including benchmark analysis"""
        # Handle the case where returns might be a Series
        try:
            # Temporarily convert returns to list if it's a Series
            original_returns = self.returns
            if hasattr(self, 'returns') and isinstance(self.returns, pd.Series):
                self.returns = self.returns.tolist()
            
            metrics = super().get_performance_metrics()
            
            # Restore original returns
            if hasattr(self, 'returns'):
                self.returns = original_returns
                
        except Exception as e:
            logger.warning(f"Base performance metrics failed: {e}")
            metrics = {
                'total_return': 0.0,
                'annualized_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': len(getattr(self, 'trades', []))
            }
        
        # Add benchmark analysis if SPY data is available
        if self.spy_data is not None and hasattr(self, 'returns') and len(self.returns) > 0:
            try:
                # Calculate SPY returns
                spy_returns = self.spy_data['close'].pct_change().dropna()
                
                # Convert returns to Series if needed
                if isinstance(self.returns, list):
                    strategy_returns = pd.Series(self.returns)
                else:
                    strategy_returns = self.returns
                
                # Align returns series
                strategy_returns = strategy_returns.reindex(spy_returns.index).dropna()
                spy_returns = spy_returns.reindex(strategy_returns.index).dropna()
                
                if not strategy_returns.empty and not spy_returns.empty:
                    # Calculate benchmark metrics
                    benchmark_metrics = self.benchmark_analyzer.calculate_benchmark_metrics(
                        strategy_returns, spy_returns
                    )
                    
                    # Add benchmark metrics to performance
                    metrics.update({
                        'information_ratio': benchmark_metrics['information_ratio'],
                        'tracking_error': benchmark_metrics['tracking_error'],
                        'beta': benchmark_metrics['beta'],
                        'excess_return': benchmark_metrics['excess_return'],
                        'spy_sharpe_ratio': benchmark_metrics['spy_sharpe_ratio']
                    })
                    
                    logger.info("Benchmark analysis completed")
                    
            except Exception as e:
                logger.error(f"Benchmark analysis failed: {e}")
        
        self.performance_metrics = metrics
        return metrics
    
    def optimize_parameters(self) -> Dict[str, any]:
        """Optimize strategy parameters using benchmark analysis"""
        if self.spy_data is None or not hasattr(self, 'returns') or len(self.returns) == 0:
            logger.warning("Cannot optimize parameters - insufficient data")
            return {}
        
        try:
            # Calculate current performance
            current_metrics = self.calculate_performance_metrics()
            
            # Simple parameter optimization based on Information Ratio
            optimization_results = {
                'current_metrics': current_metrics,
                'optimization_score': 0.0,
                'recommended_adjustments': {}
            }
            
            # Optimize momentum weights based on performance
            if 'information_ratio' in current_metrics:
                ir = current_metrics['information_ratio']
                
                if ir < 0.5:  # Low Information Ratio
                    # Increase long-term momentum weight
                    optimization_results['recommended_adjustments'] = {
                        'momentum_weights': {
                            'short_term': 0.15,
                            'medium_term': 0.25,
                            'long_term': 0.4,
                            'intermediate': 0.2
                        }
                    }
                elif ir > 1.0:  # High Information Ratio
                    # Current weights are working well
                    optimization_results['recommended_adjustments'] = {
                        'momentum_weights': self.momentum_weights
                    }
                
                optimization_results['optimization_score'] = min(ir / 1.5, 1.0)
            
            self.optimization_results = optimization_results
            logger.info(f"Parameter optimization completed - score: {optimization_results['optimization_score']:.4f}")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return {}
    
    def get_strategy_summary(self) -> Dict[str, any]:
        """Get comprehensive strategy summary"""
        # Get base summary from parent class
        try:
            summary = super().get_strategy_summary()
        except AttributeError:
            # Fallback if parent doesn't have this method
            summary = {
                'name': getattr(self.config, 'name', 'Enhanced Academic Strategy'),
                'version': getattr(self.config, 'version', '2.0.0'),
                'initial_capital': getattr(self.config, 'initial_capital', 100000.0),
                'current_cash': getattr(self, 'cash', 100000.0),
                'total_positions': len(getattr(self, 'positions', {}))
            }
        
        # Add academic components summary
        summary.update({
            'academic_foundations': {
                'multi_horizon_momentum': True,
                'volume_weighting': True,
                'regime_detection': True,
                'crash_protection': True,
                'macro_adjustments': True
            },
            'benchmark_analysis': {
                'spy_benchmark': self.spy_data is not None,
                'information_ratio': self.performance_metrics.get('information_ratio', 0),
                'tracking_error': self.performance_metrics.get('tracking_error', 0),
                'beta': self.performance_metrics.get('beta', 0)
            },
            'optimization_status': {
                'optimization_score': self.optimization_results.get('optimization_score', 0),
                'parameters_optimized': len(self.optimization_results) > 0
            }
        })
        
        return summary
    
    def calculate_positions(self, signals: List[TradingSignal], 
                          current_positions: Dict[str, Position],
                          available_cash: float) -> Dict[str, float]:
        """Calculate target positions based on academic signals"""
        target_positions = {}
        
        try:
            # Calculate total signal strength for position sizing
            total_signal_strength = sum(abs(signal.confidence) for signal in signals)
            
            if total_signal_strength == 0:
                return target_positions
            
            # Calculate position sizes based on signal strength and available capital
            for signal in signals:
                if signal.symbol not in self.data:
                    continue
                
                # Calculate position size based on signal confidence and risk limits
                signal_weight = abs(signal.confidence) / total_signal_strength
                position_value = available_cash * signal_weight * self.risk_limits['max_position_size']
                
                # Get current price
                current_price = signal.price
                if current_price <= 0:
                    continue
                
                # Calculate quantity
                quantity = position_value / current_price
                
                # Apply signal direction
                if signal.signal_type == SignalType.SHORT:
                    quantity = -quantity
                
                # Apply risk limits
                max_position_value = available_cash * self.risk_limits['max_position_size']
                max_quantity = max_position_value / current_price
                quantity = np.clip(quantity, -max_quantity, max_quantity)
                
                target_positions[signal.symbol] = quantity
            
            logger.debug(f"Calculated positions for {len(target_positions)} symbols")
            
        except Exception as e:
            logger.error(f"Position calculation failed: {e}")
        
        return target_positions 