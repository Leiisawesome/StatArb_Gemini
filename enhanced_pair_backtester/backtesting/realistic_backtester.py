"""
Realistic Backtesting Framework with Transaction Costs, Slippage, and Market Impact
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# Import our components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock classes for components that may not exist
class RegimeDetector:
    def __init__(self):
        self.current_regime = 'normal'
    
    def detect_regime(self, data):
        return {'current_regime': 'normal', 'confidence': 0.8}

class AdvancedPositionSizer:
    def __init__(self):
        pass

class RiskManager:
    def __init__(self):
        pass
    
    def calculate_portfolio_risk(self, positions, prices, volatilities):
        return {'total_var': 0.03}

class LiquidityTimingAnalyzer:
    def __init__(self):
        pass
    
    def get_execution_timing_score(self, timestamp):
        # Simple time-based scoring
        hour = timestamp.hour
        if 10 <= hour <= 15:
            return 0.8
        else:
            return 0.6

class AdvancedExecutor:
    def __init__(self):
        pass

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class Order:
    """Represents a trading order with realistic execution characteristics"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0

@dataclass
class Trade:
    """Represents a completed trade"""
    id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    commission: float
    slippage: float
    market_impact: float
    total_cost: float

@dataclass
class MarketData:
    """Realistic market data with microstructure details"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    mid: float
    volume: float
    bid_size: float
    ask_size: float
    last_price: float
    volatility: float
    
    @property
    def spread(self) -> float:
        return self.ask - self.bid
    
    @property
    def spread_bps(self) -> float:
        return (self.spread / self.mid) * 10000

class RealisticMarketSimulator:
    """Simulates realistic market conditions with microstructure effects"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Market microstructure parameters
        self.base_spreads = {
            'SPY': 0.01, 'QQQ': 0.01, 'IWM': 0.02,
            'TLT': 0.02, 'TMF': 0.05, 'TQQQ': 0.03,
            'UPRO': 0.03, 'TNA': 0.05, 'SOXL': 0.08
        }
        
        # Market impact parameters (basis points per $1M notional)
        self.impact_coefficients = {
            'SPY': 0.5, 'QQQ': 0.6, 'IWM': 1.2,
            'TLT': 0.8, 'TMF': 2.5, 'TQQQ': 1.8,
            'UPRO': 1.5, 'TNA': 2.0, 'SOXL': 3.0
        }
        
        # Liquidity parameters
        self.avg_daily_volumes = {
            'SPY': 50_000_000, 'QQQ': 30_000_000, 'IWM': 20_000_000,
            'TLT': 8_000_000, 'TMF': 2_000_000, 'TQQQ': 15_000_000,
            'UPRO': 5_000_000, 'TNA': 3_000_000, 'SOXL': 8_000_000
        }
        
    def generate_market_data(self, symbol: str, base_price: float, 
                           volatility: float, timestamp: datetime) -> MarketData:
        """Generate realistic market data with bid-ask spreads"""
        
        # Base spread with volatility adjustment
        base_spread = self.base_spreads.get(symbol, 0.02)
        vol_adjustment = 1 + (volatility - 0.2) * 2  # Spreads widen with volatility
        spread = base_spread * vol_adjustment
        
        # Time-of-day spread adjustment
        hour = timestamp.hour
        if hour < 10 or hour > 15:  # Market open/close
            spread *= 1.5
        elif 11 <= hour <= 14:  # Midday
            spread *= 0.8
            
        # Generate bid-ask around mid price
        mid_price = base_price
        half_spread = spread / 2
        bid = mid_price - half_spread
        ask = mid_price + half_spread
        
        # Volume simulation
        base_volume = self.avg_daily_volumes.get(symbol, 1_000_000) / 390  # Per minute
        volume_multiplier = np.random.lognormal(0, 0.5)
        volume = base_volume * volume_multiplier
        
        # Bid/ask sizes
        bid_size = np.random.exponential(1000)
        ask_size = np.random.exponential(1000)
        
        return MarketData(
            timestamp=timestamp,
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=mid_price,
            volume=volume,
            bid_size=bid_size,
            ask_size=ask_size,
            last_price=mid_price,
            volatility=volatility
        )
    
    def calculate_market_impact(self, symbol: str, quantity: float, 
                              price: float, market_data: MarketData) -> float:
        """Calculate market impact based on order size and liquidity"""
        
        notional = abs(quantity * price)
        impact_coeff = self.impact_coefficients.get(symbol, 1.0)
        
        # Square root impact model
        impact_bps = impact_coeff * np.sqrt(notional / 1_000_000)
        
        # Liquidity adjustment
        participation_rate = abs(quantity) / market_data.volume
        if participation_rate > 0.1:  # High participation increases impact
            impact_bps *= (1 + participation_rate * 5)
            
        # Volatility adjustment
        vol_mult = 1 + (market_data.volatility - 0.2) * 2
        impact_bps *= vol_mult
        
        return impact_bps / 10000  # Convert to decimal

class RealisticExecutionEngine:
    """Realistic order execution with slippage and market impact"""
    
    def __init__(self, market_simulator: RealisticMarketSimulator):
        self.market_simulator = market_simulator
        self.logger = logging.getLogger(__name__)
        
        # Commission structure (per share)
        self.commission_per_share = 0.005  # $0.005 per share
        self.min_commission = 1.0  # Minimum $1 per trade
        
    def execute_order(self, order: Order, market_data: MarketData) -> List[Trade]:
        """Execute order with realistic slippage and market impact"""
        
        trades = []
        
        if order.status != OrderStatus.PENDING:
            return trades
            
        # Calculate market impact
        market_impact = self.market_simulator.calculate_market_impact(
            order.symbol, order.quantity, market_data.mid, market_data
        )
        
        # Determine execution price based on order type
        if order.order_type == OrderType.MARKET:
            if order.side == 'buy':
                base_price = market_data.ask
                # Add market impact (adverse selection)
                execution_price = base_price * (1 + market_impact)
            else:
                base_price = market_data.bid
                # Subtract market impact (adverse selection)
                execution_price = base_price * (1 - market_impact)
                
        elif order.order_type == OrderType.LIMIT:
            # Limit orders may not fill immediately
            if order.price is not None:
                if order.side == 'buy' and order.price >= market_data.ask:
                    execution_price = min(order.price, market_data.ask)
                elif order.side == 'sell' and order.price <= market_data.bid:
                    execution_price = max(order.price, market_data.bid)
                else:
                    # Order doesn't fill
                    return trades
            else:
                # No price specified for limit order
                return trades
        else:
            # Stop orders not implemented for simplicity
            return trades
            
        # Calculate slippage (difference from mid price)
        slippage = abs(execution_price - market_data.mid) / market_data.mid
        
        # Calculate commission
        commission = max(self.min_commission, 
                        abs(order.quantity) * self.commission_per_share)
        
        # Create trade
        trade = Trade(
            id=f"trade_{order.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            timestamp=market_data.timestamp,
            commission=commission,
            slippage=slippage,
            market_impact=market_impact,
            total_cost=commission + abs(order.quantity * execution_price * market_impact)
        )
        
        trades.append(trade)
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = execution_price
        order.commission = commission
        order.slippage = slippage
        order.market_impact = market_impact
        
        return trades

class RealisticBacktester:
    """Comprehensive backtesting framework with realistic market simulation"""
    
    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # symbol -> quantity
        self.cash = initial_capital
        
        # Components
        self.market_simulator = RealisticMarketSimulator()
        self.execution_engine = RealisticExecutionEngine(self.market_simulator)
        self.regime_detector = RegimeDetector()
        self.position_sizer = AdvancedPositionSizer()
        self.risk_manager = RiskManager()
        self.liquidity_analyzer = LiquidityTimingAnalyzer()
        
        # Tracking
        self.orders = []
        self.trades = []
        self.portfolio_history = []
        self.performance_metrics = {}
        
        # Market data cache
        self.market_data_cache = {}
        
        self.logger = logging.getLogger(__name__)
        
    def generate_sample_data(self, symbols: List[str], 
                           start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate sample price data for backtesting"""
        
        dates = pd.date_range(start_date, end_date, freq='1min')
        data = []
        
        # Base prices
        base_prices = {
            'SPY': 400, 'QQQ': 350, 'IWM': 180,
            'TLT': 100, 'TMF': 25, 'TQQQ': 35,
            'UPRO': 45, 'TNA': 30, 'SOXL': 15
        }
        
        for symbol in symbols:
            price = base_prices.get(symbol, 100)
            returns = np.random.normal(0, 0.002, len(dates))  # 0.2% volatility per minute
            
            prices = [price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
                
            for i, date in enumerate(dates):
                volatility = 0.15 + 0.1 * np.sin(i / 100)  # Varying volatility
                data.append({
                    'timestamp': date,
                    'symbol': symbol,
                    'price': prices[i],
                    'volatility': volatility
                })
                
        return pd.DataFrame(data)
    
    def get_market_data(self, symbol: str, timestamp: datetime, 
                       price: float, volatility: float) -> MarketData:
        """Get or generate market data for a symbol at a timestamp"""
        
        key = (symbol, timestamp)
        if key not in self.market_data_cache:
            self.market_data_cache[key] = self.market_simulator.generate_market_data(
                symbol, price, volatility, timestamp
            )
        return self.market_data_cache[key]
    
    def calculate_portfolio_value(self, timestamp: datetime, 
                                price_data: Dict[str, float]) -> float:
        """Calculate current portfolio value"""
        
        total_value = self.cash
        
        for symbol, quantity in self.positions.items():
            if symbol in price_data:
                total_value += quantity * price_data[symbol]
                
        return total_value
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                   order_type: OrderType = OrderType.MARKET,
                   price: Optional[float] = None) -> Order:
        """Place a trading order"""
        
        order = Order(
            id=f"order_{len(self.orders)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price
        )
        
        self.orders.append(order)
        return order
    
    def process_orders(self, timestamp: datetime, price_data: Dict[str, float],
                      volatility_data: Dict[str, float]):
        """Process pending orders"""
        
        for order in self.orders:
            if order.status == OrderStatus.PENDING:
                if order.symbol in price_data:
                    market_data = self.get_market_data(
                        order.symbol, timestamp, 
                        price_data[order.symbol],
                        volatility_data.get(order.symbol, 0.2)
                    )
                    
                    trades = self.execution_engine.execute_order(order, market_data)
                    
                    for trade in trades:
                        self.trades.append(trade)
                        
                        # Update positions and cash
                        if trade.side == 'buy':
                            self.positions[trade.symbol] = (
                                self.positions.get(trade.symbol, 0) + trade.quantity
                            )
                            self.cash -= (trade.quantity * trade.price + 
                                        trade.commission + trade.total_cost)
                        else:
                            self.positions[trade.symbol] = (
                                self.positions.get(trade.symbol, 0) - trade.quantity
                            )
                            self.cash += (trade.quantity * trade.price - 
                                        trade.commission - trade.total_cost)
    
    def run_backtest(self, pairs: List[Tuple[str, str]], 
                    start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Run comprehensive backtest"""
        
        self.logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Generate sample data
        all_symbols = list(set([s for pair in pairs for s in pair]))
        data = self.generate_sample_data(all_symbols, start_date, end_date)
        
        # Group by timestamp
        data_by_time = data.groupby('timestamp')
        
        signal_count = 0
        trade_count = 0
        
        for timestamp, group in data_by_time:
            # Create price and volatility dictionaries
            price_data = dict(zip(group['symbol'], group['price']))
            volatility_data = dict(zip(group['symbol'], group['volatility']))
            
            # Convert timestamp to datetime if needed
            if isinstance(timestamp, pd.Timestamp):
                timestamp_dt = timestamp.to_pydatetime()
            elif isinstance(timestamp, datetime):
                timestamp_dt = timestamp
            else:
                # Skip if timestamp is not a valid datetime type
                continue
            
            # Process existing orders first
            self.process_orders(timestamp_dt, price_data, volatility_data)
            
            # Generate trading signals every 5 minutes
            if timestamp_dt.minute % 5 == 0:
                # Update regime detection
                regime_data = {symbol: {
                    'price': price_data[symbol],
                    'volatility': volatility_data[symbol]
                } for symbol in all_symbols if symbol in price_data}
                
                regime_info = self.regime_detector.detect_regime(regime_data)
                current_regime = regime_info['current_regime']
                
                # Check liquidity timing
                timing_score = self.liquidity_analyzer.get_execution_timing_score(timestamp)
                
                # Generate signals for each pair
                for symbol1, symbol2 in pairs:
                    if symbol1 in price_data and symbol2 in price_data:
                        # Simple mean reversion signal
                        price1, price2 = price_data[symbol1], price_data[symbol2]
                        
                        # Calculate spread
                        spread = np.log(price1) - np.log(price2)
                        
                        # Simple signal: buy when spread is low, sell when high
                        if spread < -0.02 and timing_score > 0.6:  # Buy signal
                            signal_count += 1
                            
                            # Calculate position sizes
                            portfolio_value = self.calculate_portfolio_value(timestamp, price_data)
                            
                            # Risk check
                            risk_metrics = self.risk_manager.calculate_portfolio_risk(
                                self.positions, price_data, volatility_data
                            )
                            
                            if risk_metrics['total_var'] < 0.05:  # VaR < 5%
                                # Calculate position sizes
                                target_allocation = min(0.1, 0.2 / len(pairs))  # Max 10% per pair
                                position_value = portfolio_value * target_allocation
                                
                                # Long symbol1, short symbol2
                                qty1 = position_value / price1
                                qty2 = -position_value / price2
                                
                                # Regime adjustment
                                if current_regime == 'high_vol':
                                    qty1 *= 0.7
                                    qty2 *= 0.7
                                elif current_regime == 'crisis':
                                    qty1 *= 0.4
                                    qty2 *= 0.4
                                
                                # Place orders
                                self.place_order(symbol1, 'buy', qty1)
                                self.place_order(symbol2, 'sell', abs(qty2))
                                trade_count += 2
                                
                        elif spread > 0.02 and timing_score > 0.6:  # Sell signal
                            signal_count += 1
                            
                            # Close positions if we have them
                            if (symbol1 in self.positions and 
                                self.positions[symbol1] > 0):
                                self.place_order(symbol1, 'sell', self.positions[symbol1])
                                trade_count += 1
                                
                            if (symbol2 in self.positions and 
                                self.positions[symbol2] < 0):
                                self.place_order(symbol2, 'buy', abs(self.positions[symbol2]))
                                trade_count += 1
            
            # Record portfolio snapshot
            portfolio_value = self.calculate_portfolio_value(timestamp, price_data)
            self.portfolio_history.append({
                'timestamp': timestamp,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'positions': self.positions.copy(),
                'regime': getattr(self.regime_detector, 'current_regime', 'normal')
            })
        
        # Calculate performance metrics
        self.calculate_performance_metrics()
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.portfolio_history[-1]['portfolio_value'],
            'total_return': (self.portfolio_history[-1]['portfolio_value'] - self.initial_capital) / self.initial_capital,
            'total_trades': len(self.trades),
            'signals_generated': signal_count,
            'orders_placed': trade_count,
            'portfolio_history': self.portfolio_history,
            'trades': self.trades,
            'performance_metrics': self.performance_metrics
        }
        
        self.logger.info(f"Backtest completed. Total return: {results['total_return']:.2%}")
        self.logger.info(f"Total trades: {results['total_trades']}")
        
        return results
    
    def calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        
        if not self.portfolio_history:
            return
            
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(self.portfolio_history)
        df['returns'] = df['portfolio_value'].pct_change()
        
        # Basic metrics
        total_return = (df['portfolio_value'].iloc[-1] - self.initial_capital) / self.initial_capital
        
        # Annualized metrics (assuming 252 trading days)
        periods_per_year = 252 * 390  # 390 minutes per trading day
        periods = len(df)
        
        annualized_return = (1 + total_return) ** (periods_per_year / periods) - 1
        annualized_volatility = df['returns'].std() * np.sqrt(periods_per_year)
        
        # Risk metrics
        portfolio_values = df['portfolio_value']
        if isinstance(portfolio_values, pd.Series):
            max_drawdown = self.calculate_max_drawdown(portfolio_values)
        else:
            max_drawdown = 0.0
        sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
        
        # Trade metrics
        if self.trades:
            trade_pnl = []
            for trade in self.trades:
                pnl = trade.quantity * trade.price - trade.commission - trade.total_cost
                if trade.side == 'sell':
                    pnl = -pnl
                trade_pnl.append(pnl)
            
            win_rate = sum(1 for pnl in trade_pnl if pnl > 0) / len(trade_pnl)
            avg_win = np.mean([pnl for pnl in trade_pnl if pnl > 0]) if any(pnl > 0 for pnl in trade_pnl) else 0
            avg_loss = np.mean([pnl for pnl in trade_pnl if pnl < 0]) if any(pnl < 0 for pnl in trade_pnl) else 0
            
            # Transaction costs
            total_commissions = sum(trade.commission for trade in self.trades)
            total_slippage = sum(abs(trade.quantity * trade.price * trade.slippage) for trade in self.trades)
            total_market_impact = sum(trade.total_cost for trade in self.trades)
            
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            total_commissions = 0
            total_slippage = 0
            total_market_impact = 0
        
        self.performance_metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_commissions': total_commissions,
            'total_slippage': total_slippage,
            'total_market_impact': total_market_impact,
            'total_transaction_costs': total_commissions + total_slippage + total_market_impact
        }
    
    def calculate_max_drawdown(self, portfolio_values: pd.Series) -> float:
        """Calculate maximum drawdown"""
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        return drawdown.min()
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive backtest report"""
        
        report = f"""
=== REALISTIC BACKTEST REPORT ===

PERFORMANCE SUMMARY:
- Initial Capital: ${results['initial_capital']:,.2f}
- Final Capital: ${results['final_capital']:,.2f}
- Total Return: {results['total_return']:.2%}
- Annualized Return: {self.performance_metrics['annualized_return']:.2%}
- Annualized Volatility: {self.performance_metrics['annualized_volatility']:.2%}
- Sharpe Ratio: {self.performance_metrics['sharpe_ratio']:.2f}
- Maximum Drawdown: {self.performance_metrics['max_drawdown']:.2%}

TRADING ACTIVITY:
- Total Trades: {results['total_trades']}
- Signals Generated: {results['signals_generated']}
- Orders Placed: {results['orders_placed']}
- Win Rate: {self.performance_metrics['win_rate']:.1%}
- Average Win: ${self.performance_metrics['avg_win']:.2f}
- Average Loss: ${self.performance_metrics['avg_loss']:.2f}

TRANSACTION COSTS:
- Total Commissions: ${self.performance_metrics['total_commissions']:.2f}
- Total Slippage: ${self.performance_metrics['total_slippage']:.2f}
- Total Market Impact: ${self.performance_metrics['total_market_impact']:.2f}
- Total Transaction Costs: ${self.performance_metrics['total_transaction_costs']:.2f}
- Transaction Cost as % of Capital: {self.performance_metrics['total_transaction_costs'] / results['initial_capital']:.2%}

RISK ANALYSIS:
- Maximum position concentration: {max([abs(sum(h['positions'].values()) if h['positions'] else 0) for h in results['portfolio_history']] + [0]) / results['initial_capital']:.1%}
- Average cash utilization: {(1 - np.mean([h['cash'] for h in results['portfolio_history']]) / results['initial_capital']):.1%}
"""
        
        return report

# Demo function
def run_realistic_backtest_demo():
    """Run a demonstration of the realistic backtesting framework"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Realistic Backtesting Demo")
    
    # Initialize backtester
    backtester = RealisticBacktester(initial_capital=1_000_000)
    
    # Define pairs to trade
    pairs = [
        ('SPY', 'UPRO'),
        ('QQQ', 'TQQQ'),
        ('TLT', 'TMF'),
        ('IWM', 'TNA')
    ]
    
    # Run backtest
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    
    results = backtester.run_backtest(pairs, start_date, end_date)
    
    # Generate report
    report = backtester.generate_report(results)
    print(report)
    
    # Save results
    results_df = pd.DataFrame(results['portfolio_history'])
    results_df.to_csv('realistic_backtest_results.csv', index=False)
    
    logger.info("Realistic backtest demo completed")
    return results

if __name__ == "__main__":
    run_realistic_backtest_demo() 