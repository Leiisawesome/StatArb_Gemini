"""
Professional Pair Trading Strategy with Advanced Components
Integrates execution quality, portfolio management, and advanced signal generation.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta

from ..models.kalman_filter import AdvancedKalmanFilter
from ..models.cointegration import CointegrationTester
from ..risk_management import RiskManager
from ..execution import (
    OrderManager, PositionManager, MarketImpactModel, 
    SlippageModel, TransactionCostOptimizer
)
from ..portfolio import PortfolioOptimizer, PairInfo
from ..signals import AdvancedSignalGenerator
from ..utils.data_loader import DataLoader
from ..utils.validation import validate_data

logger = logging.getLogger(__name__)

class ProfessionalPairTradingStrategy:
    """
    Professional pair trading strategy with institutional-grade components.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol1 = config.get('symbol1', 'AAPL')
        self.symbol2 = config.get('symbol2', 'MSFT')
        self.lookback_period = config.get('lookback_period', 252)
        self.entry_threshold = config.get('entry_threshold', 2.0)
        self.exit_threshold = config.get('exit_threshold', 0.5)
        self.stop_loss = config.get('stop_loss', 0.05)
        self.take_profit = config.get('take_profit', 0.10)
        
        # Initialize components
        self.data_loader = DataLoader()
        self.kalman_filter = AdvancedKalmanFilter()
        self.cointegration_tester = CointegrationTester()
        self.risk_manager = RiskManager(config.get('risk_config', {}))
        
        # Advanced execution components
        self.order_manager = OrderManager(config.get('initial_capital', 1000000))
        self.position_manager = PositionManager(self.order_manager)
        self.market_impact_model = MarketImpactModel()
        self.slippage_model = SlippageModel()
        self.cost_optimizer = TransactionCostOptimizer(
            self.market_impact_model, self.slippage_model
        )
        
        # Portfolio management
        self.portfolio_optimizer = PortfolioOptimizer()
        
        # Advanced signal generation
        self.signal_generator = AdvancedSignalGenerator()
        
        # Strategy state
        self.current_position = 0
        self.entry_price = 0.0
        self.hedge_ratio = 1.0
        self.spread_mean = 0.0
        self.spread_std = 1.0
        self.is_cointegrated = False
        self.last_signal = 0.0
        
        # Performance tracking
        self.trades = []
        self.daily_returns = []
        self.performance_metrics = {}
        
        logger.info(f"Initialized professional pair trading strategy for {self.symbol1}-{self.symbol2}")
    
    def prepare_data(self, start_date: str, end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare and validate data for the strategy.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Tuple of (price_data, volume_data)
        """
        # Load data
        price_data = self.data_loader.load_data(
            [self.symbol1, self.symbol2], 
            start_date, 
            end_date,
            data_type='price'
        )
        
        volume_data = self.data_loader.load_data(
            [self.symbol1, self.symbol2],
            start_date,
            end_date,
            data_type='volume'
        )
        
        # Validate data
        if not validate_data(price_data):
            raise ValueError("Invalid price data")
        
        # Align data
        common_index = price_data.index.intersection(volume_data.index)
        price_data = price_data.loc[common_index]
        volume_data = volume_data.loc[common_index]
        
        logger.info(f"Prepared data: {len(price_data)} observations")
        return price_data, volume_data
    
    def initialize_strategy(self, price_data: pd.DataFrame, volume_data: pd.DataFrame):
        """
        Initialize strategy components with historical data.
        
        Args:
            price_data: Historical price data
            volume_data: Historical volume data
        """
        # Test cointegration
        self.is_cointegrated = self.cointegration_tester.test_cointegration(
            price_data[self.symbol1], price_data[self.symbol2]
        )
        
        if not self.is_cointegrated:
            logger.warning("Symbols are not cointegrated - strategy may not perform well")
        
        # Initialize Kalman filter
        self.kalman_filter.initialize(
            price_data[self.symbol1], price_data[self.symbol2]
        )
        
        # Calculate initial hedge ratio and spread statistics
        self._calculate_spread_statistics(price_data)
        
        # Initialize portfolio optimizer
        self._initialize_portfolio_optimizer(price_data, volume_data)
        
        # Initialize advanced signal generator
        self._initialize_signal_generator(price_data, volume_data)
        
        # Set position limits
        self._set_position_limits(price_data)
        
        logger.info("Strategy initialization completed")
    
    def _calculate_spread_statistics(self, price_data: pd.DataFrame):
        """Calculate spread statistics for the pair."""
        # Calculate spread using Kalman filter
        spread = self.kalman_filter.calculate_spread(
            price_data[self.symbol1], price_data[self.symbol2]
        )
        
        # Calculate statistics
        self.spread_mean = spread.mean()
        self.spread_std = spread.std()
        self.hedge_ratio = self.kalman_filter.get_hedge_ratio()
        
        logger.info(f"Spread stats - Mean: {self.spread_mean:.4f}, Std: {self.spread_std:.4f}")
        logger.info(f"Hedge ratio: {self.hedge_ratio:.4f}")
    
    def _initialize_portfolio_optimizer(self, price_data: pd.DataFrame, volume_data: pd.DataFrame):
        """Initialize portfolio optimizer with pair information."""
        # Create pair info
        returns = price_data.pct_change().dropna()
        pair_info = PairInfo(
            symbol1=self.symbol1,
            symbol2=self.symbol2,
            hedge_ratio=self.hedge_ratio,
            spread_volatility=float(returns[self.symbol1].std()),
            correlation=float(returns[self.symbol1].corr(returns[self.symbol2])),
            signal_strength=0.0,  # Will be updated dynamically
            current_spread=0.0,   # Will be updated dynamically
            z_score=0.0,          # Will be updated dynamically
            last_update=pd.Timestamp.now()
        )
        
        # Add pair to optimizer
        self.portfolio_optimizer.add_pair(f"{self.symbol1}_{self.symbol2}", pair_info)
        
        # Update correlation matrix and volatility estimates
        self.portfolio_optimizer.calculate_correlation_matrix(returns)
        volatility_estimates = {
            self.symbol1: float(returns[self.symbol1].std() * np.sqrt(252)),
            self.symbol2: float(returns[self.symbol2].std() * np.sqrt(252))
        }
        self.portfolio_optimizer.update_volatility_estimates(volatility_estimates)
    
    def _initialize_signal_generator(self, price_data: pd.DataFrame, volume_data: pd.DataFrame):
        """Initialize advanced signal generator."""
        # Train ML models if sufficient data
        if len(price_data) > 100:
            try:
                # Extract features
                features = self.signal_generator.ml_enhancer.extract_features(
                    price_data[self.symbol1], volume_data[self.symbol1]
                )
                
                # Create targets (simplified - could be more sophisticated)
                targets = (price_data[self.symbol1].pct_change() > 0).astype(int)
                
                # Train models
                self.signal_generator.ml_enhancer.train_models(
                    features, targets, target_type='classification'
                )
                
                logger.info("ML models trained successfully")
            except Exception as e:
                logger.warning(f"ML model training failed: {str(e)}")
    
    def _set_position_limits(self, price_data: pd.DataFrame):
        """Set position limits based on data characteristics."""
        avg_price = price_data.mean()
        daily_volume = price_data.mean() * 0.01  # Estimate daily volume
        
        # Set position limits (10% of average daily volume)
        max_position_size = daily_volume * 0.1
        
        self.position_manager.set_position_limit(self.symbol1, max_position_size[self.symbol1])
        self.position_manager.set_position_limit(self.symbol2, max_position_size[self.symbol2])
        
        logger.info(f"Position limits set: {self.symbol1}: ${max_position_size[self.symbol1]:.2f}, "
                   f"{self.symbol2}: ${max_position_size[self.symbol2]:.2f}")
    
    def generate_signals(self, 
                        price_data: pd.DataFrame, 
                        volume_data: pd.DataFrame,
                        current_date: pd.Timestamp) -> Dict[str, Any]:
        """
        Generate comprehensive trading signals.
        
        Args:
            price_data: Current price data
            volume_data: Current volume data
            current_date: Current trading date
            
        Returns:
            Signal analysis
        """
        # Get current prices
        current_price1 = price_data[self.symbol1].iloc[-1]
        current_price2 = price_data[self.symbol2].iloc[-1]
        
        # Update Kalman filter
        self.kalman_filter.update(current_price1, current_price2)
        
        # Calculate current spread and z-score
        current_spread = self.kalman_filter.calculate_spread(
            pd.Series([current_price1]), pd.Series([current_price2])
        ).iloc[-1]
        
        z_score = (current_spread - self.spread_mean) / self.spread_std
        
        # Generate advanced signals
        advanced_signals = self.signal_generator.generate_advanced_signals(
            price_data[self.symbol1],
            volume_data[self.symbol1] if volume_data is not None else None
        )
        
        # Combine signals
        base_signal = self._calculate_base_signal(z_score)
        advanced_signal = advanced_signals['combined_signal']
        
        # Weighted combination
        final_signal = 0.7 * base_signal + 0.3 * advanced_signal
        
        # Update portfolio optimizer
        self._update_portfolio_optimizer(current_spread, z_score, final_signal)
        
        # Generate execution signals
        execution_signals = self._generate_execution_signals(
            final_signal, current_price1, current_price2, volume_data
        )
        
        return {
            'base_signal': base_signal,
            'advanced_signal': advanced_signal,
            'final_signal': final_signal,
            'z_score': z_score,
            'current_spread': current_spread,
            'regime': advanced_signals['regime'],
            'execution_signals': execution_signals,
            'confidence': advanced_signals['signal_confidence']
        }
    
    def _calculate_base_signal(self, z_score: float) -> float:
        """Calculate base signal from z-score."""
        if z_score > self.entry_threshold:
            return -1.0  # Short signal
        elif z_score < -self.entry_threshold:
            return 1.0   # Long signal
        elif abs(z_score) < self.exit_threshold:
            return 0.0   # Exit signal
        else:
            return 0.0   # Hold
    
    def _update_portfolio_optimizer(self, current_spread: float, z_score: float, signal: float):
        """Update portfolio optimizer with current information."""
        pair_id = f"{self.symbol1}_{self.symbol2}"
        
        updates = {
            'signal_strength': signal,
            'current_spread': current_spread,
            'z_score': z_score,
            'last_update': pd.Timestamp.now()
        }
        
        self.portfolio_optimizer.update_pair_info(pair_id, updates)
    
    def _generate_execution_signals(self, 
                                  signal: float, 
                                  price1: float, 
                                  price2: float,
                                  volume_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate execution-specific signals."""
        if abs(signal) < 0.1:  # Weak signal
            return {'execute': False, 'reason': 'Weak signal'}
        
        # Calculate optimal position size
        optimal_size = self.position_manager.calculate_optimal_position_size(
            self.symbol1, signal, price1
        )
        
        # Calculate transaction costs
        avg_volume1 = volume_data[self.symbol1].rolling(20).mean().iloc[-1]
        avg_volume2 = volume_data[self.symbol2].rolling(20).mean().iloc[-1]
        
        # Estimate volatility and spread
        volatility1 = volume_data[self.symbol1].pct_change().std() * np.sqrt(252)
        spread1 = 0.001  # 10bp estimate
        
        # Optimize order size
        optimization = self.cost_optimizer.optimize_order_size(
            target_notional=optimal_size * price1,
            current_price=price1,
            avg_volume=avg_volume1,
            volatility=volatility1,
            spread=spread1
        )
        
        # Calculate timing
        timing = self.cost_optimizer.calculate_optimal_timing(
            optimization['optimal_order_size'],
            avg_volume1,
            volatility1,
            spread1
        )
        
        return {
            'execute': True,
            'optimal_size': optimization['optimal_order_size'],
            'transaction_cost_bps': optimization['min_total_cost_bps'],
            'timing': timing['recommended_timing'],
            'estimated_duration': timing['estimated_duration_minutes']
        }
    
    def execute_trades(self, signals: Dict[str, Any], current_prices: Dict[str, float]):
        """
        Execute trades based on signals.
        
        Args:
            signals: Trading signals
            current_prices: Current market prices
        """
        if not signals['execution_signals']['execute']:
            return
        
        signal = signals['final_signal']
        optimal_size = signals['execution_signals']['optimal_size']
        
        # Check risk limits
        if not self.risk_manager.check_position_limits(optimal_size, current_prices):
            logger.warning("Position limit exceeded")
            return
        
        # Generate orders
        orders = []
        
        if signal > 0:  # Long signal
            # Buy symbol1, sell symbol2
            order1 = self._create_order(
                self.symbol1, 'buy', optimal_size, current_prices[self.symbol1]
            )
            order2 = self._create_order(
                self.symbol2, 'sell', optimal_size * self.hedge_ratio, current_prices[self.symbol2]
            )
            orders = [order1, order2]
            
        elif signal < 0:  # Short signal
            # Sell symbol1, buy symbol2
            order1 = self._create_order(
                self.symbol1, 'sell', optimal_size, current_prices[self.symbol1]
            )
            order2 = self._create_order(
                self.symbol2, 'buy', optimal_size * self.hedge_ratio, current_prices[self.symbol2]
            )
            orders = [order1, order2]
        
        # Submit orders
        for order in orders:
            order_id = self.order_manager.submit_order(order)
            logger.info(f"Submitted order {order_id}: {order.side.value} {order.quantity} {order.symbol}")
    
    def _create_order(self, symbol: str, side: str, quantity: float, price: float):
        """Create an order object."""
        from ..execution import Order, OrderSide, OrderType
        
        return Order(
            order_id=f"{symbol}_{side}_{datetime.now().timestamp()}",
            symbol=symbol,
            side=OrderSide.BUY if side == 'buy' else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=price,
            parent_strategy="professional_pair_trading"
        )
    
    def update_positions(self, current_prices: Dict[str, float]):
        """Update position P&L and risk metrics."""
        # Update position prices
        self.order_manager.update_position_prices(current_prices)
        
        # Update risk metrics
        self.risk_manager.update_risk_metrics(
            self.order_manager.get_portfolio_summary()
        )
        
        # Check risk limits
        if self.risk_manager.check_risk_limits():
            logger.warning("Risk limits exceeded - consider reducing positions")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        portfolio_summary = self.order_manager.get_portfolio_summary()
        risk_metrics = self.risk_manager.get_risk_metrics()
        
        # Calculate strategy-specific metrics
        strategy_metrics = {
            'total_trades': len(self.order_manager.trade_history),
            'win_rate': self._calculate_win_rate(),
            'avg_trade_pnl': self._calculate_avg_trade_pnl(),
            'max_drawdown': portfolio_summary['drawdown'],
            'sharpe_ratio': portfolio_summary['portfolio_return'] / portfolio_summary.get('portfolio_volatility', 0.01),
            'current_position': self.current_position,
            'hedge_ratio': self.hedge_ratio,
            'is_cointegrated': self.is_cointegrated
        }
        
        return {
            'portfolio_summary': portfolio_summary,
            'risk_metrics': risk_metrics,
            'strategy_metrics': strategy_metrics,
            'last_signal': self.last_signal
        }
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trade history."""
        if not self.order_manager.trade_history:
            return 0.0
        
        winning_trades = sum(1 for trade in self.order_manager.trade_history 
                           if trade.get('pnl', 0) > 0)
        return winning_trades / len(self.order_manager.trade_history)
    
    def _calculate_avg_trade_pnl(self) -> float:
        """Calculate average trade P&L."""
        if not self.order_manager.trade_history:
            return 0.0
        
        total_pnl = sum(trade.get('pnl', 0) for trade in self.order_manager.trade_history)
        return total_pnl / len(self.order_manager.trade_history)
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Run comprehensive backtest with all advanced components.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Backtest results
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Prepare data
        price_data, volume_data = self.prepare_data(start_date, end_date)
        
        # Initialize strategy
        self.initialize_strategy(price_data, volume_data)
        
        # Run backtest
        results = []
        
        for i in range(self.lookback_period, len(price_data)):
            current_date = price_data.index[i]
            current_prices = price_data.iloc[i].to_dict()
            
            # Get historical data for signal generation
            hist_prices = price_data.iloc[i-self.lookback_period:i+1]
            hist_volumes = volume_data.iloc[i-self.lookback_period:i+1]
            
            # Generate signals
            signals = self.generate_signals(hist_prices, hist_volumes, current_date)
            
            # Execute trades
            self.execute_trades(signals, current_prices)
            
            # Update positions
            self.update_positions(current_prices)
            
            # Record results
            results.append({
                'date': current_date,
                'signal': signals['final_signal'],
                'z_score': signals['z_score'],
                'portfolio_value': self.order_manager.get_portfolio_summary()['total_market_value'],
                'regime': signals['regime'].regime_type
            })
        
        # Calculate final performance
        performance = self.get_performance_summary()
        
        logger.info("Backtest completed")
        return {
            'performance': performance,
            'results': pd.DataFrame(results),
            'trades': self.order_manager.trade_history
        } 