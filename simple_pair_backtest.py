#!/usr/bin/env python3
"""
Simple Pair Trading Backtest: VNET vs GDS
Uses the configured external data directory for backtesting.
"""
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from stat_arb_project.data.unified_data_loader import UnifiedDataLoader
from stat_arb_project.data.data_config import DataConfig, DataSource
from stat_arb_project.strategy.cointegration import CointegrationTester

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplePairTrader:
    """Simple pair trading strategy implementation."""
    
    def __init__(self, symbol1: str, symbol2: str, initial_capital: float = 100000):
        self.symbol1 = symbol1
        self.symbol2 = symbol2
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Trading state
        self.position = 0  # 1: long spread, -1: short spread, 0: flat
        self.entry_price = 0.0
        self.entry_time = None
        self.trades = []
        self.equity_curve = []
        
        # Strategy parameters
        self.entry_threshold = 2.0  # Z-score threshold for entry
        self.exit_threshold = 0.5   # Z-score threshold for exit
        self.lookback_period = 60   # Days for z-score calculation
        
        logger.info(f"Initialized pair trader for {symbol1}-{symbol2}")
    
    def calculate_spread(self, price1: float, price2: float) -> float:
        """Calculate simple price spread."""
        return price1 - price2
    
    def calculate_z_score(self, current_spread: float, spread_history: list) -> float:
        """Calculate z-score of current spread."""
        if len(spread_history) < self.lookback_period:
            return 0.0
        
        recent_spreads = spread_history[-self.lookback_period:]
        mean_spread = float(np.mean(recent_spreads))
        std_spread = float(np.std(recent_spreads))
        
        if std_spread == 0:
            return 0.0
        
        return float((current_spread - mean_spread) / std_spread)
    
    def generate_signal(self, z_score: float) -> int:
        """Generate trading signal based on z-score."""
        if self.position == 0:  # No position
            if z_score > self.entry_threshold:
                return -1  # Short spread (long symbol2, short symbol1)
            elif z_score < -self.entry_threshold:
                return 1   # Long spread (long symbol1, short symbol2)
        elif self.position == 1:  # Long spread
            if abs(z_score) < self.exit_threshold:
                return 0   # Exit position
        elif self.position == -1:  # Short spread
            if abs(z_score) < self.exit_threshold:
                return 0   # Exit position
        
        return 0  # No action
    
    def execute_trade(self, signal: int, price1: float, price2: float, timestamp: pd.Timestamp):
        """Execute trade based on signal."""
        if signal == 0 and self.position != 0:
            # Exit position
            if self.position == 1:
                # Exit long spread
                pnl = (price1 - self.entry_price) - (price2 - self.entry_price)
            else:
                # Exit short spread
                pnl = (self.entry_price - price1) - (self.entry_price - price2)
            
            self.current_capital += pnl * 1000  # Assume 1000 shares per position
            
            trade = {
                'entry_time': self.entry_time,
                'exit_time': timestamp,
                'position': self.position,
                'entry_price1': self.entry_price,
                'entry_price2': self.entry_price,
                'exit_price1': price1,
                'exit_price2': price2,
                'pnl': pnl * 1000,
                'capital': self.current_capital
            }
            self.trades.append(trade)
            
            self.position = 0
            self.entry_price = 0.0
            self.entry_time = None
            
            logger.info(f"Exit trade: PnL = ${pnl * 1000:.2f}, Capital = ${self.current_capital:.2f}")
            
        elif signal != 0 and self.position == 0:
            # Enter position
            self.position = signal
            self.entry_price = price1  # Use price1 as reference
            self.entry_time = timestamp
            
            if signal == 1:
                logger.info(f"Enter long spread: Long {self.symbol1} @ {price1:.2f}, Short {self.symbol2} @ {price2:.2f}")
            else:
                logger.info(f"Enter short spread: Short {self.symbol1} @ {price1:.2f}, Long {self.symbol2} @ {price2:.2f}")
        
        # Record equity
        self.equity_curve.append({
            'timestamp': timestamp,
            'capital': self.current_capital,
            'position': self.position,
            'price1': price1,
            'price2': price2
        })
    
    def run_backtest(self, data: pd.DataFrame) -> dict:
        """Run backtest on the data."""
        logger.info(f"Starting backtest with {len(data)} observations")
        
        spread_history = []
        
        for i, (timestamp, row) in enumerate(data.iterrows()):
            price1 = float(row[self.symbol1])
            price2 = float(row[self.symbol2])
            
            # Calculate spread
            spread = self.calculate_spread(price1, price2)
            spread_history.append(spread)
            
            # Calculate z-score
            z_score = self.calculate_z_score(spread, spread_history)
            
            # Generate signal
            signal = self.generate_signal(z_score)
            
            # Execute trade
            self.execute_trade(signal, price1, price2, timestamp)
            
            # Log progress
            if i % 1000 == 0:
                logger.info(f"Processed {i}/{len(data)} observations")
        
        # Close any open position at the end
        if self.position != 0:
            last_row = data.iloc[-1]
            last_price1 = float(last_row[self.symbol1])
            last_price2 = float(last_row[self.symbol2])
            self.execute_trade(0, last_price1, last_price2, data.index[-1])
        
        return self.calculate_performance()
    
    def calculate_performance(self) -> dict:
        """Calculate performance metrics."""
        if not self.trades:
            return {
                'total_return': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_trade': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'final_capital': self.current_capital
            }
        
        # Calculate returns
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # Calculate trade statistics
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.trades)
        avg_trade = np.mean([t['pnl'] for t in self.trades])
        
        # Calculate drawdown
        equity_series = pd.DataFrame(self.equity_curve)
        equity_series['cummax'] = equity_series['capital'].cummax()
        equity_series['drawdown'] = (equity_series['capital'] - equity_series['cummax']) / equity_series['cummax']
        max_drawdown = equity_series['drawdown'].min()
        
        # Calculate Sharpe ratio (simplified)
        if len(self.trades) > 1:
            returns = [t['pnl'] for t in self.trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_return': total_return,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'avg_trade': avg_trade,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': self.current_capital,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }

def run_vnet_gds_backtest():
    """Run backtest for VNET vs GDS pair."""
    print("="*80)
    print("VNET vs GDS PAIR TRADING BACKTEST")
    print("="*80)
    
    # Initialize data loader
    config = DataConfig(
        source=DataSource.POLYGON_OFFLINE,
        data_directory="/Users/lei/Documents/data/polygon",
        validate_quality=True
    )
    
    loader = UnifiedDataLoader(config)
    
    # Check available symbols
    symbols = loader.get_available_symbols()
    print(f"Available symbols: {symbols}")
    
    # Define symbols and date range
    symbol1, symbol2 = "VNET", "GDS"
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    
    print(f"\nLoading data for {symbol1} vs {symbol2}")
    print(f"Date range: {start_date} to {end_date}")
    
    try:
        # Load data
        data = loader.load_data(
            symbols=[symbol1, symbol2],
            start_date=start_date,
            end_date=end_date,
            interval='1m',
            data_type='close'
        )
        
        if data.empty:
            print("❌ No data loaded. Check if VNET and GDS are available in your data.")
            return
        
        print(f"✓ Loaded {len(data)} observations")
        print(f"Data range: {data.index[0]} to {data.index[-1]}")
        print(f"Columns: {list(data.columns)}")
        
        # Test cointegration
        print(f"\nTesting cointegration between {symbol1} and {symbol2}...")
        cointegration_tester = CointegrationTester()
        
        # Use first 252 days (1 year) for cointegration testing
        test_data = data.head(252 * 390)  # ~390 minutes per trading day
        series1 = test_data[symbol1]
        series2 = test_data[symbol2]
        
        cointegration_result = cointegration_tester.test_cointegration(series1, series2)
        is_cointegrated = bool(cointegration_result.get('is_cointegrated', False)) if isinstance(cointegration_result, dict) else bool(cointegration_result)
        
        print(f"Cointegration test result: {is_cointegrated}")
        if isinstance(cointegration_result, dict):
            print(f"P-value: {cointegration_result.get('p_value', 'N/A')}")
            print(f"Test statistic: {cointegration_result.get('test_statistic', 'N/A')}")
        
        # Run backtest
        print(f"\nRunning pair trading backtest...")
        trader = SimplePairTrader(symbol1, symbol2, initial_capital=100000)
        results = trader.run_backtest(data)
        
        # Print results
        print(f"\n" + "="*80)
        print("BACKTEST RESULTS")
        print("="*80)
        print(f"Symbols: {symbol1} vs {symbol2}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Capital: ${trader.initial_capital:,.2f}")
        print(f"Final Capital: ${results['final_capital']:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']:.2%}")
        print(f"Average Trade: ${results['avg_trade']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2%}")
        print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"Cointegrated: {is_cointegrated}")
        
        # Plot results if matplotlib is available
        try:
            plot_results(results, symbol1, symbol2)
        except Exception as e:
            print(f"Could not create plots: {e}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error during backtest: {e}")
        logger.error(f"Backtest error: {e}")
        return None

def plot_results(results: dict, symbol1: str, symbol2: str):
    """Plot backtest results."""
    if not results.get('equity_curve'):
        return
    
    equity_df = pd.DataFrame(results['equity_curve'])
    equity_df.set_index('timestamp', inplace=True)
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot equity curve
    ax1.plot(equity_df.index, equity_df['capital'], label='Portfolio Value', linewidth=2)
    ax1.axhline(y=100000, color='r', linestyle='--', alpha=0.7, label='Initial Capital')
    ax1.set_title(f'{symbol1} vs {symbol2} Pair Trading - Equity Curve')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot positions
    ax2.plot(equity_df.index, equity_df['position'], label='Position', linewidth=2)
    ax2.set_title('Trading Positions')
    ax2.set_ylabel('Position')
    ax2.set_xlabel('Date')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('vnet_gds_backtest_results.png', dpi=300, bbox_inches='tight')
    print(f"✓ Results plot saved as 'vnet_gds_backtest_results.png'")
    plt.show()

if __name__ == "__main__":
    run_vnet_gds_backtest() 