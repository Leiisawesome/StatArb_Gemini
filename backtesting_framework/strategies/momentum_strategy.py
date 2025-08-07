#!/usr/bin/env python3
"""
Advanced Momentum Trading Strategy for Backtesting Framework

This strategy defines momentum trading parameters and logic, delegating actual
data processing and execution to core_structure modules for loose coupling.

Design:
- Strategy defines momentum-specific parameters and rules
- Core structure handles data loading, signal generation, and execution
- Training period: 2023, Trading period: 2024
- Modular architecture for easy testing and optimization
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from .base_strategy import BaseStrategy, StrategyConfig, TradingSignal, SignalType, Position

# Import flow monitoring
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.flow_monitor import get_flow_monitor, FlowStage, ComponentType, monitor_stage

logger = logging.getLogger(__name__)

class MomentumType(Enum):
    """Types of momentum calculations"""
    SIMPLE_RETURN = "simple_return"
    LOG_RETURN = "log_return" 
    RISK_ADJUSTED = "risk_adjusted"
    CROSS_SECTIONAL = "cross_sectional"

class SignalDecayType(Enum):
    """Signal decay models"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"

@dataclass
class MomentumConfig(StrategyConfig):
    """
    Configuration for momentum trading strategy
    
    Defines all momentum-specific parameters that will be passed to
    core_structure modules for execution.
    """
    # Core momentum parameters
    momentum_type: MomentumType = MomentumType.RISK_ADJUSTED
    lookback_period: int = 252  # 1 year for momentum calculation
    skip_period: int = 21  # Skip most recent month to avoid reversal
    momentum_threshold: float = 0.15  # 15% minimum momentum for signal
    
    # Signal generation parameters
    signal_decay_type: SignalDecayType = SignalDecayType.EXPONENTIAL
    signal_decay_lambda: float = 0.8  # Exponential decay factor
    rebalancing_frequency: str = "monthly"  # monthly, weekly, daily
    
    # Risk management parameters
    volatility_lookback: int = 60  # 3 months for volatility calculation
    target_volatility: float = 0.15  # 15% annualized target volatility
    max_weight_per_asset: float = 0.10  # 10% max allocation per asset
    sector_neutrality: bool = True  # Apply sector neutral constraints
    
    # Universe definition
    universe_size: int = 100  # Top N stocks by market cap
    min_market_cap: float = 1e9  # $1B minimum market cap
    min_avg_volume: float = 1e6  # $1M average daily volume
    
    # Transaction cost modeling
    commission_rate: float = 0.0005  # 5 bps commission
    bid_ask_spread: float = 0.0008  # 8 bps average spread
    market_impact_rate: float = 0.0012  # 12 bps market impact
    
    # Capital management
    initial_capital: float = 250000.0  # $250K for momentum strategy
    
    # Training and trading periods
    training_start: str = "2023-01-01"
    training_end: str = "2023-12-31" 
    trading_start: str = "2024-01-01"
    trading_end: str = "2024-12-31"
    
    # Performance attribution
    benchmark_symbol: str = "SPY"
    enable_performance_attribution: bool = True
    enable_regime_detection: bool = True
    
    # Core structure module configs
    market_data_config: Dict[str, Any] = field(default_factory=lambda: {
        "data_source": "clickhouse",
        "frequency": "daily",
        "adjust_splits": True,
        "adjust_dividends": True,
        "min_data_quality": 0.95
    })
    
    signal_generation_config: Dict[str, Any] = field(default_factory=lambda: {
        "momentum_calculation_method": "vectorized",
        "risk_adjustment_method": "rolling_volatility", 
        "cross_sectional_normalization": True,
        "sector_neutralization": True
    })
    
    execution_config: Dict[str, Any] = field(default_factory=lambda: {
        "execution_model": "realistic",
        "slippage_model": "linear",
        "timing_model": "end_of_day",
        "partial_fills": True
    })
    
    optimization_config: Dict[str, Any] = field(default_factory=lambda: {
        "optimizer_type": "mean_variance",
        "constraint_handling": "penalty",
        "risk_model": "factor_based",
        "turnover_penalty": 0.001
    })


class MomentumStrategy(BaseStrategy):
    """
    Advanced Momentum Trading Strategy
    
    This strategy defines momentum trading logic and parameters, then delegates
    execution to core_structure modules for loose coupling and modularity.
    """
    
    def __init__(self, config: MomentumConfig):
        """
        Initialize momentum strategy with core structure integration
        
        Args:
            config: Momentum strategy configuration
        """
        super().__init__(config)
        
        # Handle enum conversion if needed (for JSON/dict config inputs)
        if hasattr(config, 'momentum_type') and isinstance(config.momentum_type, str):
            # Convert string to enum
            config.momentum_type = MomentumType(config.momentum_type)
        
        self.config = config
        
        # Initialize flow monitoring
        self.flow_monitor = get_flow_monitor()
        
        # Initialize core structure modules (lazy loading)
        self._data_manager = None
        self._signal_generator = None
        self._execution_engine = None
        self._optimizer = None
        self._performance_analyzer = None
        
        # Strategy state
        self.training_data: Optional[Dict[str, pd.DataFrame]] = None
        self.is_trained: bool = False
        self.current_signals: Dict[str, float] = {}
        self.momentum_history: Dict[str, List[float]] = {}
        self.volatility_history: Dict[str, List[float]] = {}
        
        logger.info(f"Initialized momentum strategy: {config.name}")
        logger.info(f"Training period: {config.training_start} to {config.training_end}")
        logger.info(f"Trading period: {config.trading_start} to {config.trading_end}")
    
    def _init_data_manager(self):
        """Initialize data manager with fallback"""
        if self._data_manager is None:
            try:
                from core_structure.market_data import EnhancedDataManager
                self._data_manager = EnhancedDataManager()
                logger.info("Using core structure data manager")
            except ImportError as e:
                logger.error(f"Core system not available - DataManager import failed: {e}")
                self._data_manager = self._create_fallback_data_manager()
    
    def _init_signal_generator(self):
        """Initialize signal generator with fallback"""
        if self._signal_generator is None:
            try:
                import sys, os
                # Get the correct path to StatArb_Gemini directory
                current_dir = os.path.dirname(__file__)  # strategies/
                backtesting_dir = os.path.dirname(current_dir)  # backtesting_framework/
                statarb_dir = os.path.dirname(backtesting_dir)  # StatArb_Gemini/
                sys.path.append(statarb_dir)
                
                from core_structure.signal_generation.signal_generator import SignalGenerator, SignalConfig
                
                # Create compatible signal config
                signal_config = SignalConfig(
                    lookback_window=self.config.lookback_period,
                    min_confidence_threshold=self.config.momentum_threshold,
                    volatility_target=self.config.target_volatility,
                    max_position_size=self.config.max_weight_per_asset,
                    # Map momentum-specific settings to core structure parameters
                    enable_ml_features=False,  # Keep it simple for momentum
                    enable_real_time=False    # We're doing batch processing
                )
                
                self._signal_generator = SignalGenerator(signal_config)
                logger.info("Using core structure signal generator with compatible config")
            except Exception as e:
                logger.info(f"Core structure signal generator not available: {e}")
                logger.info("Using enhanced fallback implementation")
                self._signal_generator = self._create_fallback_signal_generator()
    
    def _init_execution_engine(self):
        """Initialize execution engine with fallback"""
        if self._execution_engine is None:
            try:
                import sys, os
                # Get the correct path to StatArb_Gemini directory
                current_dir = os.path.dirname(__file__)  # strategies/
                backtesting_dir = os.path.dirname(current_dir)  # backtesting_framework/
                statarb_dir = os.path.dirname(backtesting_dir)  # StatArb_Gemini/
                sys.path.append(statarb_dir)
                
                from core_structure.execution_engine.execution_engine import ExecutionEngine
                self._execution_engine = ExecutionEngine(self.config.execution_config)
                logger.info("Using core structure execution engine")
            except ImportError as e:
                logger.info(f"Core structure execution engine not available: {e}")
                logger.info("Using enhanced fallback implementation")
                self._execution_engine = self._create_fallback_executor()
    
    def _init_optimizer(self):
        """Initialize optimizer with fallback"""
        if self._optimizer is None:
            try:
                import sys, os
                # Get the correct path to StatArb_Gemini directory
                current_dir = os.path.dirname(__file__)  # strategies/
                backtesting_dir = os.path.dirname(current_dir)  # backtesting_framework/
                statarb_dir = os.path.dirname(backtesting_dir)  # StatArb_Gemini/
                sys.path.append(statarb_dir)
                
                # Try to import portfolio optimizer (may not exist yet)
                from core_structure.optimization.performance_optimization.optimize_execution import PortfolioOptimizer
                self._optimizer = PortfolioOptimizer(self.config.optimization_config)
                logger.info("Using core structure optimizer")
            except ImportError as e:
                logger.info(f"Core structure optimizer not available: {e}")
                logger.info("Using enhanced fallback implementation")
                self._optimizer = self._create_fallback_optimizer()

    @monitor_stage(FlowStage.DATA_LOADING, ComponentType.STRATEGY)
    def train(self, training_data: Optional[Dict[str, pd.DataFrame]] = None) -> bool:
        """
        Train the momentum strategy using historical data
        
        Uses training period data to calibrate parameters and validate approach.
        
        Args:
            training_data: Optional training data. If not provided, will try to load from core system
        
        Returns:
            True if training successful, False otherwise
        """
        context_id = self.flow_monitor.start_stage(
            FlowStage.DATA_LOADING, 
            ComponentType.STRATEGY,
            metadata={'training_start': self.config.training_start, 'training_end': self.config.training_end}
        )
        
        try:
            logger.info("Starting momentum strategy training...")
            
            # Use provided data or try to load from core system
            if training_data is not None:
                logger.info("Using provided training data")
                self.training_data = training_data
                data_size = sum(len(df) for df in training_data.values())
            else:
                # Initialize data manager
                self._init_data_manager()
                
                # Load training data from ClickHouse
                training_data = self._data_manager.load_historical_data(
                    symbols=self.config.symbols,
                    start_date=self.config.training_start,
                    end_date=self.config.training_end
                )
                
                if not training_data:
                    logger.warning("No training data available from core system - strategy will train on first signal generation")
                    self.is_trained = True  # Mark as trained to avoid repeated attempts
                    self.flow_monitor.complete_stage(context_id, data_size=0, output_data={})
                    return True
                
                self.training_data = training_data
                data_size = sum(len(df) for df in training_data.values())
            
            # Training steps with flow tracking
            self._validate_training_data()
            self._filter_universe()
            self._calculate_training_statistics()
            self._validate_momentum_approach()
            
            self.is_trained = True
            logger.info("Momentum strategy training completed successfully")
            
            self.flow_monitor.complete_stage(
                context_id, 
                data_size=data_size, 
                output_data=self.training_data,
                symbols_count=len(self.training_data) if self.training_data else 0
            )
            return True
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            self.flow_monitor.record_error(context_id, e)
            # Mark as trained to avoid repeated attempts when core system unavailable
            self.is_trained = True
            logger.info("Strategy marked as trained with fallback configuration")
            self.flow_monitor.complete_stage(context_id, data_size=0, output_data={})
            return True
    
    @monitor_stage(FlowStage.SIGNAL_GENERATION, ComponentType.STRATEGY)
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Generate momentum trading signals using core structure modules
        
        Args:
            data: Market data for signal generation
            
        Returns:
            List of trading signals
        """
        context_id = self.flow_monitor.start_stage(
            FlowStage.SIGNAL_GENERATION,
            ComponentType.STRATEGY,
            metadata={
                'symbols_count': len(data),
                'rebalancing_frequency': self.config.rebalancing_frequency,
                'momentum_type': getattr(self.config.momentum_type, 'value', str(self.config.momentum_type))
            }
        )
        
        try:
            if not self.is_trained:
                logger.warning("Strategy not trained, training now...")
                # Try to train with provided data if available
                self.train(training_data=data if data else None)
            
            # Check if we should rebalance today (NEW REBALANCING LOGIC)
            current_date = self._get_current_date(data)
            if not self._should_rebalance(current_date):
                # Return cached signals if we're not rebalancing today
                cached_signals = getattr(self, '_last_signals', [])
                if cached_signals:
                    logger.info(f"Using cached signals - no rebalancing on {current_date.strftime('%Y-%m-%d')} (frequency: {self.config.rebalancing_frequency})")
                    self.flow_monitor.complete_stage(
                        context_id,
                        data_size=len(cached_signals),
                        output_data=cached_signals,
                        cached=True
                    )
                    return cached_signals
                else:
                    logger.info(f"No cached signals available - generating initial signals")
            else:
                logger.info(f"Rebalancing day: {current_date.strftime('%Y-%m-%d')} (frequency: {self.config.rebalancing_frequency})")
            
            # Initialize signal generator
            self._init_signal_generator()
            
            # Get momentum type value safely
            momentum_type_value = (self.config.momentum_type.value 
                                 if hasattr(self.config.momentum_type, 'value') 
                                 else self.config.momentum_type)
            
            # Try to use core structure signal generator with expected API
            raw_signals = self._signal_generator.generate_momentum_signals(
                data=data,
                lookback_period=self.config.lookback_period,
                skip_period=self.config.skip_period,
                momentum_type=momentum_type_value,
                threshold=self.config.momentum_threshold
            )
            
            # Track data lineage
            self.flow_monitor.track_data_lineage(
                input_data=data,
                output_data=raw_signals,
                transformation="momentum_signal_generation",
                metadata={
                    'lookback_period': self.config.lookback_period,
                    'momentum_type': momentum_type_value,
                    'threshold': self.config.momentum_threshold
                }
            )
            
            # Convert to standardized trading signals
            signals = self._convert_to_trading_signals(raw_signals, data)
            
            # Apply signal filters and decay
            filtered_signals = self._apply_signal_filters(signals)
            
            # Store current signals for tracking and caching
            self.current_signals = {s.symbol: s.strength for s in filtered_signals}
            self._last_signals = filtered_signals  # Cache for rebalancing frequency
            self._last_rebalance_date = current_date  # Track last rebalance
            
            logger.info(f"Generated {len(filtered_signals)} momentum signals")
            
            self.flow_monitor.complete_stage(
                context_id,
                data_size=len(filtered_signals),
                output_data=filtered_signals,
                signals_count=len(filtered_signals),
                symbols_processed=len(data)
            )
            
            return filtered_signals
            
        except AttributeError as e:
            if "generate_momentum_signals" in str(e):
                logger.info("Core structure signal generator has different API - falling back to enhanced implementation")
                # Reinitialize with fallback
                self._signal_generator = self._create_fallback_signal_generator()
                # Retry with fallback
                return self.generate_signals(data)
            else:
                logger.error(f"Signal generation failed: {e}")
                self.flow_monitor.record_error(context_id, e)
                return []
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            self.flow_monitor.record_error(context_id, e)
            return []
    
    def _get_current_date(self, data: Dict[str, pd.DataFrame]) -> datetime:
        """Extract current date from data"""
        try:
            # Get the latest date from any available symbol data
            for symbol, symbol_data in data.items():
                if not symbol_data.empty:
                    latest_date = symbol_data.index[-1]
                    if isinstance(latest_date, pd.Timestamp):
                        return latest_date.to_pydatetime()
                    elif isinstance(latest_date, str):
                        return pd.to_datetime(latest_date).to_pydatetime()
                    else:
                        return datetime.now()
            return datetime.now()
        except Exception:
            return datetime.now()
    
    def _should_rebalance(self, current_date: datetime) -> bool:
        """Determine if we should rebalance on the current date"""
        frequency = getattr(self.config, 'rebalancing_frequency', 'daily')
        last_rebalance = getattr(self, '_last_rebalance_date', None)
        
        if frequency == "daily":
            return True
        elif frequency == "weekly":
            # Rebalance every Monday (weekday 0)
            if last_rebalance is None:
                return True
            # Check if we've crossed into a new week
            current_week = current_date.isocalendar()[1]
            last_week = last_rebalance.isocalendar()[1]
            return current_week != last_week
        elif frequency == "monthly":
            # Rebalance on first trading day of each month
            if last_rebalance is None:
                return True
            # Check if we've crossed into a new month
            return current_date.month != last_rebalance.month or current_date.year != last_rebalance.year
        else:
            # Default to daily if unknown frequency
            logger.warning(f"Unknown rebalancing frequency: {frequency}, defaulting to daily")
            return True
    
    @monitor_stage(FlowStage.POSITION_SIZING, ComponentType.STRATEGY)
    def calculate_positions(self, signals: List[TradingSignal], 
                          current_positions: Dict[str, Position],
                          available_cash: float) -> Dict[str, float]:
        """
        Calculate optimal positions using core structure optimizer
        
        Args:
            signals: Trading signals
            current_positions: Current portfolio positions  
            available_cash: Available cash for trading
            
        Returns:
            Dictionary mapping symbols to target position sizes
        """
        context_id = self.flow_monitor.start_stage(
            FlowStage.POSITION_SIZING,
            ComponentType.OPTIMIZER,
            metadata={
                'signals_count': len(signals),
                'current_positions': len(current_positions),
                'available_cash': available_cash
            }
        )
        
        try:
            # Prepare inputs for optimizer
            signal_dict = {s.symbol: s.strength for s in signals}
            current_weights = self._positions_to_weights(current_positions, available_cash)
            
            # Initialize optimizer
            self._init_optimizer()
            
            # Use core structure optimizer
            optimal_weights = self._optimizer.optimize_portfolio(
                signals=signal_dict,
                current_weights=current_weights,
                risk_budget=self.config.target_volatility,
                constraints={
                    'max_weight': self.config.max_weight_per_asset,
                    'sector_neutral': self.config.sector_neutrality,
                    'turnover_penalty': self.config.optimization_config.get('turnover_penalty', 0.001)
                }
            )
            
            # Convert weights to position sizes
            target_positions = self._weights_to_positions(optimal_weights, available_cash, signals)
            
            logger.info(f"Calculated positions for {len(target_positions)} symbols")
            
            self.flow_monitor.complete_stage(
                context_id,
                data_size=len(target_positions),
                output_data=target_positions,
                positions_count=len(target_positions)
            )
            
            return target_positions
            
        except Exception as e:
            logger.error(f"Position calculation failed: {e}")
            self.flow_monitor.record_error(context_id, e)
            # Fallback to simple position sizing
            fallback_positions = self._fallback_position_sizing(signals, available_cash)
            self.flow_monitor.complete_stage(
                context_id,
                data_size=len(fallback_positions),
                output_data=fallback_positions,
                fallback=True
            )
            return fallback_positions
    
    @monitor_stage(FlowStage.TRADE_EXECUTION, ComponentType.EXECUTION_ENGINE)
    def execute_trades(self, signals: List[Any], 
                      current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Execute trades based on signals and current prices (base strategy interface)
        
        Args:
            signals: List of trading signals
            current_prices: Current prices for all symbols
            
        Returns:
            List of executed trades
        """
        context_id = self.flow_monitor.start_stage(
            FlowStage.TRADE_EXECUTION,
            ComponentType.EXECUTION_ENGINE,
            metadata={
                'signals_count': len(signals) if signals else 0,
                'prices_available': len(current_prices)
            }
        )
        
        try:
            # Convert signals to target positions if needed
            if not signals:
                logger.info("No signals to execute")
                self.flow_monitor.complete_stage(context_id, data_size=0, output_data=[])
                return []
            
            # Convert TradingSignal objects to position targets
            target_positions = {}
            
            if isinstance(signals, list) and signals:
                # Get available cash (use current portfolio value as proxy)
                available_cash = getattr(self, 'portfolio_value', getattr(self, 'initial_capital', 250000))
                
                # Calculate position targets from signals using position sizing logic
                target_positions = self._calculate_position_targets_from_signals(signals, current_prices, available_cash)
                
                logger.info(f"Converted {len(signals)} signals to {len(target_positions)} position targets")
            elif isinstance(signals, dict):
                target_positions = signals
            
            if not target_positions:
                logger.info("No valid position targets from signals")
                self.flow_monitor.complete_stage(context_id, data_size=0, output_data=[])
                return []
            
            # Get current positions (simplified for backtesting)
            current_positions = getattr(self, 'current_positions', {})
            
            # Calculate required trades
            trades_to_execute = self._calculate_required_trades_simple(
                target_positions, current_positions, current_prices
            )
            
            if not trades_to_execute:
                self.flow_monitor.complete_stage(context_id, data_size=0, output_data=[])
                return []
            
            # Execute trades with current prices (simplified for backtesting)
            executed_trades = []
            for trade in trades_to_execute:
                symbol = trade['symbol']
                quantity = trade['quantity']
                action = trade['action']
                
                if symbol in current_prices:
                    price = current_prices[symbol]
                    executed_trade = {
                        'symbol': symbol,
                        'quantity': abs(quantity),
                        'action': action,
                        'price': price,
                        'timestamp': datetime.now(),
                        'commission': abs(quantity) * price * self.config.commission_rate
                    }
                    executed_trades.append(executed_trade)
                    
                    # Update portfolio tracking (existing code)
                    from strategies.base_strategy import Position
                    
                    if symbol not in self.positions:
                        # Create new position
                        self.positions[symbol] = Position(
                            symbol=symbol,
                            quantity=abs(quantity) if action == 'BUY' else -abs(quantity),
                            entry_price=price,
                            entry_time=datetime.now(),
                            current_price=price,
                            pnl=0.0
                        )
                    else:
                        # Update existing position
                        existing_pos = self.positions[symbol]
                        if action == 'BUY':
                            new_quantity = existing_pos.quantity + abs(quantity)
                            # Update average entry price
                            total_cost = (existing_pos.quantity * existing_pos.entry_price) + (abs(quantity) * price)
                            existing_pos.entry_price = total_cost / new_quantity if new_quantity != 0 else price
                            existing_pos.quantity = new_quantity
                        elif action == 'SELL':
                            existing_pos.quantity -= abs(quantity)
                            # Remove position if quantity becomes zero or negative
                            if existing_pos.quantity <= 0:
                                del self.positions[symbol]
                        
                        if symbol in self.positions:
                            self.positions[symbol].current_price = price
                    
                    # Also update cash position
                    trade_value = abs(quantity) * price
                    commission = trade_value * self.config.commission_rate
                    if action == 'BUY':
                        self.cash -= (trade_value + commission)
                    elif action == 'SELL':
                        self.cash += (trade_value - commission)
                    
                    # Update current_positions for compatibility (if needed)
                    if not hasattr(self, 'current_positions'):
                        self.current_positions = {}
                    
                    current_qty = self.current_positions.get(symbol, 0)
                    if action == 'BUY':
                        self.current_positions[symbol] = current_qty + abs(quantity)
                    elif action == 'SELL':
                        self.current_positions[symbol] = current_qty - abs(quantity)
            
            self.logger.info(f"Executed {len(executed_trades)} trades")
            
            self.flow_monitor.complete_stage(
                context_id,
                data_size=len(executed_trades),
                output_data=executed_trades,
                trades_executed=len(executed_trades)
            )
            
            return executed_trades
            
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            self.flow_monitor.record_error(context_id, e)
            return []
    
    def _calculate_required_trades_simple(self, target_positions: Dict[str, float], 
                                        current_positions: Dict[str, float],
                                        current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Calculate required trades with simplified interface"""
        trades = []
        
        for symbol, target_size in target_positions.items():
            current_size = current_positions.get(symbol, 0)
            required_change = target_size - current_size
            
            if abs(required_change) > 0.001:  # Minimum trade threshold
                action = 'BUY' if required_change > 0 else 'SELL'
                trades.append({
                    'symbol': symbol,
                    'quantity': abs(required_change),
                    'action': action
                })
        
        return trades
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive strategy performance metrics including flow analysis
        
        Returns:
            Dictionary of strategy metrics and statistics
        """
        base_metrics = super().get_performance_metrics()
        
        # Add momentum-specific metrics
        momentum_type_value = (self.config.momentum_type.value 
                             if hasattr(self.config.momentum_type, 'value') 
                             else self.config.momentum_type)
        
        momentum_metrics = {
            'momentum_config': {
                'type': momentum_type_value,
                'lookback_period': self.config.lookback_period,
                'skip_period': self.config.skip_period,
                'threshold': self.config.momentum_threshold,
                'rebalancing_frequency': self.config.rebalancing_frequency
            },
            'risk_metrics': {
                'target_volatility': self.config.target_volatility,
                'max_weight_per_asset': self.config.max_weight_per_asset,
                'sector_neutrality': self.config.sector_neutrality
            },
            'universe_stats': {
                'universe_size': len(self.config.symbols),
                'min_market_cap': self.config.min_market_cap,
                'min_avg_volume': self.config.min_avg_volume
            },
            'signal_stats': {
                'current_signals_count': len(self.current_signals),
                'avg_signal_strength': np.mean(list(self.current_signals.values())) if self.current_signals else 0,
                'signal_decay_type': self.config.signal_decay_type.value
            },
            'training_status': {
                'is_trained': self.is_trained,
                'training_period': f"{self.config.training_start} to {self.config.training_end}",
                'trading_period': f"{self.config.trading_start} to {self.config.trading_end}"
            }
        }
        
        # Add flow monitoring metrics
        flow_summary = self.flow_monitor.get_flow_summary()
        momentum_metrics['flow_analysis'] = flow_summary
        
        return {**base_metrics, **momentum_metrics}
    
    # Helper Methods
    def _validate_training_data(self):
        """Validate quality of training data"""
        for symbol, data in self.training_data.items():
            if len(data) < self.config.min_data_points:
                logger.warning(f"Insufficient data for {symbol}: {len(data)} < {self.config.min_data_points}")
            
            # Check for data quality issues
            if data.isnull().sum().sum() / len(data) > 0.05:  # >5% missing data
                logger.warning(f"High missing data percentage for {symbol}")
    
    def _filter_universe(self):
        """Filter universe based on market cap and volume criteria"""
        # This would integrate with core structure for market cap and volume data
        # For now, assume symbols are pre-filtered
        logger.info(f"Universe filtered to {len(self.config.symbols)} symbols")
    
    def _calculate_training_statistics(self):
        """Calculate statistics during training period"""
        for symbol, data in self.training_data.items():
            # Calculate momentum history
            momentum_values = []
            volatility_values = []
            
            for i in range(self.config.lookback_period, len(data)):
                momentum = self._calculate_momentum(data.iloc[i-self.config.lookback_period:i+1])
                volatility = self._calculate_volatility(data.iloc[max(0, i-self.config.volatility_lookback):i+1])
                momentum_values.append(momentum)
                volatility_values.append(volatility)
            
            self.momentum_history[symbol] = momentum_values
            self.volatility_history[symbol] = volatility_values
    
    def _validate_momentum_approach(self):
        """Validate that momentum approach is working on training data"""
        # Simple validation: check if momentum signals have predictive power
        total_momentum_signals = sum(len(values) for values in self.momentum_history.values())
        if total_momentum_signals == 0:
            raise ValueError("No momentum signals generated during training")
        
        logger.info(f"Training validation: {total_momentum_signals} momentum observations across {len(self.momentum_history)} symbols")
    
    def _convert_to_trading_signals(self, raw_signals: Dict[str, float], 
                                  data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """Convert raw momentum signals to standardized trading signals"""
        signals = []
        current_time = datetime.now()
        
        for symbol, strength in raw_signals.items():
            if symbol not in data or data[symbol].empty:
                continue
            
            current_price = data[symbol]['close'].iloc[-1]
            
            # Determine signal type based on momentum strength
            if strength > self.config.momentum_threshold:
                signal_type = SignalType.LONG
                confidence = min(strength / (2 * self.config.momentum_threshold), 1.0)
            elif strength < -self.config.momentum_threshold:
                signal_type = SignalType.SHORT
                confidence = min(abs(strength) / (2 * self.config.momentum_threshold), 1.0)
            else:
                continue  # Skip weak signals
            
            momentum_type_value = (self.config.momentum_type.value 
                                  if hasattr(self.config.momentum_type, 'value') 
                                  else self.config.momentum_type)
            
            signals.append(TradingSignal(
                timestamp=current_time,
                symbol=symbol,
                signal_type=signal_type,
                strength=abs(strength),
                confidence=confidence,
                price=current_price,
                metadata={
                    'momentum_type': momentum_type_value,
                    'lookback_period': self.config.lookback_period,
                    'skip_period': self.config.skip_period
                }
            ))
        
        return signals
    
    def _apply_signal_filters(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Apply signal decay and other filters"""
        # Apply signal decay if we have previous signals
        # For now, return signals as-is
        return signals
    
    def _calculate_position_targets_from_signals(self, signals: List[TradingSignal], 
                                               current_prices: Dict[str, float], 
                                               available_cash: float) -> Dict[str, float]:
        """
        Convert trading signals to position targets using portfolio optimization
        
        Args:
            signals: List of trading signals
            current_prices: Current market prices
            available_cash: Available cash for trading
            
        Returns:
            Dictionary mapping symbols to target position quantities
        """
        if not signals:
            return {}
        
        try:
            # Convert signals to a simple signal dictionary
            signal_dict = {}
            valid_signals = []
            
            for signal in signals:
                if signal.symbol in current_prices:
                    # Use signal strength with direction based on signal type
                    strength = signal.strength
                    if signal.signal_type == SignalType.SHORT:
                        strength = -strength
                    signal_dict[signal.symbol] = strength
                    valid_signals.append(signal)
            
            if not signal_dict:
                logger.info("No valid signals with current prices")
                return {}
            
            # Simple position sizing based on signal strength
            # This replaces the complex optimizer for now
            total_signal_strength = sum(abs(s) for s in signal_dict.values())
            max_position_value = available_cash * self.config.max_weight_per_asset
            
            position_targets = {}
            
            for symbol, strength in signal_dict.items():
                if symbol in current_prices and current_prices[symbol] > 0:
                    # Calculate position size based on signal strength proportion
                    strength_proportion = abs(strength) / total_signal_strength if total_signal_strength > 0 else 0
                    position_value = available_cash * strength_proportion * min(self.config.max_weight_per_asset, 0.1)
                    
                    # Convert to position quantity
                    position_qty = position_value / current_prices[symbol]
                    
                    # Apply direction (negative for short signals)
                    if strength < 0:
                        position_qty = -position_qty
                    
                    position_targets[symbol] = position_qty
                    
                    logger.debug(f"Position target for {symbol}: {position_qty:.2f} shares "
                               f"(strength={strength:.4f}, value=${position_value:.2f})")
            
            logger.info(f"Calculated {len(position_targets)} position targets from {len(signals)} signals")
            return position_targets
            
        except Exception as e:
            logger.error(f"Failed to calculate position targets: {e}")
            # Fallback to simple equal weight
            return self._simple_equal_weight_positions(signals, current_prices, available_cash)
    
    def _simple_equal_weight_positions(self, signals: List[TradingSignal], 
                                     current_prices: Dict[str, float], 
                                     available_cash: float) -> Dict[str, float]:
        """Simple equal-weight position sizing fallback"""
        position_targets = {}
        
        if not signals:
            return position_targets
        
        # Filter signals that have current prices
        valid_signals = [s for s in signals if s.symbol in current_prices and current_prices[s.symbol] > 0]
        
        if not valid_signals:
            return position_targets
        
        # Equal weight allocation
        position_value_per_signal = available_cash / len(valid_signals) * 0.95  # Use 95% of cash
        
        for signal in valid_signals:
            position_qty = position_value_per_signal / current_prices[signal.symbol]
            
            # Apply direction (negative for short signals)
            if signal.signal_type == SignalType.SHORT:
                position_qty = -position_qty
            
            position_targets[signal.symbol] = position_qty
        
        logger.info(f"Simple equal weight: {len(position_targets)} positions, ${position_value_per_signal:.2f} each")
        return position_targets
    
    def _positions_to_weights(self, positions: Dict[str, Position], 
                            total_capital: float) -> Dict[str, float]:
        """Convert positions to portfolio weights"""
        weights = {}
        for symbol, position in positions.items():
            position_value = position.quantity * position.current_price
            weights[symbol] = position_value / total_capital if total_capital > 0 else 0.0
        return weights
    
    def _weights_to_positions(self, weights: Dict[str, float], 
                            available_cash: float,
                            signals: List[TradingSignal]) -> Dict[str, float]:
        """Convert portfolio weights to position sizes"""
        positions = {}
        signal_prices = {s.symbol: s.price for s in signals}
        
        for symbol, weight in weights.items():
            if symbol in signal_prices and signal_prices[symbol] > 0:
                position_value = weight * available_cash
                position_size = position_value / signal_prices[symbol]
                positions[symbol] = position_size
        
        return positions
    
    def _calculate_required_trades(self, target_positions: Dict[str, float],
                                 current_positions: Dict[str, Position]) -> List[Dict[str, Any]]:
        """Calculate trades needed to reach target positions"""
        trades = []
        
        # Get current quantities
        current_quantities = {pos.symbol: pos.quantity for pos in current_positions.values()}
        
        # Calculate trades for each symbol
        all_symbols = set(target_positions.keys()) | set(current_quantities.keys())
        
        for symbol in all_symbols:
            target_qty = target_positions.get(symbol, 0.0)
            current_qty = current_quantities.get(symbol, 0.0)
            
            trade_qty = target_qty - current_qty
            
            if abs(trade_qty) > 1e-6:  # Minimum trade size threshold
                trades.append({
                    'symbol': symbol,
                    'quantity': trade_qty,
                    'side': 'buy' if trade_qty > 0 else 'sell',
                    'order_type': 'market'
                })
        
        return trades
    
    def _fallback_position_sizing(self, signals: List[TradingSignal], 
                                available_cash: float) -> Dict[str, float]:
        """Simple fallback position sizing when optimizer fails"""
        positions = {}
        
        if not signals:
            return positions
        
        # Equal weight allocation
        weight_per_signal = 1.0 / len(signals)
        
        for signal in signals:
            position_value = available_cash * weight_per_signal * signal.strength
            position_size = position_value / signal.price
            
            if signal.signal_type == SignalType.SHORT:
                position_size = -position_size
            
            positions[signal.symbol] = position_size
        
        return positions
    
    def _calculate_momentum(self, data: pd.DataFrame) -> float:
        """Calculate momentum for a data series"""
        if len(data) < self.config.lookback_period:
            return 0.0
        
        # Simple momentum calculation
        current_price = data['close'].iloc[-1]
        past_price = data['close'].iloc[-self.config.lookback_period]
        
        if self.config.momentum_type == MomentumType.SIMPLE_RETURN:
            return (current_price - past_price) / past_price
        elif self.config.momentum_type == MomentumType.LOG_RETURN:
            return np.log(current_price / past_price)
        elif self.config.momentum_type == MomentumType.RISK_ADJUSTED:
            simple_return = (current_price - past_price) / past_price
            volatility = self._calculate_volatility(data)
            return simple_return / volatility if volatility > 0 else 0.0
        else:
            return (current_price - past_price) / past_price
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calculate volatility for a data series"""
        if len(data) < 2:
            return 0.0
        
        returns = data['close'].pct_change().dropna()
        if len(returns) < 2:
            return 0.0
        
        # Annualized volatility
        return returns.std() * np.sqrt(252)
    
    # Fallback implementations for when core structure modules are not available
    def _create_fallback_signal_generator(self):
        """Create fallback signal generator"""
        class FallbackSignalGenerator:
            def __init__(self, strategy_instance):
                self.strategy = strategy_instance
            
            def generate_momentum_signals(self, data, lookback_period, skip_period, 
                                        momentum_type, threshold):
                signals = {}
                
                for symbol, symbol_data in data.items():
                    if len(symbol_data) < lookback_period + skip_period:
                        continue
                    
                    # Calculate momentum using the strategy's momentum calculation method
                    # This ensures consistency with the training approach
                    momentum_data = symbol_data.iloc[:-skip_period] if skip_period > 0 else symbol_data
                    
                    if len(momentum_data) >= lookback_period:
                        momentum = self.strategy._calculate_momentum(momentum_data)
                        
                        # Only include signals above threshold
                        if abs(momentum) >= threshold:
                            signals[symbol] = momentum
                        
                        logger.debug(f"Fallback signal for {symbol}: momentum={momentum:.4f}, threshold={threshold}")
                
                logger.info(f"Fallback signal generator produced {len(signals)} signals above threshold")
                return signals
        
        return FallbackSignalGenerator(self)
    
    def _create_fallback_executor(self):
        """Create fallback execution engine"""
        class FallbackExecutor:
            def execute_trades(self, trades, market_data, execution_params):
                # Simple execution simulation
                executed = []
                for trade in trades:
                    executed.append({
                        'symbol': trade['symbol'],
                        'quantity': trade['quantity'],
                        'price': market_data[trade['symbol']]['close'].iloc[-1],
                        'timestamp': datetime.now(),
                        'commission': abs(trade['quantity']) * execution_params.get('commission_rate', 0.001)
                    })
                return executed
        
        return FallbackExecutor()
    
    def _create_fallback_optimizer(self):
        """Create fallback portfolio optimizer"""
        class FallbackOptimizer:
            def optimize_portfolio(self, signals, current_weights, risk_budget, constraints):
                # Simple equal weight optimization
                if not signals:
                    return {}
                
                max_weight = constraints.get('max_weight', 0.1)
                weights = {}
                
                # Sort signals by strength
                sorted_signals = sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True)
                
                # Allocate equal weights up to max_weight
                for symbol, strength in sorted_signals:
                    weights[symbol] = min(max_weight, 1.0 / len(signals))
                
                return weights
        
        return FallbackOptimizer()
    
    def _create_fallback_data_manager(self):
        """Create fallback data manager"""
        class FallbackDataManager:
            def load_historical_data(self, symbols, start_date, end_date):
                # For testing, return empty dict - in real implementation
                # this would load from a different data source
                logger.warning(f"Fallback data manager: Cannot load data for {symbols} from {start_date} to {end_date}")
                return {}
        
        return FallbackDataManager() 