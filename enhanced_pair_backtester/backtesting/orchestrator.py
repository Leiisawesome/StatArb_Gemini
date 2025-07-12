"""
Simplified Backtesting Orchestrator for Final Integration Testing
===============================================================

A simplified version of the orchestrator that works with existing components
and provides a foundation for testing the final integration.

Author: Pro Quant Desk Trader
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import os
import json
from pathlib import Path

# System imports with fallback
try:
    from ..config.backtest_config import BacktestConfig
    from ..data.data_loader import DataLoader
    from ..utils.spread_calculator import SpreadCalculator
    from ..models.kalman_filter import create_kalman_filter
    from ..models.hmm_regime_optimized import create_optimized_hmm_detector
    from ..models.ensemble_filter_simple import create_simple_ensemble_filter
    from ..models.signal_generator import SignalGenerator, SignalConfig
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    from config.backtest_config import BacktestConfig
    from data.data_loader import DataLoader
    from utils.spread_calculator import SpreadCalculator
    from models.kalman_filter import create_kalman_filter
    from models.hmm_regime_optimized import create_optimized_hmm_detector
    from models.ensemble_filter_simple import create_simple_ensemble_filter
    from models.signal_generator import SignalGenerator, SignalConfig


@dataclass
class BacktestResults:
    """Simplified backtest results container."""
    
    # Basic information
    pair_name: str
    start_date: str
    end_date: str
    total_days: int
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    cvar_95: float = 0.0
    beta: float = 0.0
    alpha: float = 0.0
    information_ratio: float = 0.0
    
    # Regime analysis
    regime_distribution: Dict[str, float] = field(default_factory=dict)
    regime_performance: Dict[str, float] = field(default_factory=dict)
    
    # Model performance
    signal_accuracy: float = 0.0
    ensemble_accuracy: float = 0.0
    kalman_tracking_error: float = 0.0
    
    # Execution metrics
    avg_slippage: float = 0.0
    total_costs: float = 0.0
    cost_ratio: float = 0.0
    
    # Detailed data
    equity_curve: pd.Series = field(default_factory=pd.Series)
    trade_log: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_returns: pd.Series = field(default_factory=pd.Series)
    position_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    signal_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Visualization paths
    chart_paths: Dict[str, str] = field(default_factory=dict)


class BacktestOrchestrator:
    """
    Simplified backtesting orchestrator for final integration testing.
    """
    
    def __init__(self, config: BacktestConfig):
        """Initialize the orchestrator with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.data_loader = None
        self.spread_calculator = None
        self.signal_generator = None
        
        # Data containers
        self.training_data = None
        self.testing_data = None
        self.spread_result = None
        self.hmm_result = None
        self.ensemble_result = None
        
        # Results
        self.backtest_results = None
        
        # Ensure output directory exists
        os.makedirs(config.output_dir, exist_ok=True)
    
    def initialize_components(self) -> bool:
        """Initialize all system components."""
        try:
            self.logger.info("Initializing backtesting components...")
            
            # Initialize data loader
            self.data_loader = DataLoader(self.config.to_dict())
            
            # Initialize spread calculator
            hedge_ratio_method = 'kalman' if self.config.use_kalman_filter else 'ols'
            spread_config = {
                'hedge_ratio_method': hedge_ratio_method,
                'lookback_window': self.config.lookback_window,
                'min_observations': 30
            }
            self.spread_calculator = SpreadCalculator(spread_config)
            
            # Initialize signal generator
            if self.config.use_kalman_filter or self.config.use_hmm_regime or self.config.use_ensemble_filter:
                signal_config = SignalConfig(
                    mean_reverting_entry=self.config.entry_threshold,
                    mean_reverting_exit=self.config.exit_threshold,
                    trending_entry=self.config.entry_threshold * 0.75,
                    trending_exit=self.config.exit_threshold * 0.6,
                    volatile_entry=self.config.entry_threshold * 1.5,
                    volatile_exit=self.config.exit_threshold * 1.2,
                    max_position_size=0.3,
                    ensemble_confidence_threshold=0.7,
                    ensemble_strength_threshold=60.0
                )
                self.signal_generator = SignalGenerator(signal_config)
            
            self.logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            return False
    
    def load_and_validate_data(self) -> bool:
        """Load and validate data for backtesting."""
        try:
            self.logger.info("Loading and validating data...")
            
            # Validate data availability
            validation = self.data_loader.validate_data_quality(
                self.config.symbol1, self.config.symbol2,
                self.config.training_start, self.config.testing_end
            )
            
            if not validation['valid']:
                self.logger.error("Data validation failed:")
                for issue in validation['issues']:
                    self.logger.error(f"  - {issue}")
                return False
            
            # Load training data
            self.training_data = self.data_loader.get_aligned_data(
                self.config.symbol1, self.config.symbol2,
                self.config.training_start, self.config.training_end
            )
            
            # Load testing data
            self.testing_data = self.data_loader.get_aligned_data(
                self.config.symbol1, self.config.symbol2,
                self.config.testing_start, self.config.testing_end
            )
            
            self.logger.info(f"Training data: {len(self.training_data)} observations")
            self.logger.info(f"Testing data: {len(self.testing_data)} observations")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data loading failed: {e}")
            return False
    
    def train_models(self) -> bool:
        """Train all models on training data."""
        try:
            self.logger.info("Training models on training data...")
            
            # Calculate spread on training data
            price1 = self.training_data[f'{self.config.symbol1}_close']
            price2 = self.training_data[f'{self.config.symbol2}_close']
            
            self.spread_result = self.spread_calculator.calculate_spread(
                price1, price2, self.config.symbol1, self.config.symbol2
            )
            
            self.logger.info(f"Spread calculated using {self.spread_result.method} method")
            
            # Train HMM regime detector if enabled
            if self.config.use_hmm_regime:
                self.logger.info("Training HMM regime detector...")
                self.hmm_result = create_optimized_hmm_detector(
                    self.spread_result.spread,
                    n_states=3,
                    subsample_factor=10,
                    max_iterations=25,
                    tolerance=1e-3,
                    random_state=42
                )
                self.logger.info(f"HMM detected {len(self.hmm_result.regime_changes)} regime changes")
            
            # Train ensemble filter if enabled
            if self.config.use_ensemble_filter:
                self.logger.info("Training ensemble filter...")
                self.ensemble_result = create_simple_ensemble_filter(
                    self.spread_result.spread,
                    hmm_result=self.hmm_result,
                    random_state=42
                )
                self.logger.info(f"Ensemble model trained successfully")
            
            self.logger.info("Model training completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Model training failed: {e}")
            return False
    
    def run_simple_backtest(self) -> bool:
        """Run a simplified backtesting process."""
        try:
            self.logger.info("Starting simplified backtesting process...")
            
            # Combine all data for backtesting
            all_data = pd.concat([self.training_data, self.testing_data])
            
            # Initialize tracking variables
            equity_curve = []
            trade_log = []
            signal_history = []
            
            current_position = 0
            current_capital = self.config.initial_capital
            
            # Simple backtesting logic
            for i in range(len(self.training_data), len(all_data)):
                current_date = all_data.index[i]
                
                # Simple signal generation based on spread
                if self.spread_result:
                    # Calculate current z-score
                    current_spread = self.spread_result.spread.iloc[i] if i < len(self.spread_result.spread) else 0
                    z_score = (current_spread - self.spread_result.spread_mean) / self.spread_result.spread_std
                    
                    # Simple signal logic
                    signal_type = 'HOLD'
                    if z_score > self.config.entry_threshold:
                        signal_type = 'SHORT'
                    elif z_score < -self.config.entry_threshold:
                        signal_type = 'LONG'
                    elif abs(z_score) < self.config.exit_threshold:
                        signal_type = 'HOLD'
                    
                    # Record signal
                    signal_history.append({
                        'date': current_date,
                        'signal_type': signal_type,
                        'z_score': z_score,
                        'spread': current_spread
                    })
                    
                    # Simple position management
                    if signal_type == 'LONG' and current_position <= 0:
                        current_position = 1
                        trade_log.append({
                            'date': current_date,
                            'action': 'BUY',
                            'z_score': z_score
                        })
                    elif signal_type == 'SHORT' and current_position >= 0:
                        current_position = -1
                        trade_log.append({
                            'date': current_date,
                            'action': 'SELL',
                            'z_score': z_score
                        })
                    elif signal_type == 'HOLD':
                        current_position = 0
                
                # Simple portfolio valuation
                portfolio_value = current_capital + current_position * 1000  # Simplified
                
                # Record equity curve
                equity_curve.append({
                    'date': current_date,
                    'portfolio_value': portfolio_value,
                    'position': current_position
                })
            
            # Convert to DataFrames
            equity_df = pd.DataFrame(equity_curve).set_index('date')
            trade_df = pd.DataFrame(trade_log)
            signal_df = pd.DataFrame(signal_history).set_index('date')
            
            # Calculate simple performance metrics
            returns = equity_df['portfolio_value'].pct_change().dropna()
            
            # Create simplified results
            self.backtest_results = BacktestResults(
                pair_name=self.config.pair_name,
                start_date=self.config.testing_start,
                end_date=self.config.testing_end,
                total_days=len(equity_df),
                
                # Performance metrics
                total_return=(equity_df['portfolio_value'].iloc[-1] / self.config.initial_capital - 1) if len(equity_df) > 0 else 0,
                annualized_return=returns.mean() * 252 if len(returns) > 0 else 0,
                volatility=returns.std() * np.sqrt(252) if len(returns) > 0 else 0,
                sharpe_ratio=(returns.mean() * 252) / (returns.std() * np.sqrt(252)) if len(returns) > 0 and returns.std() > 0 else 0,
                max_drawdown=self._calculate_max_drawdown(equity_df['portfolio_value']) if len(equity_df) > 0 else 0,
                
                # Trading statistics
                total_trades=len(trade_df),
                
                # Detailed data
                equity_curve=equity_df['portfolio_value'],
                trade_log=trade_df,
                daily_returns=returns,
                signal_history=signal_df
            )
            
            self.logger.info("Simplified backtesting completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Simplified backtesting failed: {e}")
            return False
    
    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown."""
        if len(equity_curve) == 0:
            return 0.0
        peak = equity_curve.expanding(min_periods=1).max()
        drawdown = (equity_curve - peak) / peak
        return drawdown.min()
    
    def generate_simple_report(self) -> str:
        """Generate simplified backtest report."""
        if self.backtest_results is None:
            return "No backtest results available"
        
        results = self.backtest_results
        
        report = f"""
{'='*80}
SIMPLIFIED PAIR TRADING BACKTEST REPORT
{'='*80}

PAIR INFORMATION:
  Trading Pair: {results.pair_name}
  Testing Period: {results.start_date} to {results.end_date}
  Total Days: {results.total_days}

PERFORMANCE METRICS:
  Total Return: {results.total_return:.2%}
  Annualized Return: {results.annualized_return:.2%}
  Volatility: {results.volatility:.2%}
  Sharpe Ratio: {results.sharpe_ratio:.3f}
  Maximum Drawdown: {results.max_drawdown:.2%}

TRADING STATISTICS:
  Total Trades: {results.total_trades}

{'='*80}
"""
        
        return report
    
    def save_simple_results(self) -> Dict[str, str]:
        """Save simplified results to files."""
        if self.backtest_results is None:
            return {}
        
        output_paths = {}
        
        try:
            # Save simplified report
            report_path = os.path.join(self.config.output_dir, f"{self.config.pair_name}_simple_report.txt")
            with open(report_path, 'w') as f:
                f.write(self.generate_simple_report())
            output_paths['report'] = report_path
            
            # Save equity curve
            if not self.backtest_results.equity_curve.empty:
                equity_path = os.path.join(self.config.output_dir, f"{self.config.pair_name}_simple_equity.csv")
                self.backtest_results.equity_curve.to_csv(equity_path)
                output_paths['equity_curve'] = equity_path
            
            # Save trade log
            if not self.backtest_results.trade_log.empty:
                trades_path = os.path.join(self.config.output_dir, f"{self.config.pair_name}_simple_trades.csv")
                self.backtest_results.trade_log.to_csv(trades_path, index=False)
                output_paths['trades'] = trades_path
            
            self.logger.info(f"Simple results saved to {len(output_paths)} files")
            return output_paths
            
        except Exception as e:
            self.logger.error(f"Failed to save simple results: {e}")
            return {}
    
    def run_complete_simple_backtest(self) -> bool:
        """Run the complete simplified backtesting process."""
        try:
            self.logger.info("Starting complete simplified backtesting process...")
            
            # Step 1: Initialize components
            if not self.initialize_components():
                return False
            
            # Step 2: Load and validate data
            if not self.load_and_validate_data():
                return False
            
            # Step 3: Train models
            if not self.train_models():
                return False
            
            # Step 4: Run simplified backtest
            if not self.run_simple_backtest():
                return False
            
            # Step 5: Save results
            output_paths = self.save_simple_results()
            
            # Step 6: Generate final summary
            self.logger.info("Simplified backtesting process completed successfully!")
            self.logger.info(f"Results saved to: {output_paths}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Complete simplified backtesting process failed: {e}")
            return False 