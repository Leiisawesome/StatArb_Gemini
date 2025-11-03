"""
Test Helpers for Strategy Testing
=================================

Helper functions to create enriched DataFrames with all required indicators
and features for comprehensive strategy testing.

Author: StatArb_Gemini Test Suite
Date: November 3, 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType


def create_enriched_dataframe(
    symbol: str = 'AAPL',
    rows: int = 200,
    start_price: float = 100.0,
    trend: str = 'uptrend',
    include_indicators: bool = True,
    include_features: bool = True
) -> pd.DataFrame:
    """
    Create a complete enriched DataFrame with OHLCV + indicators + features
    
    This simulates the output from ProcessingPipelineOrchestrator (Rule 3 Phase 4)
    """
    # Create timestamps
    dates = pd.date_range(
        start=datetime.now() - timedelta(minutes=rows),
        end=datetime.now(),
        freq='1min'
    )[:rows]
    
    # Generate price data based on trend
    num_points = len(dates)
    if trend == 'uptrend':
        trend_component = np.linspace(0, 20, num_points)
        noise = np.random.normal(0, 2, num_points)
        close_prices = start_price + trend_component + noise
    elif trend == 'downtrend':
        trend_component = np.linspace(0, -20, num_points)
        noise = np.random.normal(0, 2, num_points)
        close_prices = start_price + trend_component + noise
    elif trend == 'sideways':
        noise = np.random.normal(0, 3, num_points)
        close_prices = start_price + noise
    else:  # random
        close_prices = start_price + np.cumsum(np.random.normal(0, 1, num_points))
    
    # Ensure positive prices
    close_prices = np.maximum(close_prices, start_price * 0.5)
    
    # Create OHLCV data
    data = pd.DataFrame({
        'timestamp': dates,
        'symbol': symbol,
        'open': close_prices * (1 + np.random.uniform(-0.01, 0.01, num_points)),
        'high': close_prices * (1 + np.random.uniform(0, 0.02, num_points)),
        'low': close_prices * (1 + np.random.uniform(-0.02, 0, num_points)),
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, num_points)
    })
    
    # Add technical indicators (Phase 2 output)
    if include_indicators:
        # Trend indicators
        data['SMA_10'] = data['close'].rolling(10).mean()
        data['SMA_20'] = data['close'].rolling(20).mean()
        data['SMA_50'] = data['close'].rolling(50).mean()
        data['SMA_200'] = data['close'].rolling(200).mean()
        data['EMA_9'] = data['close'].ewm(span=9).mean()
        data['EMA_12'] = data['close'].ewm(span=12).mean()
        data['EMA_26'] = data['close'].ewm(span=26).mean()
        
        # Momentum indicators
        data['RSI_14'] = 50 + np.random.uniform(-20, 20, num_points)  # Simplified RSI
        data['MACD'] = data['EMA_12'] - data['EMA_26']
        data['MACD_signal'] = data['MACD'].ewm(span=9).mean()
        data['MACD_hist'] = data['MACD'] - data['MACD_signal']
        data['Stochastic_K'] = 50 + np.random.uniform(-20, 20, num_points)
        data['Stochastic_D'] = data['Stochastic_K'].rolling(3).mean()
        
        # Volatility indicators
        data['ATR_14'] = np.abs(data['high'] - data['low']).rolling(14).mean()
        data['bb_upper'] = data['SMA_20'] + (data['close'].rolling(20).std() * 2)
        data['bb_middle'] = data['SMA_20']
        data['bb_lower'] = data['SMA_20'] - (data['close'].rolling(20).std() * 2)
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        
        # Trend strength
        data['ADX_14'] = 20 + np.random.uniform(-10, 10, num_points)
        
        # Volume indicators
        volume_ma = data['volume'].rolling(20).mean()
        data['volume_ratio'] = data['volume'] / volume_ma.replace(0, 1)
        data['OBV'] = (np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum()
        data['VWAP'] = (data['close'] * data['volume']).cumsum() / data['volume'].cumsum()
        
    # Add features (Phase 3 output)
    if include_features:
        # Returns
        data['returns_1'] = data['close'].pct_change(1)
        data['returns_5'] = data['close'].pct_change(5)
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        
        # Momentum features
        data['momentum_short'] = data['close'].pct_change(10)
        data['momentum_medium'] = data['close'].pct_change(20)
        data['momentum_long'] = data['close'].pct_change(50)
        data['momentum_score'] = (
            data['momentum_short'].fillna(0) * 0.5 +
            data['momentum_medium'].fillna(0) * 0.3 +
            data['momentum_long'].fillna(0) * 0.2
        )
        
        # Trend features
        data['trend_strength'] = np.abs(data['ADX_14'] - 20) / 20 if 'ADX_14' in data.columns else 0
        data['trend_direction'] = np.where(data['SMA_10'] > data['SMA_20'], 1, -1) if 'SMA_10' in data.columns else 0
        
        # Volatility features
        returns_std = data['returns_1'].rolling(20).std()
        data['volatility'] = returns_std * np.sqrt(252)
        data['volatility_ratio'] = data['volatility'] / data['volatility'].rolling(60).mean().replace(0, 1)
        
        # Price position
        if 'bb_upper' in data.columns:
            data['bb_position_normalized'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower']).replace(0, 1)
        
        # Z-score (for mean reversion)
        rolling_mean = data['close'].rolling(20).mean()
        rolling_std = data['close'].rolling(20).std()
        data['zscore'] = (data['close'] - rolling_mean) / rolling_std.replace(0, 1)
    
    # Forward fill NaN values (simulating pipeline cleaning)
    # Use forward fill then backward fill for compatibility
    data = data.ffill().bfill().fillna(0)
    
    return data


def create_enriched_data_dict(
    symbols: List[str] = ['AAPL'],
    rows: int = 200,
    **kwargs
) -> Dict[str, pd.DataFrame]:
    """Create enriched data dictionary for multiple symbols"""
    return {
        symbol: create_enriched_dataframe(symbol=symbol, rows=rows, **kwargs)
        for symbol in symbols
    }


def create_mock_strategy_signal(
    symbol: str = 'AAPL',
    signal_type: SignalType = SignalType.BUY,
    confidence: float = 0.75,
    quantity: float = 100.0
) -> StrategySignal:
    """Create a mock strategy signal for testing"""
    from core_engine.trading.strategies.strategy_engine import StrategySignal
    
    return StrategySignal(
        strategy_id='test_strategy',
        symbol=symbol,
        signal_type=signal_type,
        strength=confidence,
        confidence=confidence,
        target_quantity=quantity,
        timestamp=datetime.now()
    )

