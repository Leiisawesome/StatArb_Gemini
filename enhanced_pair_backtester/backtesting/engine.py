"""
Backtesting Engine for Enhanced Pair Trading System

This module provides a comprehensive backtesting framework that integrates
all system components for realistic strategy testing.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging

# Import our system components
try:
    from ..data.data_loader import DataLoader
    from ..strategies.spread_calculator import SpreadCalculator
    from ..models.kalman_filter import create_kalman_filter
    from ..models.hmm_regime_optimized import HMMRegimeDetector
    from ..models.ensemble_filter_simple import EnsembleFilter
    from ..strategies.signal_generator import SignalGenerator, TradingSignal
    from ..execution.position_sizer import PositionSizer
    from ..execution.execution_engine import ExecutionEngine
    from ..analysis.performance_metrics import PerformanceAnalyzer
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    from data.data_loader import DataLoader
    from strategies.spread_calculator import SpreadCalculator
    from models.kalman_filter import create_kalman_filter
    from models.hmm_regime_optimized import HMMRegimeDetector
    from models.ensemble_filter_simple import EnsembleFilter
    from strategies.signal_generator import SignalGenerator, TradingSignal
    from execution.position_sizer import PositionSizer
    from execution.execution_engine import ExecutionEngine
    from analysis.performance_metrics import PerformanceAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting engine."""
    
    # Pair configuration
    symbol1: str = "TLT"
    symbol2: str = "TMF"
    
    # Time period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Strategy parameters
    z_entry_threshold: float = 2.0
    z_exit_threshold: float = 0.5
    lookback_window: int = 40
    position_size: float = 0.2
    
    # Execution parameters
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    
    # Risk management
    max_position_size: float = 0.5
    stop_loss_threshold: float = 0.05
    take_profit_threshold: float = 0.02
    
    # Model parameters
    use_kalman: bool = True
    use_hmm_regime: bool = True
    use_ensemble_filter: bool = True
    
    # Validation
    min_observations: int = 1000
    require_cointegration: bool = True

@dataclass
class BacktestResult:
    """Results from backtesting run."""
    
    # Configuration
    config: BacktestConfig
    
    # Data statistics
    total_observations: int
    start_date: datetime
    end_date: datetime
    
    # Trading results
    trades: List[Any] = field(default_factory=list)
    returns: np.ndarray = field(default_factory=lambda: np.array([]))
    positions: np.ndarray = field(default_factory=lambda: np.array([]))
    
    # Performance metrics
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Signal statistics
    total_signals: int = 0
    long_signals: int = 0
    short_signals: int = 0
    hold_signals: int = 0
    
    # Execution statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Risk metrics
    var_95: float = 0.0
    expected_shortfall: float = 0.0
    
    # Additional data
    spread_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    signal_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if len(self.returns) > 0:
            self.total_return = float(np.prod(1 + self.returns) - 1)
            self.sharpe_ratio = float(np.mean(self.returns) / np.std(self.returns) * np.sqrt(252)) if np.std(self.returns) > 0 else 0.0
            
            # Max drawdown
            cumulative = np.cumprod(1 + self.returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            self.max_drawdown = float(np.min(drawdown))
            
            # Win rate
            self.win_rate = float(np.mean(self.returns > 0))
            
            # Profit factor
            winning_returns = self.returns[self.returns > 0]
            losing_returns = self.returns[self.returns < 0]
            
            if len(winning_returns) > 0 and len(losing_returns) > 0:
                self.profit_factor = float(np.sum(winning_returns) / abs(np.sum(losing_returns)))
            
            # Risk metrics
            self.var_95 = float(np.percentile(self.returns, 5))
            self.expected_shortfall = float(np.mean(self.returns[self.returns <= self.var_95]))

class BacktestEngine:
    """Main backtesting engine that orchestrates all components."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.data_loader = DataLoader()
        self.spread_calculator = SpreadCalculator()
        self.position_sizer = PositionSizer()
        self.execution_engine = ExecutionEngine()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Model components (initialized as needed)
        self.kalman_filter = None
        self.hmm_detector = None
        self.ensemble_filter = None
        self.signal_generator = None
        
    def run_backtest(self, data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """
        Run complete backtesting process.
        
        Args:
            data: Optional pre-loaded data. If None, will load from data sources.
            
        Returns:
            BacktestResult with comprehensive results
        """
        self.logger.info("Starting backtesting process...")
        
        # Load data if not provided
        if data is None:
            data = self._load_data()
        
        # Validate data
        if len(data) < self.config.min_observations:
            raise ValueError(f"Insufficient data: {len(data)} < {self.config.min_observations}")
        
        # Calculate spreads
        self.logger.info("Calculating spreads...")
        spread_data = self._calculate_spreads(data)
        
        # Initialize models
        self.logger.info("Initializing models...")
        self._initialize_models(spread_data)
        
        # Generate signals
        self.logger.info("Generating trading signals...")
        signals = self._generate_signals(spread_data)
        
        # Execute trades
        self.logger.info("Executing trades...")
        trades, returns, positions = self._execute_trades(signals, spread_data)
        
        # Analyze performance
        self.logger.info("Analyzing performance...")
        performance_metrics = self._analyze_performance(returns, trades)
        
        # Create result
        result = BacktestResult(
            config=self.config,
            total_observations=len(data),
            start_date=data.index[0],
            end_date=data.index[-1],
            trades=trades,
            returns=returns,
            positions=positions,
            spread_data=spread_data,
            signal_data=signals
        )
        
        self.logger.info(f"Backtesting completed. Total return: {result.total_return:.4f}, Sharpe: {result.sharpe_ratio:.4f}")
        
        return result
    
    def _load_data(self) -> pd.DataFrame:
        """Load price data for the pair."""
        try:
            # Load data using our data loader
            data = self.data_loader.load_pair_data(
                symbol1=self.config.symbol1,
                symbol2=self.config.symbol2,
                start_date=self.config.start_date,
                end_date=self.config.end_date
            )
            
            self.logger.info(f"Loaded {len(data)} observations from {data.index[0]} to {data.index[-1]}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    def _calculate_spreads(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate spread and related metrics."""
        try:
            # Calculate basic spread
            spread_result = self.spread_calculator.calculate_spread(
                data[self.config.symbol1], 
                data[self.config.symbol2],
                method='kalman' if self.config.use_kalman else 'ols'
            )
            
            # Create comprehensive spread dataframe
            spread_data = pd.DataFrame({
                'price1': data[self.config.symbol1],
                'price2': data[self.config.symbol2],
                'spread': spread_result['spread'],
                'hedge_ratio': spread_result['hedge_ratio'],
                'z_score': spread_result['z_score']
            }, index=data.index)
            
            # Add rolling statistics
            spread_data['rolling_mean'] = spread_data['spread'].rolling(self.config.lookback_window).mean()
            spread_data['rolling_std'] = spread_data['spread'].rolling(self.config.lookback_window).std()
            spread_data['rolling_z_score'] = (spread_data['spread'] - spread_data['rolling_mean']) / spread_data['rolling_std']
            
            return spread_data
            
        except Exception as e:
            self.logger.error(f"Error calculating spreads: {e}")
            raise
    
    def _initialize_models(self, spread_data: pd.DataFrame):
        """Initialize all model components."""
        try:
            # Initialize Kalman filter if requested
            if self.config.use_kalman:
                self.kalman_filter = create_kalman_filter(
                    spread_data['price1'].values,
                    spread_data['price2'].values
                )
            
            # Initialize HMM regime detector if requested
            if self.config.use_hmm_regime:
                self.hmm_detector = HMMRegimeDetector(n_components=3)
                self.hmm_detector.fit(spread_data['spread'].values)
            
            # Initialize ensemble filter if requested
            if self.config.use_ensemble_filter:
                self.ensemble_filter = EnsembleFilter()
                
                # Prepare features for ensemble
                features = self._prepare_ensemble_features(spread_data)
                
                # Create simple labels for training (mean reversion assumption)
                labels = np.where(spread_data['z_score'] > 1.5, -1,  # Short signal
                                np.where(spread_data['z_score'] < -1.5, 1, 0))  # Long signal
                
                # Train ensemble
                self.ensemble_filter.fit(features, labels)
            
            # Initialize signal generator
            self.signal_generator = SignalGenerator(
                spread_calculator=self.spread_calculator,
                kalman_filter=self.kalman_filter,
                hmm_detector=self.hmm_detector,
                ensemble_filter=self.ensemble_filter
            )
            
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
            raise
    
    def _prepare_ensemble_features(self, spread_data: pd.DataFrame) -> np.ndarray:
        """Prepare features for ensemble model."""
        features = []
        
        # Basic features
        features.append(spread_data['z_score'].values)
        features.append(spread_data['rolling_z_score'].values)
        
        # Momentum features
        features.append(spread_data['spread'].pct_change(5).values)  # 5-day momentum
        features.append(spread_data['spread'].pct_change(10).values)  # 10-day momentum
        
        # Volatility features
        features.append(spread_data['spread'].rolling(20).std().values)
        
        # Stack features
        feature_matrix = np.column_stack(features)
        
        # Remove NaN rows
        valid_rows = ~np.isnan(feature_matrix).any(axis=1)
        return feature_matrix[valid_rows]
    
    def _generate_signals(self, spread_data: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals using signal generator."""
        try:
            signals = []
            
            for i in range(len(spread_data)):
                if i < self.config.lookback_window:
                    # Not enough data for signal generation
                    signal = TradingSignal(
                        timestamp=spread_data.index[i],
                        signal_type='HOLD',
                        confidence=0.0,
                        position_size=0.0,
                        z_score=spread_data['z_score'].iloc[i],
                        spread=spread_data['spread'].iloc[i],
                        hedge_ratio=spread_data['hedge_ratio'].iloc[i]
                    )
                else:
                    # Generate signal using current data
                    current_data = spread_data.iloc[:i+1]
                    signal = self.signal_generator.generate_signal(
                        current_data,
                        entry_threshold=self.config.z_entry_threshold,
                        exit_threshold=self.config.z_exit_threshold
                    )
                
                signals.append(signal)
            
            # Convert to DataFrame
            signal_df = pd.DataFrame([
                {
                    'timestamp': s.timestamp,
                    'signal_type': s.signal_type,
                    'confidence': s.confidence,
                    'position_size': s.position_size,
                    'z_score': s.z_score,
                    'spread': s.spread,
                    'hedge_ratio': s.hedge_ratio
                }
                for s in signals
            ])
            
            signal_df.set_index('timestamp', inplace=True)
            
            return signal_df
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            raise
    
    def _execute_trades(self, signals: pd.DataFrame, spread_data: pd.DataFrame) -> Tuple[List[Any], np.ndarray, np.ndarray]:
        """Execute trades based on signals."""
        try:
            trades = []
            returns = []
            positions = []
            
            current_position = 0.0
            last_trade_price = 0.0
            
            for i in range(len(signals)):
                signal = signals.iloc[i]
                current_spread = spread_data['spread'].iloc[i]
                
                # Determine target position
                if signal['signal_type'] == 'LONG':
                    target_position = signal['position_size']
                elif signal['signal_type'] == 'SHORT':
                    target_position = -signal['position_size']
                else:
                    target_position = 0.0
                
                # Calculate position change
                position_change = target_position - current_position
                
                # Execute trade if position changes
                if abs(position_change) > 0.001:  # Minimum trade size
                    trade = {
                        'timestamp': signals.index[i],
                        'signal_type': signal['signal_type'],
                        'position_change': position_change,
                        'price': current_spread,
                        'confidence': signal['confidence']
                    }
                    trades.append(trade)
                    last_trade_price = current_spread
                
                # Update position
                current_position = target_position
                positions.append(current_position)
                
                # Calculate returns
                if i > 0 and abs(current_position) > 0.001:
                    spread_return = (current_spread - spread_data['spread'].iloc[i-1]) / spread_data['spread'].iloc[i-1]
                    position_return = current_position * spread_return
                    
                    # Apply transaction costs
                    if abs(position_change) > 0.001:
                        position_return -= abs(position_change) * self.config.commission_rate
                        position_return -= abs(position_change) * self.config.slippage_rate
                    
                    returns.append(position_return)
                else:
                    returns.append(0.0)
            
            return trades, np.array(returns), np.array(positions)
            
        except Exception as e:
            self.logger.error(f"Error executing trades: {e}")
            raise
    
    def _analyze_performance(self, returns: np.ndarray, trades: List[Any]) -> Dict[str, float]:
        """Analyze performance using performance analyzer."""
        try:
            if len(returns) == 0:
                return {}
            
            # Use performance analyzer
            performance_data = pd.DataFrame({
                'returns': returns,
                'cumulative_returns': np.cumprod(1 + returns)
            })
            
            metrics = self.performance_analyzer.calculate_metrics(performance_data)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            return {}
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate comprehensive backtesting report."""
        report = []
        report.append("=" * 80)
        report.append("BACKTESTING REPORT")
        report.append("=" * 80)
        
        # Configuration
        report.append(f"\nConfiguration:")
        report.append(f"  Pair: {result.config.symbol1}/{result.config.symbol2}")
        report.append(f"  Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        report.append(f"  Observations: {result.total_observations}")
        report.append(f"  Entry Threshold: {result.config.z_entry_threshold}")
        report.append(f"  Exit Threshold: {result.config.z_exit_threshold}")
        report.append(f"  Position Size: {result.config.position_size}")
        
        # Performance metrics
        report.append(f"\nPerformance Metrics:")
        report.append(f"  Total Return: {result.total_return*100:.2f}%")
        report.append(f"  Sharpe Ratio: {result.sharpe_ratio:.4f}")
        report.append(f"  Max Drawdown: {result.max_drawdown*100:.2f}%")
        report.append(f"  Win Rate: {result.win_rate*100:.2f}%")
        report.append(f"  Profit Factor: {result.profit_factor:.4f}")
        
        # Risk metrics
        report.append(f"\nRisk Metrics:")
        report.append(f"  VaR (95%): {result.var_95*100:.2f}%")
        report.append(f"  Expected Shortfall: {result.expected_shortfall*100:.2f}%")
        
        # Trading statistics
        report.append(f"\nTrading Statistics:")
        report.append(f"  Total Trades: {len(result.trades)}")
        report.append(f"  Total Signals: {result.total_signals}")
        report.append(f"  Long Signals: {result.long_signals}")
        report.append(f"  Short Signals: {result.short_signals}")
        report.append(f"  Hold Signals: {result.hold_signals}")
        
        return "\n".join(report) 