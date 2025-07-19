#!/usr/bin/env python3
"""
Simple Momentum Trading Simulation Example
Easy-to-use script for running momentum strategies
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_sample_market_data(symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'], days=500):
    """Create realistic sample market data for simulation"""
    print(f"📊 Creating sample data for {len(symbols)} symbols over {days} days...")
    
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    
    market_data = {}
    
    for symbol in symbols:
        # Set random seed for reproducible results
        np.random.seed(hash(symbol) % 1000)
        
        # Different momentum characteristics per symbol
        momentum_params = {
            'AAPL': {'drift': 0.0008, 'vol': 0.025},   # Strong positive momentum
            'MSFT': {'drift': 0.0006, 'vol': 0.022},   # Moderate positive momentum
            'GOOGL': {'drift': 0.0004, 'vol': 0.028},  # Weak positive momentum
            'AMZN': {'drift': -0.0002, 'vol': 0.032},  # Slight negative momentum
            'TSLA': {'drift': 0.0012, 'vol': 0.045},   # Strong momentum, high vol
            'NVDA': {'drift': 0.0010, 'vol': 0.038},   # Strong momentum
            'META': {'drift': 0.0003, 'vol': 0.035},   # Weak momentum
            'NFLX': {'drift': -0.0001, 'vol': 0.030},  # Slight negative
        }
        
        params = momentum_params.get(symbol, {'drift': 0.0003, 'vol': 0.025})
        
        # Generate returns with trend + noise
        trend = np.linspace(0, params['drift'] * len(dates), len(dates))
        noise = np.random.normal(0, params['vol'], len(dates))
        returns = trend / len(dates) + noise
        
        # Convert to prices
        initial_price = np.random.uniform(100, 300)
        prices = initial_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV data
        market_data[symbol] = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.005, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(dates)))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.3, len(dates))
        }, index=dates)
    
    return market_data

def calculate_momentum_signals(market_data, lookback_days=126):
    """Calculate momentum signals for each symbol"""
    signals = {}
    
    for symbol, data in market_data.items():
        if len(data) < lookback_days + 20:  # Need enough data
            continue
            
        # Simple momentum: log(current_price / price_N_days_ago)
        current_price = data['close'].iloc[-20]  # 20 days ago (skip recent to avoid noise)
        past_price = data['close'].iloc[-(lookback_days + 20)]
        
        momentum = np.log(current_price / past_price)
        signals[symbol] = momentum
    
    return signals

def construct_simple_portfolio(signals, max_positions=5, max_weight=0.15):
    """Simple portfolio construction based on momentum signals"""
    
    # Sort signals by strength
    sorted_signals = dict(sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True))
    
    # Take top signals
    selected_signals = dict(list(sorted_signals.items())[:max_positions])
    
    # Calculate weights based on signal strength
    total_signal = sum(abs(signal) for signal in selected_signals.values())
    
    allocations = {}
    for symbol, signal in selected_signals.items():
        weight = abs(signal) / total_signal
        weight = min(weight, max_weight)  # Position limit
        allocations[symbol] = {
            'weight': weight,
            'signal': signal,
            'direction': 'LONG' if signal > 0 else 'SHORT'
        }
    
    return allocations

def simulate_performance(allocations, market_data, holding_days=30):
    """Simulate portfolio performance over holding period"""
    
    portfolio_return = 0
    position_returns = {}
    
    for symbol, allocation in allocations.items():
        weight = allocation['weight']
        direction = allocation['direction']
        
        # Get performance over holding period
        data = market_data[symbol]
        start_price = data['close'].iloc[-holding_days]
        end_price = data['close'].iloc[-1]
        
        asset_return = (end_price / start_price) - 1
        
        # Apply direction (short positions get negative return)
        if direction == 'SHORT':
            asset_return = -asset_return
        
        position_return = weight * asset_return
        portfolio_return += position_return
        
        position_returns[symbol] = {
            'asset_return': asset_return,
            'position_return': position_return,
            'weight': weight,
            'direction': direction
        }
    
    return portfolio_return, position_returns

def run_momentum_simulation(symbols=None, simulation_days=252, lookback_days=126, holding_days=30):
    """
    Run a complete momentum trading simulation
    
    Args:
        symbols: List of symbols to trade
        simulation_days: Number of days of historical data
        lookback_days: Momentum calculation period
        holding_days: How long to hold positions
    """
    
    print("🚀 Simple Momentum Trading Simulation")
    print("=" * 50)
    
    # Default symbols if none provided
    if symbols is None:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    
    # 1. Create sample market data
    market_data = create_sample_market_data(symbols, simulation_days + lookback_days)
    print(f"✅ Generated market data for {len(symbols)} symbols")
    
    # 2. Calculate momentum signals
    print(f"📈 Calculating momentum signals (lookback: {lookback_days} days)...")
    signals = calculate_momentum_signals(market_data, lookback_days)
    print(f"✅ Generated {len(signals)} momentum signals")
    
    # 3. Display momentum rankings
    print("\\n📋 Momentum Rankings:")
    sorted_signals = dict(sorted(signals.items(), key=lambda x: x[1], reverse=True))
    for i, (symbol, signal) in enumerate(sorted_signals.items()):
        direction = "📈 LONG" if signal > 0 else "📉 SHORT"
        print(f"  {i+1:2d}. {symbol}: {signal:+6.3f} {direction}")
    
    # 4. Construct portfolio
    print(f"\\n🎯 Constructing portfolio...")
    allocations = construct_simple_portfolio(signals, max_positions=5)
    print(f"✅ Selected {len(allocations)} positions")
    
    # 5. Display portfolio allocation
    print("\\n💼 Portfolio Allocation:")
    total_allocated = 0
    for symbol, allocation in allocations.items():
        weight = allocation['weight']
        direction = allocation['direction']
        signal = allocation['signal']
        total_allocated += weight
        
        emoji = "📈" if direction == "LONG" else "📉"
        print(f"  {symbol}: {weight:.1%} {direction} {emoji} (signal: {signal:+.3f})")
    
    cash_position = 1.0 - total_allocated
    print(f"  CASH: {cash_position:.1%} 💰")
    
    # 6. Simulate performance
    print(f"\\n📊 Simulating performance ({holding_days} days holding period)...")
    portfolio_return, position_returns = simulate_performance(allocations, market_data, holding_days)
    
    print("\\n📈 Position Performance:")
    for symbol, perf in position_returns.items():
        emoji = "📈" if perf['asset_return'] > 0 else "📉"
        direction_emoji = "🟢" if perf['direction'] == 'LONG' else "🔴"
        print(f"  {symbol}: {perf['asset_return']:+6.2%} asset return, "
              f"{perf['position_return']:+6.2%} contribution "
              f"{emoji} {direction_emoji}")
    
    # 7. Calculate annualized return
    annualized_return = (1 + portfolio_return) ** (252 / holding_days) - 1
    
    print(f"\\n✅ Portfolio Results:")
    print(f"  {holding_days}-day return: {portfolio_return:+.2%}")
    print(f"  Annualized return: {annualized_return:+.1%}")
    
    # 8. Simple risk metrics
    portfolio_vol = 0
    for symbol, allocation in allocations.items():
        data = market_data[symbol]
        returns = data['close'].pct_change().dropna()
        vol = returns.std() * np.sqrt(252)  # Annualized volatility
        portfolio_vol += (allocation['weight'] * vol) ** 2
    
    portfolio_vol = np.sqrt(portfolio_vol)
    sharpe_ratio = annualized_return / portfolio_vol if portfolio_vol > 0 else 0
    
    print(f"  Portfolio volatility: {portfolio_vol:.1%}")
    print(f"  Sharpe ratio: {sharpe_ratio:.2f}")
    
    # 9. Summary
    print("\\n" + "=" * 50)
    print("📊 Simulation Summary:")
    print(f"  • Symbols analyzed: {len(symbols)}")
    print(f"  • Momentum signals: {len(signals)}")
    print(f"  • Portfolio positions: {len(allocations)}")
    print(f"  • Capital allocated: {total_allocated:.1%}")
    print(f"  • {holding_days}-day return: {portfolio_return:+.2%}")
    print(f"  • Annualized return: {annualized_return:+.1%}")
    print(f"  • Sharpe ratio: {sharpe_ratio:.2f}")
    
    return {
        'signals': signals,
        'allocations': allocations,
        'portfolio_return': portfolio_return,
        'annualized_return': annualized_return,
        'sharpe_ratio': sharpe_ratio,
        'market_data': market_data
    }

if __name__ == "__main__":
    print("🎯 Momentum Trading Simulation Options:")
    print("1. Quick demo (5 symbols, 6 months)")
    print("2. Standard simulation (8 symbols, 1 year)")
    print("3. Tech focus (FAANG+ stocks)")
    print("4. Custom parameters")
    print()
    
    # For non-interactive environments, run standard simulation
    try:
        choice = input("Enter choice (1-4, or press Enter for standard): ").strip()
        if not choice:
            choice = "2"
    except:
        choice = "2"  # Default for automated runs
    
    if choice == "1":
        # Quick demo
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        results = run_momentum_simulation(
            symbols=symbols, 
            simulation_days=180, 
            lookback_days=63,
            holding_days=20
        )
        
    elif choice == "3":
        # Tech focus
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'ORCL', 'CRM']
        results = run_momentum_simulation(
            symbols=symbols,
            simulation_days=252,
            lookback_days=126,
            holding_days=30
        )
        
    elif choice == "4":
        # Custom
        print("\\nEnter custom parameters (press Enter for defaults):")
        try:
            symbols_input = input("Symbols (comma-separated): ").strip()
            if symbols_input:
                symbols = [s.strip().upper() for s in symbols_input.split(',')]
            else:
                symbols = None
            
            sim_days = input("Historical days (default 252): ").strip()
            sim_days = int(sim_days) if sim_days else 252
            
            lookback = input("Momentum lookback days (default 126): ").strip()
            lookback = int(lookback) if lookback else 126
            
            holding = input("Holding period days (default 30): ").strip()
            holding = int(holding) if holding else 30
            
            results = run_momentum_simulation(symbols, sim_days, lookback, holding)
            
        except Exception as e:
            print(f"Error with custom parameters: {e}")
            print("Running with defaults...")
            results = run_momentum_simulation()
    else:
        # Standard simulation (default)
        results = run_momentum_simulation()
    
    print("\\n🎯 Simulation completed successfully!")
    print("\\n💡 Next steps to enhance your momentum strategy:")
    print("  • Add transaction costs (typically 0.1-0.5% per trade)")
    print("  • Implement sector neutrality")
    print("  • Add volatility targeting")
    print("  • Use real market data feeds")
    print("  • Backtest across multiple time periods")
    print("  • Add risk management rules (stop losses, position limits)")
    print("  • Optimize momentum lookback periods")
    print("  • Consider multiple timeframe signals")
