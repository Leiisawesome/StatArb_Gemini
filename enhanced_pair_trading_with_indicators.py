#!/usr/bin/env python3
"""
Technical Indicators Integration for Statistical Arbitrage
=========================================================

This shows how to integrate Polygon.io technical indicators
into your existing statistical arbitrage system for:

1. Market regime detection
2. Entry/exit timing enhancement  
3. Risk management filters
4. Pair correlation stability assessment
"""

import sys
import os
sys.path.append('/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini/new_structure')

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np

class TechnicalIndicatorsPairTrading:
    """Enhanced pair trading with technical indicators"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io/v1/indicators"
        
        # Cache for indicators to reduce API calls
        self.indicator_cache = {}
        
    def get_indicator(self, indicator_type: str, symbol: str, 
                     timestamp: str = None, **kwargs) -> Optional[Dict]:
        """Get technical indicator with caching"""
        
        cache_key = f"{indicator_type}_{symbol}_{timestamp}_{kwargs}"
        if cache_key in self.indicator_cache:
            return self.indicator_cache[cache_key]
            
        # Default parameters
        params = {
            "timespan": "day",
            "adjusted": "true", 
            "series_type": "close",
            "order": "desc",
            "limit": 1,
            "apikey": self.api_key
        }
        
        # Add indicator-specific parameters
        if indicator_type == "sma" or indicator_type == "ema":
            params["window"] = kwargs.get("window", 20)
        elif indicator_type == "rsi":
            params["window"] = kwargs.get("window", 14)
        elif indicator_type == "macd":
            params.update({
                "short_window": kwargs.get("short_window", 12),
                "long_window": kwargs.get("long_window", 26), 
                "signal_window": kwargs.get("signal_window", 9)
            })
            
        if timestamp:
            params["timestamp"] = timestamp
            
        try:
            response = requests.get(f"{self.base_url}/{indicator_type}/{symbol}", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            self.indicator_cache[cache_key] = data
            return data
            
        except Exception as e:
            print(f"❌ Error getting {indicator_type} for {symbol}: {e}")
            return None
    
    def detect_market_regime(self, symbols: List[str]) -> Dict[str, str]:
        """
        Detect market regime for each symbol using multiple indicators
        Returns: {'AAPL': 'trending_up', 'GOOGL': 'ranging', ...}
        """
        regimes = {}
        
        for symbol in symbols:
            try:
                # Get indicators
                rsi_data = self.get_indicator("rsi", symbol, window=14)
                sma_20_data = self.get_indicator("sma", symbol, window=20)
                sma_50_data = self.get_indicator("sma", symbol, window=50)
                macd_data = self.get_indicator("macd", symbol)
                
                # Extract values
                rsi = rsi_data['results']['values'][0]['value'] if rsi_data and 'results' in rsi_data else 50
                sma_20 = sma_20_data['results']['values'][0]['value'] if sma_20_data and 'results' in sma_20_data else 0
                sma_50 = sma_50_data['results']['values'][0]['value'] if sma_50_data and 'results' in sma_50_data else 0
                macd_hist = macd_data['results']['values'][0]['histogram'] if macd_data and 'results' in macd_data else 0
                
                # Regime classification
                if sma_20 > sma_50 and macd_hist > 0 and rsi > 50:
                    regime = "trending_up"
                elif sma_20 < sma_50 and macd_hist < 0 and rsi < 50:
                    regime = "trending_down"
                elif abs(rsi - 50) < 20 and abs(macd_hist) < 0.5:
                    regime = "ranging"
                elif rsi > 70:
                    regime = "overbought"
                elif rsi < 30:
                    regime = "oversold"
                else:
                    regime = "uncertain"
                    
                regimes[symbol] = regime
                
            except Exception as e:
                print(f"❌ Error detecting regime for {symbol}: {e}")
                regimes[symbol] = "uncertain"
                
        return regimes
    
    def should_trade_pair(self, symbol1: str, symbol2: str, 
                         spread_zscore: float) -> Tuple[bool, str]:
        """
        Enhanced pair trading decision using technical indicators
        
        Returns: (should_trade, reason)
        """
        
        # Get market regimes
        regimes = self.detect_market_regime([symbol1, symbol2])
        regime1 = regimes.get(symbol1, "uncertain")
        regime2 = regimes.get(symbol2, "uncertain")
        
        # Rule 1: Both symbols should be in similar regimes for stable correlation
        stable_regimes = ["ranging", "trending_up", "trending_down"]
        if regime1 not in stable_regimes or regime2 not in stable_regimes:
            return False, f"Unstable regimes: {symbol1}={regime1}, {symbol2}={regime2}"
        
        # Rule 2: Avoid trading during extreme conditions
        if regime1 in ["overbought", "oversold"] or regime2 in ["overbought", "oversold"]:
            return False, f"Extreme conditions: {symbol1}={regime1}, {symbol2}={regime2}"
        
        # Rule 3: Check spread magnitude with RSI confirmation
        try:
            rsi1_data = self.get_indicator("rsi", symbol1)
            rsi2_data = self.get_indicator("rsi", symbol2)
            
            rsi1 = rsi1_data['results']['values'][0]['value'] if rsi1_data and 'results' in rsi1_data else 50
            rsi2 = rsi2_data['results']['values'][0]['value'] if rsi2_data and 'results' in rsi2_data else 50
            
            # For mean reversion, look for divergent RSI with significant spread
            if abs(spread_zscore) > 2.0:
                rsi_divergence = abs(rsi1 - rsi2) > 20
                if rsi_divergence:
                    return True, f"Strong signal: spread_z={spread_zscore:.2f}, RSI divergence={abs(rsi1-rsi2):.1f}"
                else:
                    return False, f"Spread significant but no RSI divergence: {abs(rsi1-rsi2):.1f}"
            
            # For moderate spreads, need confirming momentum
            elif abs(spread_zscore) > 1.5:
                macd1_data = self.get_indicator("macd", symbol1)
                macd2_data = self.get_indicator("macd", symbol2)
                
                macd1_hist = macd1_data['results']['values'][0]['histogram'] if macd1_data and 'results' in macd1_data else 0
                macd2_hist = macd2_data['results']['values'][0]['histogram'] if macd2_data and 'results' in macd2_data else 0
                
                # Look for momentum reversal signals
                momentum_reversal = (macd1_hist * macd2_hist < 0)  # Opposite momentum
                if momentum_reversal:
                    return True, f"Momentum reversal: spread_z={spread_zscore:.2f}, MACD divergent"
                else:
                    return False, f"Moderate spread but no momentum confirmation"
            
            else:
                return False, f"Spread too small: {spread_zscore:.2f}"
                
        except Exception as e:
            print(f"❌ Error in pair analysis: {e}")
            return False, f"Technical analysis failed: {e}"
    
    def get_position_sizing_multiplier(self, symbol1: str, symbol2: str) -> float:
        """
        Adjust position sizing based on technical indicators
        Returns multiplier (0.5 to 2.0)
        """
        try:
            # Get volatility indicators (using RSI as proxy)
            rsi1_data = self.get_indicator("rsi", symbol1)
            rsi2_data = self.get_indicator("rsi", symbol2)
            
            rsi1 = rsi1_data['results']['values'][0]['value'] if rsi1_data and 'results' in rsi1_data else 50
            rsi2 = rsi2_data['results']['values'][0]['value'] if rsi2_data and 'results' in rsi2_data else 50
            
            # Average RSI as market condition indicator
            avg_rsi = (rsi1 + rsi2) / 2
            
            # Conservative sizing in extreme conditions
            if avg_rsi > 75 or avg_rsi < 25:
                return 0.5  # Reduce size in extreme conditions
            elif 60 < avg_rsi < 70 or 30 < avg_rsi < 40:
                return 0.75  # Slightly reduce in moderate extremes
            elif 45 < avg_rsi < 55:
                return 1.5  # Increase in neutral conditions (best for mean reversion)
            else:
                return 1.0  # Normal sizing
                
        except Exception as e:
            print(f"❌ Error calculating position sizing: {e}")
            return 1.0  # Default to normal sizing

def demo_enhanced_pair_trading():
    """Demonstrate enhanced pair trading with technical indicators"""
    
    print("🚀 ENHANCED PAIR TRADING WITH TECHNICAL INDICATORS")
    print("=" * 65)
    
    # Initialize system
    API_KEY = "kwnaUOlnQq7lLqRU0KQg2MqndGblHPnR"
    pair_system = TechnicalIndicatorsPairTrading(API_KEY)
    
    # Example pairs from your screening
    test_pairs = [
        ("QQQ", "TQQQ"),
        ("NVDA", "NVDL"), 
        ("TLT", "TMF"),
        ("AAPL", "GOOGL")
    ]
    
    print(f"🔍 Testing {len(test_pairs)} pairs with technical indicators...")
    print("-" * 65)
    
    for symbol1, symbol2 in test_pairs:
        print(f"\n📊 Analyzing Pair: {symbol1} vs {symbol2}")
        
        # 1. Market regime detection
        regimes = pair_system.detect_market_regime([symbol1, symbol2])
        print(f"   📈 Market Regimes: {symbol1}={regimes[symbol1]}, {symbol2}={regimes[symbol2]}")
        
        # 2. Simulated spread analysis (you'd use real spread calculation)
        simulated_spread_zscore = np.random.normal(0, 1.5)  # Random for demo
        
        # 3. Trading decision
        should_trade, reason = pair_system.should_trade_pair(symbol1, symbol2, simulated_spread_zscore)
        
        # 4. Position sizing
        size_multiplier = pair_system.get_position_sizing_multiplier(symbol1, symbol2)
        
        print(f"   📏 Spread Z-Score: {simulated_spread_zscore:.2f}")
        print(f"   ✅ Trade Decision: {'TRADE' if should_trade else 'SKIP'}")
        print(f"   💭 Reason: {reason}")
        print(f"   💰 Position Size: {size_multiplier:.1f}x normal")
        
        if should_trade:
            print(f"   🎯 RECOMMENDED ACTION: Trade this pair with {size_multiplier:.1f}x sizing")
        else:
            print(f"   ⏸️  WAIT: {reason}")
    
    print(f"\n" + "=" * 65)
    print("📋 INTEGRATION SUMMARY")
    print("=" * 65)
    
    print("""
💡 HOW THIS ENHANCES YOUR STATISTICAL ARBITRAGE:

1️⃣ REGIME AWARENESS:
   • Avoid trading when correlations break down
   • Identify optimal market conditions for pairs
   
2️⃣ IMPROVED TIMING:
   • RSI divergence confirms spread extremes
   • MACD momentum helps predict reversions
   
3️⃣ DYNAMIC RISK MANAGEMENT:
   • Position sizing based on market conditions
   • Reduced exposure during volatile periods
   
4️⃣ LOWER FALSE SIGNALS:
   • Multiple indicator confirmation
   • Regime-based filtering reduces whipsaws

🔧 NEXT STEPS FOR YOUR SYSTEM:
   • Integrate into your ClickHouse screening
   • Add to your backtesting framework
   • Use for real-time position management
   • Cache indicators for performance
    """)

if __name__ == "__main__":
    demo_enhanced_pair_trading()
