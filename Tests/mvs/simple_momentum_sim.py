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

# Import institutional components (with fallback handling)
try:
    from institutional_momentum_strategy import InstitutionalMomentumStrategy
    from portfolio_constructor import PortfolioConstructor
    from institutional_risk_manager import InstitutionalRiskManager
    print("✅ Institutional components loaded successfully")
except ImportError as e:
    print(f"⚠️  Import warning: {e}")
    print("Using simplified implementations...")
    
    # Simplified fallback implementations
    class InstitutionalMomentumStrategy:
        def calculate_momentum_signals(self, market_data, lookback=126):
            signals = {}
            for symbol, data in market_data.items():
                if len(data) > lookback:
                    # Calculate momentum as price change over lookback period
                    current_price = data['close'].iloc[-1]
                    past_price = data['close'].iloc[-lookback]
                    momentum = (current_price / past_price) - 1
                    
                    # Normalize and clip the signal
                    signals[symbol] = np.clip(momentum * 5, -2, 2)
                else:
                    signals[symbol] = 0.0
            return signals
    
    class PortfolioConstructor:
        def __init__(self):
            self.max_position_weight = 0.08
            self.target_volatility = 0.12
            
        def construct_portfolio(self, signals, current_portfolio, market_data, portfolio_value, rebalance_method='signal_weighted'):
            from dataclasses import dataclass
            
            @dataclass
            class PortfolioAllocation:
                symbol: str
                target_weight: float
                dollar_amount: float
                sector: str = "Technology"
            
            allocations = []
            sorted_signals = dict(sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True))
            
            total_weight = 0
            max_positions = 8
            position_count = 0
            
            for symbol, signal in sorted_signals.items():
                if position_count >= max_positions:
                    break
                    
                if abs(signal) > 0.1:  # Minimum signal threshold
                    weight = min(abs(signal) * 0.04, self.max_position_weight)
                    if total_weight + weight <= 0.6:  # Max 60% allocation
                        allocations.append(PortfolioAllocation(
                            symbol=symbol,
                            target_weight=weight,
                            dollar_amount=weight * portfolio_value,
                            sector="Technology"
                        ))
                        total_weight += weight
                        position_count += 1
            
            return allocations
    
    class InstitutionalRiskManager:
        def __init__(self):
            self.max_position_size = 0.08
            self.target_volatility = 0.12
            
        def calculate_position_sizes(self, signals, portfolio_value, volatilities, correlations, sector_exposures):
            return {symbol: min(abs(signal) * 0.04, self.max_position_size) 
                   for symbol, signal in signals.items()}

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
            'AAPL': {'drift': 0.0008, 'vol': 0.025},
            'MSFT': {'drift': 0.0006, 'vol': 0.022},
            'GOOGL': {'drift': 0.0004, 'vol': 0.028},
            'AMZN': {'drift': -0.0002, 'vol': 0.032},
            'TSLA': {'drift': 0.0012, 'vol': 0.045},
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

def run_momentum_simulation(symbols=None, simulation_days=252, lookback_days=63):
    """
    Run a complete momentum trading simulation
    
    Args:
        symbols: List of symbols to trade (default: tech stocks)
        simulation_days: Number of days to simulate
        lookback_days: Momentum lookback period
    """
    
    print("🚀 MVS Momentum Trading Simulation")
    print("=" * 50)
    
    # Default symbols if none provided
    if symbols is None:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
    
    # 1. Create sample market data
    market_data = create_sample_market_data(symbols, simulation_days + lookback_days)
    print(f"✅ Generated market data for {len(symbols)} symbols")
    
    # 2. Initialize strategy components
    strategy = InstitutionalMomentumStrategy()
    portfolio_constructor = PortfolioConstructor()
    risk_manager = InstitutionalRiskManager()
    
    # 3. Calculate momentum signals
    print(f"📈 Calculating momentum signals (lookback: {lookback_days} days)...")
    signals = strategy.calculate_momentum_signals(market_data)
    print(f"✅ Generated {len(signals)} momentum signals")
    
    # Debug: Print actual signal values
    if not signals or all(v == 0 for v in signals.values()):
        print("⚠️  No valid signals generated. Debugging...")
        for symbol, data in market_data.items():
            print(f"  {symbol}: {len(data)} days of data")
            if len(data) > 10:
                recent_return = (data['close'].iloc[-1] / data['close'].iloc[-10]) - 1
                print(f"    10-day return: {recent_return:.2%}")
        
        # Generate fallback signals for demonstration
        print("🔄 Generating fallback momentum signals...")
        signals = {}
        for symbol, data in market_data.items():
            # Simple momentum: compare recent vs older prices
            if len(data) > 30:
                recent_avg = data['close'].tail(10).mean()
                older_avg = data['close'].iloc[-30:-20].mean()
                momentum = (recent_avg / older_avg) - 1
                signals[symbol] = np.clip(momentum * 10, -2, 2)  # Scale and clip
            else:
                signals[symbol] = np.random.uniform(-1, 1)  # Random for demo
    
    # 4. Display top signals
    print("\\n📋 Momentum Rankings:")
    sorted_signals = dict(sorted(signals.items(), key=lambda x: x[1], reverse=True))
    for i, (symbol, signal) in enumerate(sorted_signals.items()):
        direction = "📈 LONG" if signal > 0 else "📉 SHORT"
        print(f"  {i+1:2d}. {symbol}: {signal:+6.2f} {direction}")
    
    # 5. Construct portfolio
    print(f"\\n🎯 Constructing portfolio...")
    current_portfolio = {}  # Starting fresh
    portfolio_value = 100000  # $100k portfolio
    
    allocations = portfolio_constructor.construct_portfolio(
        signals=signals,
        current_portfolio=current_portfolio,
        market_data=market_data,
        portfolio_value=portfolio_value,
        rebalance_method='signal_weighted'
    )
    
    print(f"✅ Constructed portfolio with {len(allocations)} positions")
    
    # 6. Display portfolio allocation
    print("\\n💼 Portfolio Allocation:")
    total_allocated = 0
    for allocation in allocations:
        total_allocated += allocation.target_weight
        direction = "📈 LONG" if signals.get(allocation.symbol, 0) > 0 else "📉 SHORT"
        print(f"  {allocation.symbol}: {allocation.target_weight:.1%} "
              f"(${allocation.dollar_amount:,.0f}) {direction}")
    
    cash_position = 1.0 - total_allocated
    print(f"  CASH: {cash_position:.1%} (${cash_position * portfolio_value:,.0f}) 💰")
    
    # 7. Risk analysis
    print("\\n⚠️  Risk Analysis:")
    portfolio_weights = {alloc.symbol: alloc.target_weight for alloc in allocations}
    volatilities = {}
    for symbol in portfolio_weights.keys():
        data = market_data[symbol]
        returns = data['close'].pct_change().dropna()
        volatilities[symbol] = returns.std() * np.sqrt(252)  # Annualized vol
    
    correlations = {}  # Simplified - assume low correlation
    sector_exposures = {}
    
    position_sizes = risk_manager.calculate_position_sizes(
        signals, portfolio_value, volatilities, correlations, sector_exposures
    )
    
    print(f"  Max position size: {risk_manager.max_position_size:.1%}")
    print(f"  Portfolio volatility target: {risk_manager.target_volatility:.1%}")
    
    # 8. Simulate forward performance (simple example)
    print("\\n📊 Forward Performance Simulation (30 days)...")
    
    # Get last 30 days of data for forward simulation
    forward_returns = {}
    total_portfolio_return = 0
    
    for allocation in allocations:
        symbol = allocation.symbol
        weight = allocation.target_weight
        
        # Get recent returns for this symbol
        recent_data = market_data[symbol].tail(30)
        period_return = (recent_data['close'].iloc[-1] / recent_data['close'].iloc[0]) - 1
        forward_returns[symbol] = period_return
        
        # Calculate contribution to portfolio
        contribution = weight * period_return
        total_portfolio_return += contribution
        
        direction = "📈" if period_return > 0 else "📉"
        print(f"  {symbol}: {period_return:+6.2%} return, {weight:.1%} weight {direction}")
    
    annualized_return = (1 + total_portfolio_return) ** (252/30) - 1
    print(f"\\n✅ Portfolio Performance:")
    print(f"  30-day return: {total_portfolio_return:+.2%}")
    print(f"  Annualized return: {annualized_return:+.1%}")
    
    # 9. Summary
    print("\\n" + "=" * 50)
    print("📊 Simulation Summary:")
    print(f"  • Symbols analyzed: {len(symbols)}")
    print(f"  • Signals generated: {len(signals)}")
    print(f"  • Portfolio positions: {len(allocations)}")
    print(f"  • Capital allocated: {total_allocated:.1%}")
    print(f"  • Simulated return: {total_portfolio_return:+.2%}")
    print(f"  • Annualized return: {annualized_return:+.1%}")
    
    return {
        'signals': signals,
        'allocations': allocations,
        'performance': total_portfolio_return,
        'market_data': market_data
    }

if __name__ == "__main__":
    # Example usage - you can customize these parameters
    
    print("Select simulation type:")
    print("1. Quick demo (5 symbols, 6 months)")
    print("2. Standard simulation (8 symbols, 1 year)")
    print("3. Extended simulation (15 symbols, 2 years)")
    print("4. Custom simulation")
    
    try:
        choice = input("Enter choice (1-4): ").strip()
    except:
        choice = "1"  # Default for non-interactive
    
    if choice == "1":
        # Quick demo
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        results = run_momentum_simulation(symbols, simulation_days=180, lookback_days=63)
        
    elif choice == "2":
        # Standard simulation
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX']
        results = run_momentum_simulation(symbols, simulation_days=252, lookback_days=126)
        
    elif choice == "3":
        # Extended simulation
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX',
                  'JPM', 'BAC', 'WMT', 'JNJ', 'PG', 'KO', 'XOM']
        results = run_momentum_simulation(symbols, simulation_days=504, lookback_days=252)
        
    elif choice == "4":
        # Custom simulation
        print("\\nCustom simulation - enter your parameters:")
        try:
            symbols_input = input("Symbols (comma-separated, e.g., AAPL,MSFT,GOOGL): ").strip()
            symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
            if not symbols:
                symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # Default
            
            sim_days = int(input("Simulation days (default 252): ") or "252")
            lookback = int(input("Momentum lookback days (default 126): ") or "126")
            
            results = run_momentum_simulation(symbols, sim_days, lookback)
        except:
            print("Using default parameters...")
            results = run_momentum_simulation()
    else:
        # Default
        results = run_momentum_simulation()
    
    print("\\n🎯 Simulation completed! Check the results above.")
    print("\\n💡 Next steps:")
    print("  • Modify parameters in the script")
    print("  • Add real market data connectors")
    print("  • Implement backtesting across multiple periods")
    print("  • Add transaction costs and slippage")
    print("  • Create performance reports and visualizations")
