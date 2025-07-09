#!/usr/bin/env python3
"""
VNET/GDS Pair Trading Backtest
Comprehensive statistical arbitrage analysis for VNET and GDS pair.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import gzip
from datetime import datetime, timedelta
import yaml
from scipy import stats
from statsmodels.tsa.stattools import coint
import warnings
warnings.filterwarnings('ignore')

# Set style for better plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class VNETGDSBacktest:
    def __init__(self, data_dir=None):
        """Initialize the backtest with data directory."""
        self.data_dir = data_dir or self.load_config()
        self.symbol1, self.symbol2 = 'VNET', 'GDS'
        self.data = {}
        self.spread = None
        self.signals = None
        self.positions = None
        self.returns = None
        
    def load_config(self):
        """Load configuration from multiple sources."""
        data_dir = os.getenv('POLYGON_DATA_DIR')
        
        if not data_dir:
            config_path = Path('stat_arb_project/config/production_config.yaml')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    data_dir = config.get('data', {}).get('polygon_data_dir')
        
        if not data_dir:
            data_dir = '/Users/lei/Documents/data/polygon'
        
        return data_dir
    
    def load_data(self, start_date='2023-01-01', end_date='2024-01-01'):
        """Load and prepare data for both symbols."""
        print(f"Loading data for {self.symbol1} and {self.symbol2}...")
        print(f"Date range: {start_date} to {end_date}")
        
        data_path = Path(self.data_dir)
        csv_files = list(data_path.glob('*.csv.gz'))
        
        # Filter files by date range
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        relevant_files = []
        for file_path in csv_files:
            try:
                # Remove .csv extension from stem
                date_str = file_path.stem.replace('.csv', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                if start_dt <= file_date <= end_dt:
                    relevant_files.append(file_path)
            except:
                continue
        
        print(f"Found {len(relevant_files)} relevant data files")
        
        # Load data for both symbols
        for symbol in [self.symbol1, self.symbol2]:
            symbol_data = []
            
            for file_path in relevant_files:
                try:
                    with gzip.open(file_path, 'rt') as f:
                        df = pd.read_csv(f)
                        if 'ticker' in df.columns:
                            symbol_df = df[df['ticker'] == symbol].copy()
                            if not symbol_df.empty:
                                symbol_df['date'] = pd.to_datetime(file_path.stem)
                                symbol_data.append(symbol_df)
                except Exception as e:
                    continue
            
            if symbol_data:
                combined_data = pd.concat(symbol_data, ignore_index=True)
                combined_data['timestamp'] = pd.to_datetime(combined_data['window_start'], unit='ns')
                self.data[symbol] = combined_data.sort_values('timestamp')
                print(f"Loaded {len(self.data[symbol])} records for {symbol}")
            else:
                print(f"No data found for {symbol}")
                return False
        
        return True
    
    def prepare_daily_data(self):
        """Prepare daily OHLC data for analysis."""
        print("Preparing daily data...")
        
        daily_data = {}
        for symbol in [self.symbol1, self.symbol2]:
            # Resample to daily OHLC
            df = self.data[symbol].copy()
            df.set_index('timestamp', inplace=True)
            
            daily = df.resample('D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            daily_data[symbol] = daily
        
        # Align data by date
        common_dates = daily_data[self.symbol1].index.intersection(daily_data[self.symbol2].index)
        
        for symbol in [self.symbol1, self.symbol2]:
            daily_data[symbol] = daily_data[symbol].loc[common_dates]
        
        self.daily_data = daily_data
        print(f"Prepared {len(common_dates)} days of aligned data")
        
        return len(common_dates) > 0
    
    def cointegration_analysis(self):
        """Perform cointegration analysis."""
        print("\n" + "="*50)
        print("COINTEGRATION ANALYSIS")
        print("="*50)
        
        prices1 = self.daily_data[self.symbol1]['close']
        prices2 = self.daily_data[self.symbol2]['close']
        
        # Cointegration test
        score, pvalue, _ = coint(prices1, prices2)
        
        print(f"Cointegration Test Results:")
        print(f"  Test Statistic: {score:.4f}")
        print(f"  P-value: {pvalue:.6f}")
        print(f"  Cointegrated: {'YES' if pvalue < 0.05 else 'NO'}")
        
        # Calculate hedge ratio using OLS
        model = stats.linregress(prices1, prices2)
        self.hedge_ratio = model.slope
        self.intercept = model.intercept
        
        print(f"\nHedge Ratio (Beta): {self.hedge_ratio:.4f}")
        print(f"Intercept: {self.intercept:.4f}")
        print(f"R-squared: {model.rvalue**2:.4f}")
        
        # Calculate spread
        self.spread = prices1 - self.hedge_ratio * prices2 - self.intercept
        
        # Spread statistics
        spread_mean = self.spread.mean()
        spread_std = self.spread.std()
        
        print(f"\nSpread Statistics:")
        print(f"  Mean: {spread_mean:.4f}")
        print(f"  Std Dev: {spread_std:.4f}")
        print(f"  Min: {self.spread.min():.4f}")
        print(f"  Max: {self.spread.max():.4f}")
        
        return pvalue < 0.05
    
    def generate_signals(self, entry_threshold=2.0, exit_threshold=0.5):
        """Generate trading signals based on spread z-score."""
        print(f"\nGenerating signals with entry threshold: {entry_threshold}, exit: {exit_threshold}")
        
        if self.spread is None:
            print("Error: Spread not calculated. Run cointegration analysis first.")
            return None
        
        # Calculate z-score of spread
        spread_mean = self.spread.mean()
        spread_std = self.spread.std()
        z_score = (self.spread - spread_mean) / spread_std
        
        # Generate signals
        signals = pd.Series(0, index=self.spread.index)
        
        # Long spread (long VNET, short GDS)
        signals[z_score > entry_threshold] = 1
        signals[z_score < exit_threshold] = 0
        
        # Short spread (short VNET, long GDS)
        signals[z_score < -entry_threshold] = -1
        signals[z_score > -exit_threshold] = 0
        
        self.signals = signals
        self.z_score = z_score
        
        # Count signals
        long_signals = (signals == 1).sum()
        short_signals = (signals == -1).sum()
        
        print(f"Generated {long_signals} long signals and {short_signals} short signals")
        
        return signals
    
    def calculate_returns(self):
        """Calculate strategy returns."""
        print("\nCalculating returns...")
        
        # Get price data
        prices1 = self.daily_data[self.symbol1]['close']
        prices2 = self.daily_data[self.symbol2]['close']
        
        # Calculate individual returns
        returns1 = prices1.pct_change().dropna()
        returns2 = prices2.pct_change().dropna()
        
        # Align signals with returns
        if self.signals is None:
            print("Error: Signals not generated. Run signal generation first.")
            return None
            
        signals = self.signals[returns1.index]
        
        # Calculate strategy returns
        # When signal = 1: long VNET, short GDS
        # When signal = -1: short VNET, long GDS
        strategy_returns = signals.shift(1) * (returns1 - self.hedge_ratio * returns2)
        
        # Calculate cumulative returns
        cumulative_returns = (1 + strategy_returns).cumprod()
        
        self.returns = strategy_returns
        self.cumulative_returns = cumulative_returns
        
        # Performance metrics
        total_return = cumulative_returns.iloc[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(strategy_returns)) - 1
        volatility = strategy_returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        print(f"\nPERFORMANCE METRICS:")
        print(f"  Total Return: {total_return:.2%}")
        print(f"  Annual Return: {annual_return:.2%}")
        print(f"  Volatility: {volatility:.2%}")
        print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {max_drawdown:.2%}")
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown
        }
    
    def plot_results(self):
        """Plot the backtest results."""
        print("\nGenerating plots...")
        
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle(f'{self.symbol1}/{self.symbol2} Pair Trading Backtest', fontsize=16)
        
        # Plot 1: Price comparison
        ax1 = axes[0, 0]
        prices1 = self.daily_data[self.symbol1]['close']
        prices2 = self.daily_data[self.symbol2]['close']
        ax1.plot(prices1.index, prices1, label=self.symbol1, alpha=0.7)
        ax1.plot(prices2.index, prices2, label=self.symbol2, alpha=0.7)
        ax1.set_title('Price Comparison')
        ax1.legend()
        ax1.grid(True)
        
        # Plot 2: Spread
        ax2 = axes[0, 1]
        ax2.plot(self.spread.index, self.spread, color='purple', alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_title('Spread (VNET - β*GDS)')
        ax2.grid(True)
        
        # Plot 3: Z-score
        ax3 = axes[1, 0]
        ax3.plot(self.z_score.index, self.z_score, color='orange', alpha=0.7)
        ax3.axhline(y=2, color='red', linestyle='--', alpha=0.5, label='Entry Threshold')
        ax3.axhline(y=-2, color='red', linestyle='--', alpha=0.5)
        ax3.axhline(y=0.5, color='green', linestyle='--', alpha=0.5, label='Exit Threshold')
        ax3.axhline(y=-0.5, color='green', linestyle='--', alpha=0.5)
        ax3.set_title('Z-Score')
        ax3.legend()
        ax3.grid(True)
        
        # Plot 4: Signals
        ax4 = axes[1, 1]
        ax4.plot(self.signals.index, self.signals, color='blue', alpha=0.7)
        ax4.set_title('Trading Signals')
        ax4.set_ylabel('Signal (1=Long, -1=Short, 0=Flat)')
        ax4.grid(True)
        
        # Plot 5: Cumulative Returns
        ax5 = axes[2, 0]
        ax5.plot(self.cumulative_returns.index, self.cumulative_returns, color='green', linewidth=2)
        ax5.set_title('Cumulative Returns')
        ax5.grid(True)
        
        # Plot 6: Drawdown
        ax6 = axes[2, 1]
        rolling_max = self.cumulative_returns.expanding().max()
        drawdown = (self.cumulative_returns - rolling_max) / rolling_max
        ax6.fill_between(drawdown.index, drawdown, 0, color='red', alpha=0.3)
        ax6.set_title('Drawdown')
        ax6.grid(True)
        
        plt.tight_layout()
        plt.savefig(f'{self.symbol1}_{self.symbol2}_backtest.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"Plots saved as {self.symbol1}_{self.symbol2}_backtest.png")
    
    def run_backtest(self, start_date='2023-01-01', end_date='2023-12-31'):
        """Run the complete backtest."""
        print("="*70)
        print(f"VNET/GDS PAIR TRADING BACKTEST")
        print("="*70)
        
        # Load data
        if not self.load_data(start_date, end_date):
            print("Failed to load data!")
            return None
        
        # Prepare daily data
        if not self.prepare_daily_data():
            print("Failed to prepare daily data!")
            return None
        
        # Cointegration analysis
        is_cointegrated = self.cointegration_analysis()
        
        if not is_cointegrated:
            print("\n⚠️  WARNING: Series are not cointegrated!")
            print("   This may affect strategy performance.")
        
        # Generate signals
        self.generate_signals()
        
        # Calculate returns
        performance = self.calculate_returns()
        
        # Plot results
        self.plot_results()
        
        print("\n" + "="*70)
        print("BACKTEST COMPLETE")
        print("="*70)
        
        return performance

def main():
    """Main function to run the backtest."""
    backtest = VNETGDSBacktest()
    performance = backtest.run_backtest()
    
    if performance:
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   Total Return: {performance['total_return']:.2%}")
        print(f"   Annual Return: {performance['annual_return']:.2%}")
        print(f"   Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: {performance['max_drawdown']:.2%}")
        
        if performance['sharpe_ratio'] > 1.0:
            print(f"\n✅ Good Sharpe ratio (>1.0)")
        if performance['max_drawdown'] > -0.15:
            print(f"✅ Acceptable max drawdown (<15%)")
        if performance['total_return'] > 0:
            print(f"✅ Profitable strategy")

if __name__ == "__main__":
    main() 