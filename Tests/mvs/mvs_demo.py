"""
MVS Framework Demonstration
Quick demo of the momentum trading simulation capabilities
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def create_sample_data():
    """Create realistic sample market data for demonstration"""
    print("📊 Creating sample market data...")
    
    # Generate 2 years of daily data
    dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
    
    # Sample symbols with different momentum characteristics
    symbols = {
        'AAPL': {'drift': 0.0008, 'vol': 0.025},    # Strong momentum
        'MSFT': {'drift': 0.0006, 'vol': 0.022},    # Moderate momentum  
        'GOOGL': {'drift': 0.0004, 'vol': 0.028},   # Weak momentum
        'AMZN': {'drift': -0.0002, 'vol': 0.032},   # Negative momentum
        'TSLA': {'drift': 0.0012, 'vol': 0.045},    # High momentum, high vol
        'JPM': {'drift': 0.0003, 'vol': 0.020},     # Financial sector
        'JNJ': {'drift': 0.0002, 'vol': 0.015},     # Defensive
        'XOM': {'drift': 0.0001, 'vol': 0.035},     # Energy
    }
    
    market_data = {}
    
    for symbol, params in symbols.items():
        # Generate returns with momentum characteristics
        np.random.seed(42 + hash(symbol) % 1000)  # Consistent but different per symbol
        
        # Create trending behavior for momentum
        trend_component = np.linspace(0, params['drift'] * len(dates), len(dates))
        noise_component = np.random.normal(0, params['vol'], len(dates))
        daily_returns = trend_component / len(dates) + noise_component
        
        # Calculate prices
        initial_price = np.random.uniform(50, 200)
        prices = initial_price * np.exp(np.cumsum(daily_returns))
        
        # Generate volume (higher volume for momentum stocks)
        base_volume = np.random.uniform(1e6, 5e6)
        volume_multiplier = 1 + abs(params['drift']) * 1000  # Higher volume for trending stocks
        volumes = np.random.lognormal(
            np.log(base_volume * volume_multiplier), 0.3, len(dates)
        )
        
        # Create OHLCV data
        market_data[symbol] = pd.DataFrame({
            'open': prices * np.random.uniform(0.995, 1.005, len(dates)),
            'high': prices * np.random.uniform(1.000, 1.025, len(dates)),
            'low': prices * np.random.uniform(0.975, 1.000, len(dates)),
            'close': prices,
            'volume': volumes.astype(int)
        }, index=dates)
    
    print(f"✅ Generated {len(market_data)} symbols with {len(dates)} days of data")
    return market_data

def simple_momentum_calculation(market_data, lookback_days=252, skip_days=21):
    """Simple momentum signal calculation for demo"""
    print(f"📈 Calculating momentum signals (lookback: {lookback_days} days)...")
    
    signals = {}
    
    for symbol, data in market_data.items():
        try:
            if len(data) < lookback_days + skip_days:
                continue
                
            # Calculate momentum: (current_price / price_N_days_ago) - 1
            current_price = data['close'].iloc[-skip_days]  # Skip recent days
            past_price = data['close'].iloc[-(lookback_days + skip_days)]
            
            momentum = (current_price / past_price) - 1
            
            # Normalize signal (simple z-score)
            signals[symbol] = momentum
            
        except Exception as e:
            print(f"⚠️  Error calculating momentum for {symbol}: {e}")
            continue
    
    if signals:
        # Normalize signals across universe (cross-sectional)
        values = list(signals.values())
        mean_signal = np.mean(values)
        std_signal = np.std(values)
        
        if std_signal > 0:
            normalized_signals = {
                symbol: (signal - mean_signal) / std_signal 
                for symbol, signal in signals.items()
            }
        else:
            normalized_signals = signals
    else:
        normalized_signals = {}
    
    print(f"✅ Generated {len(normalized_signals)} momentum signals")
    return normalized_signals

def simple_portfolio_construction(signals, max_positions=5, target_exposure=0.7):
    """Simple portfolio construction for demo"""
    print(f"🎯 Constructing portfolio (max {max_positions} positions)...")
    
    if not signals:
        print("❌ No signals available for portfolio construction")
        return {}
    
    # Sort signals by strength and take top positions
    sorted_signals = sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True)
    selected_signals = dict(sorted_signals[:max_positions])
    
    # Simple equal weight allocation
    weight_per_position = target_exposure / len(selected_signals)
    
    portfolio = {}
    for symbol, signal in selected_signals.items():
        # Only take positions in direction of signal
        if abs(signal) > 0.5:  # Minimum signal threshold
            portfolio[symbol] = {
                'weight': weight_per_position,
                'signal': signal,
                'direction': 'long' if signal > 0 else 'short'
            }
    
    print(f"✅ Constructed portfolio with {len(portfolio)} positions")
    return portfolio

def calculate_simple_performance(portfolio, market_data, holding_period_days=30):
    """Simple performance calculation for demo"""
    print(f"📊 Calculating performance (holding period: {holding_period_days} days)...")
    
    if not portfolio:
        print("❌ No portfolio to analyze")
        return {}
    
    portfolio_returns = []
    
    for symbol, position in portfolio.items():
        try:
            data = market_data[symbol]
            
            # Get entry and exit prices
            entry_price = data['close'].iloc[-holding_period_days]
            exit_price = data['close'].iloc[-1]
            
            # Calculate return based on position direction
            if position['direction'] == 'long':
                asset_return = (exit_price / entry_price) - 1
            else:
                asset_return = (entry_price / exit_price) - 1
            
            # Weight by portfolio allocation
            weighted_return = asset_return * position['weight']
            portfolio_returns.append(weighted_return)
            
            print(f"  {symbol}: {asset_return:.2%} return, {position['weight']:.1%} weight")
            
        except Exception as e:
            print(f"⚠️  Error calculating return for {symbol}: {e}")
            continue
    
    if portfolio_returns:
        total_return = sum(portfolio_returns)
        annualized_return = (1 + total_return) ** (252 / holding_period_days) - 1
        
        performance = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'num_positions': len(portfolio_returns),
            'holding_period_days': holding_period_days
        }
        
        print(f"✅ Portfolio Performance: {total_return:.2%} total, {annualized_return:.2%} annualized")
        return performance
    else:
        print("❌ Could not calculate performance")
        return {}

def run_mvs_demo():
    """Run complete MVS framework demonstration"""
    print("🚀 MVS Framework Demonstration")
    print("=" * 50)
    
    try:
        # 1. Generate sample data
        market_data = create_sample_data()
        
        # 2. Calculate momentum signals
        signals = simple_momentum_calculation(market_data)
        
        # 3. Display top signals
        print("\n📋 Top Momentum Signals:")
        sorted_signals = sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True)
        for symbol, signal in sorted_signals[:8]:
            direction = "📈 LONG" if signal > 0 else "📉 SHORT"
            print(f"  {symbol}: {signal:+.2f} {direction}")
        
        # 4. Construct portfolio
        portfolio = simple_portfolio_construction(signals)
        
        # 5. Display portfolio
        print("\n🎯 Portfolio Allocation:")
        total_weight = 0
        for symbol, position in portfolio.items():
            direction_emoji = "📈" if position['direction'] == 'long' else "📉"
            print(f"  {symbol}: {position['weight']:.1%} {direction_emoji} {position['direction'].upper()}")
            total_weight += position['weight']
        print(f"  Cash: {(1-total_weight):.1%} 💰")
        
        # 6. Calculate performance
        performance = calculate_simple_performance(portfolio, market_data)
        
        # 7. Summary
        print("\n📊 Demo Summary:")
        print(f"  • Market Data: {len(market_data)} symbols, 2 years daily data")
        print(f"  • Signals Generated: {len(signals)} momentum signals")
        print(f"  • Portfolio Positions: {len(portfolio)} positions")
        if performance:
            print(f"  • Simulated Return: {performance['total_return']:.2%}")
            print(f"  • Annualized Return: {performance['annualized_return']:.2%}")
        
        print("\n✅ MVS Framework Demo Completed Successfully!")
        
        return {
            'market_data': market_data,
            'signals': signals,
            'portfolio': portfolio,
            'performance': performance
        }
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = run_mvs_demo()
    
    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    print("1. Fix API mismatches in test suite")
    print("2. Integrate with core_structure components")
    print("3. Add real data connectors")
    print("4. Implement live trading capabilities")
    print("5. Deploy to production environment")
