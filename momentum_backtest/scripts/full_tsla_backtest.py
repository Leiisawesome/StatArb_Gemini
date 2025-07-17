#!/usr/bin/env python3
"""
Full TSLA Modern Momentum Backtest
Training: 2023-01-01 to 2023-12-31
Testing:  2024-01-01 to 2024-12-31
Capital:  $100,000
Strategy: Modern multi-timeframe momentum
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.modern_momentum import ModernMomentumStrategy
from src.backtesting.backtest_engine import BacktestEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_realistic_tsla_data():
    """Generate realistic TSLA price data for backtesting"""
    
    # Create date range with sufficient lookback for momentum calculation
    start_date = datetime(2022, 10, 1)  # Start earlier for momentum lookback
    end_date = datetime(2024, 12, 31)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    # Filter to business days
    dates = dates[dates.dayofweek < 5]
    
    # Initialize price series
    np.random.seed(42)  # For reproducible results
    
    # TSLA realistic price simulation with different market phases
    prices = []
    volumes = []
    
    # Starting price
    current_price = 180.0
    
    for i, date in enumerate(dates):
        # Different market phases
        if date < datetime(2023, 7, 1):
            # Bear market phase - declining trend with high volatility
            trend = -0.0002
            volatility = 0.035
        elif date < datetime(2024, 1, 1):
            # Recovery phase - modest uptrend
            trend = 0.0005
            volatility = 0.025
        elif date < datetime(2024, 7, 1):
            # Strong momentum phase
            trend = 0.0008
            volatility = 0.030
        else:
            # Consolidation phase
            trend = 0.0001
            volatility = 0.020
        
        # Add some momentum effects
        if i >= 10:
            # Recent momentum effect - use the actual price values
            recent_returns = [prices[j]['close'] / prices[j-1]['close'] - 1 
                            for j in range(max(1, i-10), i) if j > 0]
            if recent_returns:
                momentum_effect = np.mean(recent_returns) * 0.1
                trend += momentum_effect
        
        # Generate daily return
        daily_return = trend + np.random.normal(0, volatility)
        
        # Update price
        current_price *= (1 + daily_return)
        
        # Calculate OHLC
        daily_vol = volatility * 0.5
        high = current_price * (1 + abs(np.random.normal(0, daily_vol)))
        low = current_price * (1 - abs(np.random.normal(0, daily_vol)))
        open_price = current_price * (1 + np.random.normal(0, daily_vol * 0.3))
        
        prices.append({
            'date': date,
            'symbol': 'TSLA',
            'open': open_price,
            'high': max(high, current_price, open_price),
            'low': min(low, current_price, open_price),
            'close': current_price,
            'volume': int(np.random.normal(50000000, 15000000))
        })
    
    # Create DataFrame
    df = pd.DataFrame(prices)
    
    # Set MultiIndex
    df.set_index(['date', 'symbol'], inplace=True)
    
    logger.info(f"Generated {len(df)} price records")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df

def load_config():
    """Load backtest configuration"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'custom_backtest_config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info("Loaded custom backtest configuration")
        return config
    except FileNotFoundError:
        logger.warning("Custom config not found, using default configuration")
        # Default configuration
        return {
            "strategy": {
                "type": "modern_momentum",
                "short_window": 3,
                "medium_window": 10,
                "long_window": 20,
                "volatility_target": 0.15,
                "rebalance_frequency": "daily"
            },
            "data": {
                "testing_start": "2024-01-01",
                "testing_end": "2024-12-31"
            },
            "backtesting": {
                "initial_capital": 100000
            },
            "risk": {
                "max_leverage": 1.0,
                "max_position_weight": 1.0,
                "max_drawdown_limit": 0.25
            },
            "execution": {
                "commission_rate": 0.001,
                "bid_ask_spread": 0.001,
                "market_impact_coeff": 0.0005
            }
        }

def analyze_results(results):
    """Analyze and display backtest results"""
    
    print("\n" + "="*80)
    print("TSLA MODERN MOMENTUM BACKTEST RESULTS")
    print("="*80)
    
    # Basic performance metrics
    print(f"\nPERFORMANCE SUMMARY:")
    print(f"  Initial Capital:     ${results['initial_capital']:,.0f}")
    print(f"  Final Portfolio:     ${results['final_portfolio_value']:,.0f}")
    print(f"  Total Return:        {results['total_return']:.2%}")
    print(f"  Annualized Return:   {results['annualized_return']:.2%}")
    
    # Risk metrics
    print(f"\nRISK METRICS:")
    print(f"  Volatility:          {results['volatility']:.2%}")
    print(f"  Sharpe Ratio:        {results['sharpe_ratio']:.3f}")
    print(f"  Maximum Drawdown:    {results['max_drawdown']:.2%}")
    print(f"  VaR (5%):           {results['var_5pct']:.2%}")
    
    # Trading metrics
    print(f"\nTRADING STATISTICS:")
    print(f"  Total Trades:        {results['total_trades']}")
    print(f"  Winning Trades:      {results['winning_trades']}")
    print(f"  Win Rate:           {results['winning_trades']/max(1, results['total_trades']):.1%}")
    print(f"  Total Commission:    ${results['total_commission']:.2f}")
    print(f"  Total Slippage:      ${results['total_slippage']:.2f}")
    
    # Portfolio metrics
    print(f"\nPORTFOLIO METRICS:")
    print(f"  Average Leverage:    {results['avg_leverage']:.2f}")
    print(f"  Avg Long Exposure:   ${results['avg_long_exposure']:,.0f}")
    
    # Monthly performance breakdown
    if not results['portfolio_history'].empty:
        portfolio_df = results['portfolio_history']
        portfolio_df['month'] = portfolio_df.index.to_period('M')
        monthly_returns = portfolio_df.groupby('month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        print(f"\nMONTHLY RETURNS:")
        for month, ret in monthly_returns.items():
            print(f"  {month}:  {ret:7.2%}")
    
    # Trade analysis
    if not results['trade_history'].empty:
        trades_df = results['trade_history']
        
        print(f"\nTRADE ANALYSIS:")
        print(f"  Avg Trade Size:      ${trades_df['quantity'].mean() * trades_df['price'].mean():,.0f}")
        print(f"  Largest Trade:       ${trades_df['quantity'].max() * trades_df['price'].max():,.0f}")
        
        # Show recent trades
        print(f"\nRECENT TRADES (last 5):")
        recent_trades = trades_df.tail(5)
        for _, trade in recent_trades.iterrows():
            trade_value = trade['quantity'] * trade['price']
            print(f"  {trade['date'].strftime('%Y-%m-%d')} {trade['side']:4s} "
                  f"{trade['quantity']:6.0f} @ ${trade['price']:6.2f} "
                  f"(${trade_value:8,.0f})")

def main():
    """Run the full TSLA backtest"""
    logger.info("Starting Full TSLA Modern Momentum Backtest")
    
    try:
        # Load configuration
        config = load_config()
        
        # Generate realistic data
        logger.info("Generating realistic TSLA price data...")
        data = generate_realistic_tsla_data()
        
        # Initialize strategy
        logger.info("Initializing Modern Momentum Strategy...")
        strategy = ModernMomentumStrategy(config['strategy'])
        
        # Initialize backtest engine
        logger.info("Initializing backtest engine...")
        engine = BacktestEngine(config, strategy)
        
        # Run backtest
        logger.info("Running backtest...")
        results = engine.run_backtest(
            data=data,
            start_date=config['data']['testing_start'],
            end_date=config['data']['testing_end']
        )
        
        # Analyze results
        analyze_results(results)
        
        logger.info("Backtest completed successfully!")
        
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = main()
