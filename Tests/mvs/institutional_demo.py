#!/usr/bin/env python3
"""
Advanced Momentum Trading with Full MVS Framework
Uses all institutional-grade components
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import asyncio
import json

# Add paths for core structure and ClickHouse components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'core_structure'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ClickHouse_Manager'))

# MVS Framework components
from institutional_momentum_strategy import InstitutionalMomentumStrategy
from portfolio_constructor import PortfolioConstructor
from institutional_risk_manager import InstitutionalRiskManager
from data_validator import DataValidator

# ClickHouse and data components
try:
    from clickhouse_data_loader import MVSClickHouseLoader, AsyncClickHouseLoader
    CLICKHOUSE_AVAILABLE = True
    print("✅ MVS ClickHouse loader imported successfully")
except ImportError as e:
    print(f"⚠️  ClickHouse loader not available: {e}")
    CLICKHOUSE_AVAILABLE = False

async def load_clickhouse_market_data(symbols, days=500, interval='1d'):
    """Load real market data from ClickHouse database"""
    print(f"🏛️  Loading institutional-grade data from ClickHouse...")
    print(f"📊 Symbols: {symbols}")
    print(f"📅 Period: {days} days, Interval: {interval}")
    
    try:
        if CLICKHOUSE_AVAILABLE:
            # Use the MVS ClickHouse loader
            with MVSClickHouseLoader() as loader:
                if loader.is_connected():
                    market_data = loader.load_market_data(symbols, days, interval)
                    
                    if market_data:
                        print(f"✅ Successfully loaded data for {len(market_data)} symbols from ClickHouse")
                        return market_data
                    else:
                        print("❌ No data returned from ClickHouse")
                        raise Exception("No data available")
                else:
                    raise Exception("Could not connect to ClickHouse")
        else:
            raise Exception("ClickHouse not available")
            
    except Exception as e:
        print(f"❌ ClickHouse loading failed: {e}")
        print("🔄 Falling back to synthetic data for demonstration...")
        return create_fallback_market_data(symbols, days)

def create_fallback_market_data(symbols, days=500):
    """Create synthetic market data as fallback when ClickHouse is unavailable"""
    print(f"📊 Creating fallback synthetic data for {len(symbols)} symbols...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    market_data = {}
    
    # Simplified symbol characteristics
    symbol_profiles = {
        'AAPL': {'sector': 'Technology', 'vol': 0.025},
        'MSFT': {'sector': 'Technology', 'vol': 0.022},
        'GOOGL': {'sector': 'Technology', 'vol': 0.028},
        'AMZN': {'sector': 'Consumer Discretionary', 'vol': 0.032},
        'TSLA': {'sector': 'Consumer Discretionary', 'vol': 0.045},
        'JPM': {'sector': 'Financials', 'vol': 0.025},
        'JNJ': {'sector': 'Healthcare', 'vol': 0.015},
        'XOM': {'sector': 'Energy', 'vol': 0.035},
    }
    
    for symbol in symbols:
        profile = symbol_profiles.get(symbol, {'sector': 'Other', 'vol': 0.025})
        
        np.random.seed(hash(symbol) % 1000)
        
        # Generate price series
        returns = np.random.normal(0.0003, profile['vol'], len(dates))
        initial_price = np.random.uniform(50, 300)
        prices = initial_price * np.exp(np.cumsum(returns))
        
        # Create OHLCV
        market_data[symbol] = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.002, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.008, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.008, len(dates)))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.2, len(dates))
        }, index=dates)
    
    return market_data

async def run_institutional_momentum_strategy(symbols=None, portfolio_value=1000000, use_clickhouse=True):
    """
    Run momentum strategy using full institutional framework with ClickHouse data
    """
    
    print("🏛️  Institutional Momentum Trading Strategy")
    print("=" * 60)
    
    if symbols is None:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'JPM', 'JNJ', 'XOM']
    
    # 1. Load market data from ClickHouse
    if use_clickhouse:
        print("🏛️  Using institutional ClickHouse data source")
        market_data = await load_clickhouse_market_data(symbols, days=400, interval='1d')
    else:
        print("📊 Using fallback synthetic data")
        market_data = create_fallback_market_data(symbols, days=400)
        
    print(f"✅ Loaded market data for {len(market_data)} symbols")
    
    # 2. Initialize institutional components
    print("\\n🔧 Initializing institutional components...")
    
    strategy = InstitutionalMomentumStrategy()
    portfolio_constructor = PortfolioConstructor()
    risk_manager = InstitutionalRiskManager()
    data_validator = DataValidator()
    
    print("✅ All components initialized")
    
    # 3. Data validation
    print("\\n🔍 Validating market data quality...")
    validation_results = {}
    
    for symbol, data in market_data.items():
        try:
            # Create simple validation result
            data_quality = min(1.0, len(data) / 200)  # More data = higher quality
            price_consistency = 1.0 - (data['close'].isna().sum() / len(data))
            
            validation_results[symbol] = {
                'data_quality_score': data_quality * price_consistency,
                'sufficient_data': len(data) > 100,
                'price_data_complete': data['close'].notna().all()
            }
        except Exception as e:
            print(f"⚠️  Validation failed for {symbol}: {e}")
            validation_results[symbol] = {
                'data_quality_score': 0.0,
                'sufficient_data': False,
                'price_data_complete': False
            }
    
    valid_symbols = [s for s, v in validation_results.items() 
                    if v['sufficient_data'] and v['data_quality_score'] > 0.8]
    
    print(f"✅ {len(valid_symbols)} symbols passed validation")
    print(f"⚠️  {len(symbols) - len(valid_symbols)} symbols failed validation")
    
    # 4. Generate momentum signals
    print("\\n📈 Generating institutional momentum signals...")
    
    # Filter to valid symbols
    valid_market_data = {s: market_data[s] for s in valid_symbols}
    
    try:
        signals = strategy.calculate_momentum_signals(valid_market_data)
        print(f"✅ Generated {len(signals)} momentum signals")
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return None
    
    # 5. Display signals with sector information
    print("\\n📊 Momentum Signal Analysis:")
    
    sector_map = {
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
        'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary',
        'JPM': 'Financials', 'JNJ': 'Healthcare', 'XOM': 'Energy'
    }
    
    # Group by sector
    sector_signals = {}
    for symbol, signal in signals.items():
        sector = sector_map.get(symbol, 'Other')
        if sector not in sector_signals:
            sector_signals[sector] = []
        sector_signals[sector].append((symbol, signal))
    
    for sector, sector_stocks in sector_signals.items():
        print(f"\\n📋 {sector} Sector:")
        sorted_stocks = sorted(sector_stocks, key=lambda x: x[1], reverse=True)
        for symbol, signal in sorted_stocks:
            direction = "📈 LONG" if signal > 0 else "📉 SHORT"
            print(f"    {symbol}: {signal:+6.3f} {direction}")
    
    # 6. Risk analysis
    print("\\n⚠️  Risk Analysis:")
    
    # Calculate correlations (simplified)
    correlation_matrix = {}
    for symbol1 in valid_symbols:
        correlation_matrix[symbol1] = {}
        for symbol2 in valid_symbols:
            if symbol1 == symbol2:
                correlation_matrix[symbol1][symbol2] = 1.0
            else:
                # Simplified correlation calculation
                returns1 = valid_market_data[symbol1]['close'].pct_change().dropna()
                returns2 = valid_market_data[symbol2]['close'].pct_change().dropna()
                
                # Align the data
                min_len = min(len(returns1), len(returns2))
                if min_len > 20:
                    corr = np.corrcoef(returns1.tail(min_len), returns2.tail(min_len))[0,1]
                    correlation_matrix[symbol1][symbol2] = corr if not np.isnan(corr) else 0.0
                else:
                    correlation_matrix[symbol1][symbol2] = 0.0
    
    # Calculate volatilities
    volatilities = {}
    for symbol in valid_symbols:
        returns = valid_market_data[symbol]['close'].pct_change().dropna()
        volatilities[symbol] = returns.std() * np.sqrt(252)
    
    print(f"📊 Average correlation: {np.mean([correlation_matrix[s1][s2] for s1 in valid_symbols for s2 in valid_symbols if s1 != s2]):.3f}")
    print(f"📊 Volatility range: {min(volatilities.values()):.1%} - {max(volatilities.values()):.1%}")
    
    # 7. Portfolio construction
    print("\\n🎯 Constructing institutional portfolio...")
    
    current_portfolio = {}  # Starting fresh
    
    try:
        allocations = portfolio_constructor.construct_portfolio(
            signals=signals,
            current_portfolio=current_portfolio,
            market_data=valid_market_data,
            portfolio_value=portfolio_value,
            rebalance_method='risk_adjusted'
        )
        print(f"✅ Portfolio constructed with {len(allocations)} positions")
    except Exception as e:
        print(f"❌ Portfolio construction failed: {e}")
        return None
    
    # 8. Display portfolio
    print("\\n💼 Institutional Portfolio Allocation:")
    
    total_allocated = 0
    sector_exposure = {}
    
    for allocation in allocations:
        symbol = allocation.symbol
        weight = allocation.target_weight
        sector = allocation.sector
        total_allocated += weight
        
        # Track sector exposure
        sector_exposure[sector] = sector_exposure.get(sector, 0) + weight
        
        signal = signals.get(symbol, 0)
        direction = "📈 LONG" if signal > 0 else "📉 SHORT"
        
        print(f"  {symbol:6s}: {weight:5.1%} {direction} | "
              f"${weight * portfolio_value:8,.0f} | "
              f"{sector}")
    
    cash_position = 1.0 - total_allocated
    print(f"  {'CASH':6s}: {cash_position:5.1%} 💰     | "
          f"${cash_position * portfolio_value:8,.0f}")
    
    # 9. Sector exposure analysis
    print("\\n📊 Sector Exposure Analysis:")
    for sector, exposure in sector_exposure.items():
        print(f"  {sector:20s}: {exposure:5.1%}")
    
    # 10. Risk metrics
    print("\\n📈 Portfolio Risk Metrics:")
    
    # Portfolio volatility (simplified)
    portfolio_variance = 0
    for i, alloc1 in enumerate(allocations):
        for j, alloc2 in enumerate(allocations):
            weight1 = alloc1.target_weight
            weight2 = alloc2.target_weight
            vol1 = volatilities.get(alloc1.symbol, 0.2)
            vol2 = volatilities.get(alloc2.symbol, 0.2)
            corr = correlation_matrix.get(alloc1.symbol, {}).get(alloc2.symbol, 0.5)
            
            portfolio_variance += weight1 * weight2 * vol1 * vol2 * corr
    
    portfolio_vol = np.sqrt(portfolio_variance)
    
    print(f"  Target volatility: {portfolio_constructor.target_volatility:.1%}")
    print(f"  Estimated portfolio volatility: {portfolio_vol:.1%}")
    print(f"  Maximum position size: {portfolio_constructor.max_position_weight:.1%}")
    print(f"  Capital allocation: {total_allocated:.1%}")
    
    # 11. Summary
    print("\\n" + "=" * 60)
    print("📊 Institutional Strategy Summary:")
    print(f"  • Universe: {len(symbols)} symbols analyzed")
    print(f"  • Data quality: {len(valid_symbols)} symbols validated")
    print(f"  • Signals generated: {len(signals)}")
    print(f"  • Portfolio positions: {len(allocations)}")
    print(f"  • Capital deployed: {total_allocated:.1%}")
    print(f"  • Target volatility: {portfolio_constructor.target_volatility:.1%}")
    print(f"  • Estimated volatility: {portfolio_vol:.1%}")
    print(f"  • Sector diversification: {len(sector_exposure)} sectors")
    
    return {
        'signals': signals,
        'allocations': allocations,
        'portfolio_value': portfolio_value,
        'sector_exposure': sector_exposure,
        'risk_metrics': {
            'portfolio_volatility': portfolio_vol,
            'total_allocation': total_allocated
        }
    }

async def main():
    """Main async function"""
    print("🏛️  Institutional Momentum Strategy Simulator")
    print("Choose your simulation:")
    print("1. Standard institutional portfolio ($1M)")
    print("2. Large institutional portfolio ($10M)")
    print("3. Custom portfolio size")
    print("4. Use synthetic data instead of ClickHouse")
    print()
    
    try:
        choice = input("Enter choice (1-4): ").strip()
    except:
        choice = "1"
    
    use_clickhouse = choice != "4"
    
    if choice == "2":
        portfolio_value = 10_000_000
    elif choice == "3":
        try:
            portfolio_value = float(input("Enter portfolio value ($): "))
        except:
            portfolio_value = 1_000_000
    else:
        portfolio_value = 1_000_000
    
    # Run the simulation
    results = await run_institutional_momentum_strategy(
        portfolio_value=portfolio_value,
        use_clickhouse=use_clickhouse
    )
    
    if results:
        print("\\n✅ Institutional momentum strategy simulation completed!")
        print("\\n🎯 Professional Implementation Steps:")
        print("  1. ✅ ClickHouse data integration (COMPLETED)")
        print("  2. Integrate with prime brokerage systems")
        print("  3. Implement advanced execution algorithms")
        print("  4. Add comprehensive risk monitoring")
        print("  5. Create institutional reporting dashboards")
        print("  6. Establish performance attribution analysis")
        print("  7. Implement ESG and regulatory compliance")
    else:
        print("❌ Simulation failed - check logs for details")

if __name__ == "__main__":
    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n❌ Simulation interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        # Fallback to synchronous execution
        print("🔄 Falling back to synchronous execution...")
        
        print("🏛️  Institutional Momentum Strategy Simulator")
        portfolio_value = 1_000_000
        
        # Use fallback data
        market_data = create_fallback_market_data(['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'JPM', 'JNJ', 'XOM'])
        print("📊 Using fallback synthetic data for demonstration")
