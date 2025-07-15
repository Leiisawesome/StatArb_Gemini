"""
Enhanced Backtesting Engine for StatArb Gemini Trading System

This module provides a comprehensive backtesting framework that integrates
all system components for realistic strategy testing.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import new structure components
from ...market_data.data_manager import MarketDataManager
from ...signal_generation.signal_generator import SignalGenerator
from ...signal_generation.feature_engine import FeatureEngine
from ...signal_generation.regime_detector import RegimeDetector
from ...strategy_engine.strategy_engine import StrategyEngine
from ...portfolio_management.portfolio_manager import PortfolioManager
from ...risk_management.risk_manager import RiskManager
from ...execution_engine.execution_engine import ExecutionEngine
from ...analytics.performance_analytics import PerformanceAnalytics
from ...infrastructure.config.base_config import BaseConfig

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig(BaseConfig):
    """Configuration for backtesting engine."""
    
    # Pair configuration
    symbols: List[str] = field(default_factory=lambda: ["AAPL", "MSFT"])
    
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
    daily_var_limit: float = 0.02
    
    # Model parameters
    use_kalman: bool = True
    use_hmm_regime: bool = True
    use_ensemble_filter: bool = True
    
    # Validation
    min_observations: int = 1000
    require_cointegration: bool = True
    
    # Performance
    benchmark_symbol: str = "SPY"
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    
    # Advanced features
    enable_regime_switching: bool = True
    enable_transaction_costs: bool = True
    enable_market_impact: bool = True
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        if len(self.symbols) < 2:
            raise ValueError("At least 2 symbols required for backtesting")
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError("Start date must be before end date")
        
        if self.z_entry_threshold <= 0:
            raise ValueError("Entry threshold must be positive")
            
        if self.position_size <= 0 or self.position_size > 1:
            raise ValueError("Position size must be between 0 and 1")
            
        return True

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
    trades: List[Dict[str, Any]] = field(default_factory=list)
    returns: np.ndarray = field(default_factory=lambda: np.array([]))
    positions: np.ndarray = field(default_factory=lambda: np.array([]))
    portfolio_values: np.ndarray = field(default_factory=lambda: np.array([]))
    
    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    
    # Benchmark comparison
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    
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
    cvar_95: float = 0.0
    max_leverage: float = 0.0
    
    # Additional data
    spread_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    signal_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    portfolio_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if len(self.returns) > 0:
            self._calculate_performance_metrics()
            self._calculate_risk_metrics()
    
    def _calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics."""
        returns = self.returns
        
        # Basic returns
        self.total_return = float(np.prod(1 + returns) - 1)
        self.annualized_return = float((1 + self.total_return) ** (252 / len(returns)) - 1)
        
        # Risk-adjusted returns
        if np.std(returns) > 0:
            self.sharpe_ratio = float(np.mean(returns) / np.std(returns) * np.sqrt(252))
        
        # Drawdown analysis
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        self.max_drawdown = float(np.min(drawdown))
        
        # Trade analysis
        self.win_rate = float(np.mean(returns > 0))
        
        # Profit factor
        winning_returns = returns[returns > 0]
        losing_returns = returns[returns < 0]
        
        if len(winning_returns) > 0 and len(losing_returns) > 0:
            self.profit_factor = float(np.sum(winning_returns) / abs(np.sum(losing_returns)))
    
    def _calculate_risk_metrics(self):
        """Calculate risk metrics."""
        returns = self.returns
        
        if len(returns) > 0:
            # Value at Risk
            self.var_95 = float(np.percentile(returns, 5))
            
            # Conditional Value at Risk (Expected Shortfall)
            var_returns = returns[returns <= self.var_95]
            if len(var_returns) > 0:
                self.cvar_95 = float(np.mean(var_returns))
            
            # Maximum leverage (from positions)
            if len(self.positions) > 0:
                self.max_leverage = float(np.max(np.abs(self.positions)))

class BacktestEngine:
    """Main backtesting engine that orchestrates all components."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.config.validate()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.data_manager = MarketDataManager()
        self.feature_engine = FeatureEngine()
        self.signal_generator = SignalGenerator()
        self.regime_detector = RegimeDetector()
        self.strategy_engine = StrategyEngine()
        self.portfolio_manager = PortfolioManager()
        self.risk_manager = RiskManager()
        self.execution_engine = ExecutionEngine()
        self.performance_analytics = PerformanceAnalytics()
        
        # State tracking
        self.current_portfolio = None
        self.current_positions = {}
        self.trade_history = []
        
    async def run_backtest(self, data: Optional[pd.DataFrame] = None) -> BacktestResult:
        """
        Run complete backtesting process.
        
        Args:
            data: Optional pre-loaded data. If None, will load from data sources.
            
        Returns:
            BacktestResult with comprehensive results
        """
        self.logger.info("Starting enhanced backtesting process...")
        
        try:
            # Load data if not provided
            if data is None:
                data = await self._load_data()
            
            # Validate data
            if len(data) < self.config.min_observations:
                raise ValueError(f"Insufficient data: {len(data)} < {self.config.min_observations}")
            
            # Prepare features and signals
            self.logger.info("Preparing features and signals...")
            features = await self._prepare_features(data)
            
            # Initialize models
            self.logger.info("Initializing models...")
            await self._initialize_models(features)
            
            # Run simulation
            self.logger.info("Running simulation...")
            simulation_results = await self._run_simulation(data, features)
            
            # Analyze performance
            self.logger.info("Analyzing performance...")
            result = await self._analyze_performance(simulation_results, data)
            
            self.logger.info(f"Backtesting completed. Total return: {result.total_return:.4f}, "
                           f"Sharpe: {result.sharpe_ratio:.4f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Backtesting failed: {e}")
            raise
    
    async def _load_data(self) -> pd.DataFrame:
        """Load market data for backtesting."""
        try:
            # Load price data for all symbols
            data = await self.data_manager.get_historical_data(
                symbols=self.config.symbols + [self.config.benchmark_symbol],
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                frequency='1D'
            )
            
            self.logger.info(f"Loaded {len(data)} observations from "
                           f"{data.index[0]} to {data.index[-1]}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
    
    async def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for strategy signals."""
        try:
            # Use feature engine to create comprehensive features
            features = await self.feature_engine.generate_features(
                data=data,
                feature_types=['technical', 'statistical', 'regime', 'cointegration']
            )
            
            # Add regime information if enabled
            if self.config.enable_regime_switching:
                regime_features = await self.regime_detector.detect_regimes(
                    data=data,
                    lookback_window=self.config.lookback_window
                )
                features = pd.concat([features, regime_features], axis=1)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
            raise
    
    async def _initialize_models(self, features: pd.DataFrame):
        """Initialize all model components."""
        try:
            # Initialize signal generator with features
            await self.signal_generator.initialize(
                features=features,
                config={
                    'entry_threshold': self.config.z_entry_threshold,
                    'exit_threshold': self.config.z_exit_threshold,
                    'use_ensemble': self.config.use_ensemble_filter
                }
            )
            
            # Initialize strategy engine
            await self.strategy_engine.initialize(
                signal_generator=self.signal_generator,
                config=self.config.dict()
            )
            
            # Initialize portfolio manager
            await self.portfolio_manager.initialize(
                symbols=self.config.symbols,
                initial_capital=1000000,  # Default initial capital
                config=self.config.dict()
            )
            
            # Initialize risk manager
            await self.risk_manager.initialize(
                config={
                    'var_limit': self.config.daily_var_limit,
                    'max_position_size': self.config.max_position_size,
                    'stop_loss': self.config.stop_loss_threshold
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
            raise
    
    async def _run_simulation(self, data: pd.DataFrame, features: pd.DataFrame) -> Dict[str, Any]:
        """Run the main simulation loop."""
        try:
            portfolio_values = []
            returns = []
            positions = []
            trades = []
            signals_data = []
            
            # Initialize portfolio
            current_value = 1000000  # Initial capital
            current_positions = {symbol: 0.0 for symbol in self.config.symbols}
            
            # Simulation loop
            for i in range(self.config.lookback_window, len(data)):
                timestamp = data.index[i]
                current_data = data.iloc[:i+1]
                current_features = features.iloc[:i+1]
                
                # Generate signals
                signals = await self.signal_generator.generate_signals(
                    data=current_data,
                    features=current_features
                )
                
                # Strategy decision
                strategy_output = await self.strategy_engine.make_decision(
                    signals=signals,
                    current_positions=current_positions,
                    market_data=current_data.iloc[-1]
                )
                
                # Risk check
                risk_check = await self.risk_manager.validate_positions(
                    proposed_positions=strategy_output['target_positions'],
                    current_portfolio_value=current_value,
                    market_data=current_data
                )
                
                if risk_check['approved']:
                    target_positions = strategy_output['target_positions']
                else:
                    target_positions = risk_check['adjusted_positions']
                
                # Execute trades
                trades_executed = await self._execute_trades(
                    current_positions=current_positions,
                    target_positions=target_positions,
                    market_data=current_data.iloc[-1],
                    timestamp=timestamp
                )
                
                # Update positions and portfolio value
                current_positions = target_positions.copy()
                new_value = await self._calculate_portfolio_value(
                    positions=current_positions,
                    prices=current_data.iloc[-1]
                )
                
                # Calculate returns
                if i > self.config.lookback_window:
                    period_return = (new_value - current_value) / current_value
                    returns.append(period_return)
                
                current_value = new_value
                
                # Store results
                portfolio_values.append(current_value)
                positions.append(list(current_positions.values()))
                trades.extend(trades_executed)
                signals_data.append({
                    'timestamp': timestamp,
                    'signals': signals,
                    'strategy_output': strategy_output
                })
            
            return {
                'portfolio_values': np.array(portfolio_values),
                'returns': np.array(returns),
                'positions': np.array(positions),
                'trades': trades,
                'signals_data': signals_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in simulation: {e}")
            raise
    
    async def _execute_trades(self, current_positions: Dict[str, float],
                            target_positions: Dict[str, float],
                            market_data: pd.Series,
                            timestamp: datetime) -> List[Dict[str, Any]]:
        """Execute trades to reach target positions."""
        trades = []
        
        for symbol in target_positions:
            current_pos = current_positions.get(symbol, 0.0)
            target_pos = target_positions[symbol]
            
            position_change = target_pos - current_pos
            
            if abs(position_change) > 0.001:  # Minimum trade size
                # Calculate transaction costs if enabled
                transaction_cost = 0.0
                if self.config.enable_transaction_costs:
                    transaction_cost = abs(position_change) * self.config.commission_rate
                    
                    # Add slippage
                    transaction_cost += abs(position_change) * self.config.slippage_rate
                    
                    # Add market impact if enabled
                    if self.config.enable_market_impact:
                        market_impact = self._calculate_market_impact(position_change, symbol)
                        transaction_cost += market_impact
                
                trade = {
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'position_change': position_change,
                    'price': market_data[symbol],
                    'transaction_cost': transaction_cost,
                    'current_position': current_pos,
                    'target_position': target_pos
                }
                trades.append(trade)
        
        return trades
    
    def _calculate_market_impact(self, position_change: float, symbol: str) -> float:
        """Calculate market impact cost."""
        # Simple market impact model
        # Impact = sqrt(position_size) * volatility * impact_coefficient
        impact_coefficient = 0.1  # Basis points per sqrt(position)
        return abs(position_change) ** 0.5 * impact_coefficient * 0.0001
    
    async def _calculate_portfolio_value(self, positions: Dict[str, float],
                                       prices: pd.Series) -> float:
        """Calculate current portfolio value."""
        total_value = 0.0
        
        for symbol, position in positions.items():
            if symbol in prices:
                total_value += position * prices[symbol]
        
        return total_value
    
    async def _analyze_performance(self, simulation_results: Dict[str, Any],
                                 data: pd.DataFrame) -> BacktestResult:
        """Analyze performance and create result object."""
        try:
            # Create result object
            result = BacktestResult(
                config=self.config,
                total_observations=len(data),
                start_date=data.index[0],
                end_date=data.index[-1],
                trades=simulation_results['trades'],
                returns=simulation_results['returns'],
                positions=simulation_results['positions'],
                portfolio_values=simulation_results['portfolio_values']
            )
            
            # Calculate signal statistics
            signals_data = simulation_results['signals_data']
            result.total_signals = len(signals_data)
            
            signal_types = [s['signals'].get('signal_type', 'HOLD') for s in signals_data]
            result.long_signals = signal_types.count('LONG')
            result.short_signals = signal_types.count('SHORT')
            result.hold_signals = signal_types.count('HOLD')
            
            # Calculate trade statistics
            result.total_trades = len(result.trades)
            
            # Benchmark comparison
            if self.config.benchmark_symbol in data.columns:
                benchmark_data = data[self.config.benchmark_symbol]
                benchmark_returns = benchmark_data.pct_change().dropna()
                
                if len(benchmark_returns) > 0:
                    result.benchmark_return = float(np.prod(1 + benchmark_returns) - 1)
                    
                    # Calculate alpha and beta
                    if len(result.returns) == len(benchmark_returns):
                        result.beta = float(np.cov(result.returns, benchmark_returns)[0, 1] / 
                                          np.var(benchmark_returns))
                        result.alpha = float(np.mean(result.returns) - 
                                           result.beta * np.mean(benchmark_returns))
            
            # Create summary DataFrames
            result.signal_data = pd.DataFrame([
                {
                    'timestamp': s['timestamp'],
                    'signal_type': s['signals'].get('signal_type', 'HOLD'),
                    'confidence': s['signals'].get('confidence', 0.0)
                }
                for s in signals_data
            ])
            
            result.portfolio_data = pd.DataFrame({
                'timestamp': data.index[-len(result.portfolio_values):],
                'portfolio_value': result.portfolio_values,
                'returns': np.concatenate([[0], result.returns])
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            raise
    
    def generate_report(self, result: BacktestResult) -> str:
        """Generate comprehensive backtesting report."""
        report = []
        report.append("=" * 80)
        report.append("STATARB GEMINI BACKTESTING REPORT")
        report.append("=" * 80)
        
        # Configuration
        report.append(f"\nConfiguration:")
        report.append(f"  Symbols: {', '.join(result.config.symbols)}")
        report.append(f"  Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        report.append(f"  Observations: {result.total_observations:,}")
        report.append(f"  Entry Threshold: {result.config.z_entry_threshold}")
        report.append(f"  Exit Threshold: {result.config.z_exit_threshold}")
        report.append(f"  Position Size: {result.config.position_size}")
        
        # Performance metrics
        report.append(f"\nPerformance Metrics:")
        report.append(f"  Total Return: {result.total_return*100:.2f}%")
        report.append(f"  Annualized Return: {result.annualized_return*100:.2f}%")
        report.append(f"  Sharpe Ratio: {result.sharpe_ratio:.4f}")
        report.append(f"  Max Drawdown: {result.max_drawdown*100:.2f}%")
        report.append(f"  Win Rate: {result.win_rate*100:.2f}%")
        report.append(f"  Profit Factor: {result.profit_factor:.4f}")
        
        # Benchmark comparison
        if result.benchmark_return != 0:
            report.append(f"\nBenchmark Comparison:")
            report.append(f"  Benchmark Return: {result.benchmark_return*100:.2f}%")
            report.append(f"  Alpha: {result.alpha*100:.2f}%")
            report.append(f"  Beta: {result.beta:.4f}")
            report.append(f"  Information Ratio: {result.information_ratio:.4f}")
        
        # Risk metrics
        report.append(f"\nRisk Metrics:")
        report.append(f"  VaR (95%): {result.var_95*100:.2f}%")
        report.append(f"  CVaR (95%): {result.cvar_95*100:.2f}%")
        report.append(f"  Max Leverage: {result.max_leverage:.2f}x")
        
        # Trading statistics
        report.append(f"\nTrading Statistics:")
        report.append(f"  Total Trades: {result.total_trades:,}")
        report.append(f"  Total Signals: {result.total_signals:,}")
        report.append(f"  Long Signals: {result.long_signals:,}")
        report.append(f"  Short Signals: {result.short_signals:,}")
        report.append(f"  Hold Signals: {result.hold_signals:,}")
        
        return "\n".join(report)
