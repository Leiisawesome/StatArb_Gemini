"""
Core Engine - Standalone Trading System

A complete institutional-grade trading engine with no external dependencies.
Designed for mean reversion, momentum, and pairs trading strategies.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

from .types import (
    # Portfolio
    Portfolio, PortfolioManager, PortfolioConfig,
    
    # Strategy
    BaseStrategy, StrategyManager, StrategyConfig, StrategyType, TradingSignal,
    
    # Risk
    RiskManager, RiskConfig, RiskResult,
    
    # Data
    DataManager, DataConfig,
    
    # Orders & Execution
    Order, OrderType, OrderSide, ExecutionResult,
    
    # Broker
    BrokerManager, PaperBroker, BrokerConfig, BrokerType,
    
    # Analytics
    AnalyticsEngine, PerformanceMetrics,
    
    # Regime
    RegimeEngine, RegimeConfig, RegimeState
)

logger = logging.getLogger(__name__)


class CoreEngine:
    """
    Complete standalone trading engine
    
    Features:
    - Portfolio management with risk controls
    - Strategy management and signal generation
    - Order execution and broker integration
    - Performance analytics and reporting
    - Market regime detection
    - Paper trading support
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize core engine with configuration"""
        self.config = config or {}
        
        # Core components
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.strategy_manager: Optional[StrategyManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.data_manager: Optional[DataManager] = None
        self.broker_manager: Optional[BrokerManager] = None
        self.analytics_engine: Optional[AnalyticsEngine] = None
        self.regime_engine: Optional[RegimeEngine] = None
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.last_update = None
        
    def initialize(self) -> bool:
        """Initialize all engine components"""
        try:
            logger.info("🚀 Initializing Core Engine...")
            
            # Initialize portfolio management
            portfolio_config = PortfolioConfig(
                initial_cash=self.config.get('initial_cash', 100000.0),
                commission_rate=self.config.get('commission_rate', 0.001),
                max_position_size=self.config.get('max_position_size', 0.1)
            )
            self.portfolio_manager = PortfolioManager(portfolio_config)
            
            # Initialize risk management
            risk_config = RiskConfig(
                max_portfolio_risk=self.config.get('max_portfolio_risk', 0.02),
                max_position_size=self.config.get('max_position_size', 0.1),
                daily_loss_limit=self.config.get('daily_loss_limit', 0.03)
            )
            self.risk_manager = RiskManager(risk_config)
            
            # Initialize data management
            data_config = DataConfig(
                provider=self.config.get('data_provider', 'yahoo'),
                cache_enabled=self.config.get('cache_enabled', True)
            )
            self.data_manager = DataManager(data_config)
            
            # Initialize broker management
            self.broker_manager = BrokerManager()
            
            # Add paper broker by default
            paper_config = BrokerConfig(
                broker_type=BrokerType.PAPER,
                default_commission=self.config.get('commission_rate', 0.001)
            )
            paper_broker = PaperBroker(paper_config)
            paper_broker.set_cash(self.config.get('initial_cash', 100000.0))
            self.broker_manager.add_broker("paper", paper_broker, set_as_default=True)
            
            # Initialize strategy management
            self.strategy_manager = StrategyManager()
            
            # Initialize analytics
            self.analytics_engine = AnalyticsEngine()
            
            # Initialize regime detection
            regime_config = RegimeConfig(
                lookback_window=self.config.get('regime_lookback', 20),
                volatility_threshold=self.config.get('volatility_threshold', 0.02)
            )
            self.regime_engine = RegimeEngine(regime_config)
            
            # Connect brokers
            self.broker_manager.connect_all()
            
            self.is_initialized = True
            logger.info("✅ Core Engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Core Engine: {e}")
            return False
    
    def add_strategy(self, strategy: BaseStrategy):
        """Add strategy to the engine"""
        if not self.is_initialized:
            raise RuntimeError("Engine must be initialized before adding strategies")
        
        self.strategy_manager.register_strategy(strategy)
        logger.info(f"✅ Added strategy: {strategy.strategy_id}")
    
    def run_backtest(self, symbols: List[str], start_date: datetime, 
                    end_date: datetime) -> PerformanceMetrics:
        """Run backtest on historical data"""
        if not self.is_initialized:
            raise RuntimeError("Engine must be initialized before running backtest")
        
        logger.info(f"🔄 Starting backtest: {symbols} from {start_date} to {end_date}")
        
        # Get historical data
        data_frames = {}
        for symbol in symbols:
            data_frames[symbol] = self.data_manager.get_data(symbol, start_date, end_date)
        
        # Combine data if multiple symbols
        if len(symbols) == 1:
            market_data = data_frames[symbols[0]]
        else:
            # For multiple symbols, use the first one as primary
            market_data = data_frames[symbols[0]]
        
        if market_data.empty:
            logger.warning("No market data available for backtest")
            return PerformanceMetrics()
        
        # Reset portfolio for backtest
        self.portfolio_manager.portfolio.cash = self.portfolio_manager.config.initial_cash
        self.portfolio_manager.portfolio.positions.clear()
        
        # Track performance
        initial_value = self.portfolio_manager.portfolio.total_value
        
        # Run backtest day by day
        for date in market_data.index:
            try:
                # Get current market data slice
                current_data = market_data.loc[:date]
                
                # Update market prices
                current_prices = {}
                for symbol in symbols:
                    if symbol in data_frames and date in data_frames[symbol].index:
                        current_prices[symbol] = data_frames[symbol].loc[date, 'Close']
                
                self.portfolio_manager.portfolio.update_market_prices(current_prices)
                
                # Update regime
                regime_signal = self.regime_engine.detect_regime(current_data)
                
                # Update strategies
                self.strategy_manager.update_all_strategies(current_data)
                
                # Generate signals
                signals = self.strategy_manager.generate_all_signals(current_data)
                
                # Process signals
                for signal in signals:
                    if signal.symbol in current_prices:
                        self._process_signal(signal, current_prices[signal.symbol])
                
                # Update analytics
                portfolio_value = self.portfolio_manager.portfolio.total_value
                self.analytics_engine.add_portfolio_snapshot(
                    date, portfolio_value, 
                    {k: v.quantity for k, v in self.portfolio_manager.portfolio.positions.items()},
                    self.portfolio_manager.portfolio.cash
                )
                
            except Exception as e:
                logger.warning(f"Error processing date {date}: {e}")
                continue
        
        # Calculate final performance
        final_value = self.portfolio_manager.portfolio.total_value
        total_return = (final_value - initial_value) / initial_value
        
        logger.info(f"✅ Backtest completed. Return: {total_return:.2%}")
        
        return self.analytics_engine.calculate_performance(start_date, end_date)
    
    def _process_signal(self, signal: TradingSignal, current_price: float):
        """Process trading signal"""
        try:
            # Risk check
            current_position = self.portfolio_manager.get_position_size(signal.symbol)
            portfolio_value = self.portfolio_manager.portfolio.total_value
            
            # Calculate target quantity based on signal
            if signal.is_buy:
                # Buy signal - calculate position size
                target_value = portfolio_value * 0.05  # 5% position size
                quantity = target_value / current_price
            elif signal.is_sell:
                # Sell signal - close position
                quantity = -current_position
            else:
                return  # Hold signal
            
            if abs(quantity) < 1e-6:
                return  # No meaningful trade
            
            # Risk check
            risk_result = self.risk_manager.check_trade_risk(
                signal.symbol, quantity, current_price, portfolio_value, current_position
            )
            
            if not risk_result.approved:
                logger.warning(f"Trade rejected by risk manager: {risk_result.reasons}")
                return
            
            # Use adjusted quantity if provided
            if risk_result.adjusted_quantity is not None:
                quantity = risk_result.adjusted_quantity
            
            # Execute trade
            success = self.portfolio_manager.execute_trade(signal.symbol, quantity, current_price)
            
            if success:
                # Record trade
                side = "BUY" if quantity > 0 else "SELL"
                commission = abs(quantity * current_price) * self.portfolio_manager.config.commission_rate
                
                self.analytics_engine.add_trade(
                    datetime.now(), signal.symbol, side, 
                    abs(quantity), current_price, commission
                )
                
                logger.debug(f"✅ Executed: {side} {abs(quantity):.2f} {signal.symbol} @ ${current_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get current portfolio summary"""
        if not self.portfolio_manager:
            return {}
        
        snapshot = self.portfolio_manager.portfolio.get_snapshot()
        
        return {
            'total_value': snapshot.total_value,
            'cash': snapshot.cash,
            'positions': len(snapshot.positions),
            'unrealized_pnl': snapshot.unrealized_pnl,
            'timestamp': snapshot.timestamp
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.analytics_engine:
            return {}
        
        metrics = self.analytics_engine.calculate_performance()
        
        return {
            'total_return': metrics.total_return,
            'sharpe_ratio': metrics.sharpe_ratio,
            'max_drawdown': metrics.max_drawdown,
            'total_trades': metrics.total_trades,
            'win_rate': metrics.win_rate
        }
    
    def shutdown(self):
        """Shutdown engine and cleanup resources"""
        logger.info("🔄 Shutting down Core Engine...")
        
        if self.broker_manager:
            self.broker_manager.disconnect_all()
        
        self.is_running = False
        logger.info("✅ Core Engine shutdown complete")


# Export main class
__all__ = ['CoreEngine']