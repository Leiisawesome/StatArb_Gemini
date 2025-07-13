"""
Enhanced Realistic Backtesting Framework with Improved Signal Generation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Import the base classes from the realistic backtester
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.realistic_backtester import (
    RealisticBacktester, OrderType, OrderStatus, Order, Trade, MarketData,
    RealisticMarketSimulator, RealisticExecutionEngine
)

class EnhancedRealisticBacktester(RealisticBacktester):
    """Enhanced version with improved signal generation and execution"""
    
    def __init__(self, initial_capital: float = 1_000_000):
        super().__init__(initial_capital)
        
        # Enhanced signal parameters
        self.signal_lookback = 20  # Minutes for signal calculation
        self.entry_threshold = 0.015  # 1.5% spread threshold
        self.exit_threshold = 0.005   # 0.5% spread threshold
        self.max_position_size = 0.25  # 25% of capital per pair
        
        # Track spread history for each pair
        self.spread_history = {}
        
        # Track active positions by pair
        self.active_pairs = {}
        
    def calculate_spread_zscore(self, symbol1: str, symbol2: str, 
                               price1: float, price2: float) -> float:
        """Calculate z-score of log price spread"""
        
        pair_key = f"{symbol1}_{symbol2}"
        current_spread = np.log(price1) - np.log(price2)
        
        # Initialize or update spread history
        if pair_key not in self.spread_history:
            self.spread_history[pair_key] = []
        
        self.spread_history[pair_key].append(current_spread)
        
        # Keep only recent history
        if len(self.spread_history[pair_key]) > self.signal_lookback:
            self.spread_history[pair_key] = self.spread_history[pair_key][-self.signal_lookback:]
        
        # Calculate z-score if we have enough history
        if len(self.spread_history[pair_key]) >= 10:
            spreads = np.array(self.spread_history[pair_key])
            mean_spread = np.mean(spreads)
            std_spread = np.std(spreads)
            
            if std_spread > 0:
                z_score = (current_spread - mean_spread) / std_spread
                return z_score
        
        return 0.0
    
    def should_enter_position(self, symbol1: str, symbol2: str, z_score: float,
                            timing_score: float, risk_check: bool) -> Tuple[bool, str]:
        """Determine if we should enter a position"""
        
        pair_key = f"{symbol1}_{symbol2}"
        
        # Check if we already have a position in this pair
        if pair_key in self.active_pairs:
            return False, "already_positioned"
        
        # Check timing and risk conditions
        if timing_score < 0.6 or not risk_check:
            return False, "timing_or_risk"
        
        # Check z-score thresholds
        if z_score < -2.0:  # Spread is unusually low, expect reversion
            return True, "long_spread"
        elif z_score > 2.0:  # Spread is unusually high, expect reversion
            return True, "short_spread"
        
        return False, "no_signal"
    
    def should_exit_position(self, symbol1: str, symbol2: str, z_score: float) -> bool:
        """Determine if we should exit a position"""
        
        pair_key = f"{symbol1}_{symbol2}"
        
        if pair_key not in self.active_pairs:
            return False
        
        position_type = self.active_pairs[pair_key]
        
        # Exit conditions
        if position_type == "long_spread" and z_score > -0.5:
            return True
        elif position_type == "short_spread" and z_score < 0.5:
            return True
        
        return False
    
    def run_enhanced_backtest(self, pairs: List[Tuple[str, str]], 
                            start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Run enhanced backtest with improved signal generation"""
        
        self.logger.info(f"Starting enhanced backtest from {start_date} to {end_date}")
        
        # Generate sample data
        all_symbols = list(set([s for pair in pairs for s in pair]))
        data = self.generate_sample_data(all_symbols, start_date, end_date)
        
        # Group by timestamp
        data_by_time = data.groupby('timestamp')
        
        signal_count = 0
        trade_count = 0
        entry_count = 0
        exit_count = 0
        
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
                continue
            
            # Process existing orders first
            self.process_orders(timestamp_dt, price_data, volatility_data)
            
            # Generate trading signals every minute
            if timestamp_dt.minute % 1 == 0:
                # Update regime detection
                regime_data = {symbol: {
                    'price': price_data[symbol],
                    'volatility': volatility_data[symbol]
                } for symbol in all_symbols if symbol in price_data}
                
                regime_info = self.regime_detector.detect_regime(regime_data)
                current_regime = regime_info['current_regime']
                
                # Check liquidity timing
                timing_score = self.liquidity_analyzer.get_execution_timing_score(timestamp_dt)
                
                # Calculate portfolio value for position sizing
                portfolio_value = self.calculate_portfolio_value(timestamp_dt, price_data)
                
                # Risk check
                risk_metrics = self.risk_manager.calculate_portfolio_risk(
                    self.positions, price_data, volatility_data
                )
                risk_check = risk_metrics['total_var'] < 0.05  # VaR < 5%
                
                # Process each pair
                for symbol1, symbol2 in pairs:
                    if symbol1 in price_data and symbol2 in price_data:
                        price1, price2 = price_data[symbol1], price_data[symbol2]
                        
                        # Calculate z-score
                        z_score = self.calculate_spread_zscore(symbol1, symbol2, price1, price2)
                        
                        pair_key = f"{symbol1}_{symbol2}"
                        
                        # Check for exit signals first
                        if self.should_exit_position(symbol1, symbol2, z_score):
                            exit_count += 1
                            
                            # Close positions
                            if symbol1 in self.positions and self.positions[symbol1] != 0:
                                qty1 = self.positions[symbol1]
                                side1 = 'sell' if qty1 > 0 else 'buy'
                                self.place_order(symbol1, side1, abs(qty1))
                                trade_count += 1
                                
                            if symbol2 in self.positions and self.positions[symbol2] != 0:
                                qty2 = self.positions[symbol2]
                                side2 = 'sell' if qty2 > 0 else 'buy'
                                self.place_order(symbol2, side2, abs(qty2))
                                trade_count += 1
                            
                            # Remove from active pairs
                            if pair_key in self.active_pairs:
                                del self.active_pairs[pair_key]
                        
                        # Check for entry signals
                        else:
                            should_enter, signal_type = self.should_enter_position(
                                symbol1, symbol2, z_score, timing_score, risk_check
                            )
                            
                            if should_enter:
                                signal_count += 1
                                entry_count += 1
                                
                                # Calculate position sizes
                                max_position_value = portfolio_value * self.max_position_size
                                position_value = min(max_position_value, portfolio_value * 0.1)
                                
                                # Regime adjustment
                                if current_regime == 'high_vol':
                                    position_value *= 0.7
                                elif current_regime == 'crisis':
                                    position_value *= 0.4
                                
                                # Calculate quantities
                                qty1 = position_value / price1
                                qty2 = position_value / price2
                                
                                if signal_type == "long_spread":
                                    # Long symbol1, short symbol2
                                    self.place_order(symbol1, 'buy', qty1)
                                    self.place_order(symbol2, 'sell', qty2)
                                    self.active_pairs[pair_key] = "long_spread"
                                    
                                elif signal_type == "short_spread":
                                    # Short symbol1, long symbol2
                                    self.place_order(symbol1, 'sell', qty1)
                                    self.place_order(symbol2, 'buy', qty2)
                                    self.active_pairs[pair_key] = "short_spread"
                                
                                trade_count += 2
            
            # Record portfolio snapshot
            portfolio_value = self.calculate_portfolio_value(timestamp_dt, price_data)
            self.portfolio_history.append({
                'timestamp': timestamp_dt,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'positions': self.positions.copy(),
                'regime': getattr(self.regime_detector, 'current_regime', 'normal'),
                'active_pairs': len(self.active_pairs)
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
            'entries': entry_count,
            'exits': exit_count,
            'portfolio_history': self.portfolio_history,
            'trades': self.trades,
            'performance_metrics': self.performance_metrics,
            'spread_history': self.spread_history
        }
        
        self.logger.info(f"Enhanced backtest completed. Total return: {results['total_return']:.2%}")
        self.logger.info(f"Total trades: {results['total_trades']}, Entries: {entry_count}, Exits: {exit_count}")
        
        return results
    
    def generate_enhanced_report(self, results: Dict[str, Any]) -> str:
        """Generate enhanced backtest report"""
        
        base_report = self.generate_report(results)
        
        enhanced_section = f"""
ENHANCED METRICS:
- Entry Signals: {results['entries']}
- Exit Signals: {results['exits']}
- Signal-to-Trade Ratio: {results['total_trades'] / max(results['signals_generated'], 1):.2f}
- Average Active Pairs: {np.mean([h['active_pairs'] for h in results['portfolio_history']]):.1f}
- Max Active Pairs: {max([h['active_pairs'] for h in results['portfolio_history']] + [0])}

SPREAD ANALYSIS:
"""
        
        # Add spread statistics
        for pair_key, spreads in results['spread_history'].items():
            if len(spreads) > 10:
                spreads_array = np.array(spreads)
                enhanced_section += f"- {pair_key}: Mean={np.mean(spreads_array):.4f}, Std={np.std(spreads_array):.4f}, Range=[{np.min(spreads_array):.4f}, {np.max(spreads_array):.4f}]\n"
        
        return base_report + enhanced_section

# Demo function
def run_enhanced_backtest_demo():
    """Run a demonstration of the enhanced realistic backtesting framework"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Enhanced Realistic Backtesting Demo")
    
    # Initialize enhanced backtester
    backtester = EnhancedRealisticBacktester(initial_capital=1_000_000)
    
    # Define pairs to trade
    pairs = [
        ('SPY', 'UPRO'),
        ('QQQ', 'TQQQ'),
        ('TLT', 'TMF'),
        ('IWM', 'TNA')
    ]
    
    # Run enhanced backtest
    start_date = datetime.now() - timedelta(days=3)  # Shorter period for demo
    end_date = datetime.now()
    
    results = backtester.run_enhanced_backtest(pairs, start_date, end_date)
    
    # Generate enhanced report
    report = backtester.generate_enhanced_report(results)
    print(report)
    
    # Save results
    results_df = pd.DataFrame(results['portfolio_history'])
    results_df.to_csv('enhanced_backtest_results.csv', index=False)
    
    # Save trades
    if results['trades']:
        trades_df = pd.DataFrame([{
            'timestamp': trade.timestamp,
            'symbol': trade.symbol,
            'side': trade.side,
            'quantity': trade.quantity,
            'price': trade.price,
            'commission': trade.commission,
            'slippage': trade.slippage,
            'market_impact': trade.market_impact,
            'total_cost': trade.total_cost
        } for trade in results['trades']])
        trades_df.to_csv('enhanced_backtest_trades.csv', index=False)
    
    logger.info("Enhanced realistic backtest demo completed")
    return results

if __name__ == "__main__":
    run_enhanced_backtest_demo() 