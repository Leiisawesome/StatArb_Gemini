"""
Mock Data Generators for Testing
===============================

Utilities to generate realistic mock data for testing purposes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import random

from core_structure.engines import TradingSignal, SignalType, SignalStrength


class MockDataGenerator:
    """Generate realistic mock data for testing"""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible tests"""
        np.random.seed(seed)
        random.seed(seed)
    
    def generate_price_series(
        self, 
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        frequency: str = '1min',
        initial_price: float = 100.0,
        volatility: float = 0.02
    ) -> pd.DataFrame:
        """Generate realistic price series"""
        
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        n_periods = len(dates)
        
        # Generate returns with some autocorrelation
        returns = np.random.normal(0, volatility, n_periods)
        
        # Add some trend and mean reversion
        trend = np.linspace(-0.001, 0.001, n_periods)
        mean_reversion = -0.1 * (np.cumsum(returns) - np.mean(np.cumsum(returns)))
        
        returns = returns + trend + mean_reversion * 0.01
        
        # Calculate prices
        prices = initial_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV data
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, n_periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, n_periods)
        })
        
        # Ensure high >= close >= low and high >= open >= low
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        return data
    
    def generate_multi_asset_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        frequency: str = '1min',
        correlation_matrix: Optional[np.ndarray] = None
    ) -> Dict[str, pd.DataFrame]:
        """Generate correlated multi-asset data"""
        
        if correlation_matrix is None:
            # Generate random correlation matrix
            n_assets = len(symbols)
            correlation_matrix = self._generate_correlation_matrix(n_assets)
        
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        n_periods = len(dates)
        
        # Generate correlated returns
        independent_returns = np.random.normal(0, 0.02, (n_periods, len(symbols)))
        cholesky = np.linalg.cholesky(correlation_matrix)
        correlated_returns = independent_returns @ cholesky.T
        
        # Generate data for each symbol
        data = {}
        for i, symbol in enumerate(symbols):
            returns = correlated_returns[:, i]
            prices = 100 * np.exp(np.cumsum(returns))
            
            data[symbol] = pd.DataFrame({
                'timestamp': dates,
                'open': prices * (1 + np.random.normal(0, 0.0005, n_periods)),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
                'close': prices,
                'volume': np.random.randint(1000, 10000, n_periods)
            })
            
            # Fix OHLC relationships
            data[symbol]['high'] = np.maximum(
                data[symbol]['high'], 
                np.maximum(data[symbol]['open'], data[symbol]['close'])
            )
            data[symbol]['low'] = np.minimum(
                data[symbol]['low'], 
                np.minimum(data[symbol]['open'], data[symbol]['close'])
            )
        
        return data
    
    def generate_trending_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        trend_strength: float = 0.001,
        frequency: str = '1min'
    ) -> pd.DataFrame:
        """Generate data with strong trend for momentum testing"""
        
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        n_periods = len(dates)
        
        # Strong trend component
        trend = np.linspace(0, trend_strength * n_periods, n_periods)
        noise = np.random.normal(0, 0.01, n_periods)
        
        returns = trend + noise
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, n_periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, n_periods)
        })
    
    def generate_mean_reverting_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        mean_reversion_speed: float = 0.1,
        frequency: str = '1min'
    ) -> pd.DataFrame:
        """Generate mean-reverting data for mean reversion testing"""
        
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        n_periods = len(dates)
        
        # Mean-reverting process
        prices = [100.0]  # Initial price
        
        for i in range(1, n_periods):
            # Mean reversion towards 100
            mean_reversion = -mean_reversion_speed * (prices[-1] - 100)
            noise = np.random.normal(0, 1.0)
            
            new_price = prices[-1] + mean_reversion + noise
            prices.append(max(new_price, 50))  # Prevent negative prices
        
        prices = np.array(prices)
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, n_periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, n_periods)
        })
    
    def generate_cointegrated_pair(
        self,
        symbol1: str,
        symbol2: str,
        start_date: datetime,
        end_date: datetime,
        hedge_ratio: float = 1.0,
        frequency: str = '1min'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate cointegrated pair for pairs trading testing"""
        
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        n_periods = len(dates)
        
        # Generate first series
        returns1 = np.random.normal(0, 0.02, n_periods)
        prices1 = 100 * np.exp(np.cumsum(returns1))
        
        # Generate cointegrated second series
        # Second series follows first series with some noise
        cointegration_error = np.random.normal(0, 0.01, n_periods)
        prices2 = (prices1 * hedge_ratio + cointegration_error) / hedge_ratio
        
        # Ensure positive prices
        prices2 = np.maximum(prices2, 10)
        
        data1 = pd.DataFrame({
            'timestamp': dates,
            'open': prices1 * (1 + np.random.normal(0, 0.0005, n_periods)),
            'high': prices1 * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
            'low': prices1 * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
            'close': prices1,
            'volume': np.random.randint(1000, 10000, n_periods)
        })
        
        data2 = pd.DataFrame({
            'timestamp': dates,
            'open': prices2 * (1 + np.random.normal(0, 0.0005, n_periods)),
            'high': prices2 * (1 + np.abs(np.random.normal(0, 0.001, n_periods))),
            'low': prices2 * (1 - np.abs(np.random.normal(0, 0.001, n_periods))),
            'close': prices2,
            'volume': np.random.randint(1000, 10000, n_periods)
        })
        
        return data1, data2
    
    def _generate_correlation_matrix(self, n_assets: int) -> np.ndarray:
        """Generate a valid correlation matrix"""
        # Generate random matrix
        A = np.random.randn(n_assets, n_assets)
        
        # Make it symmetric and positive definite
        correlation_matrix = A @ A.T
        
        # Normalize to correlation matrix
        diag_sqrt = np.sqrt(np.diag(correlation_matrix))
        correlation_matrix = correlation_matrix / np.outer(diag_sqrt, diag_sqrt)
        
        return correlation_matrix


class MockSignalGenerator:
    """Generate mock trading signals for testing"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
    
    def generate_random_signals(
        self,
        symbols: List[str],
        n_signals: int,
        time_range: Tuple[datetime, datetime]
    ) -> List[TradingSignal]:
        """Generate random trading signals"""
        
        signals = []
        start_time, end_time = time_range
        time_delta = end_time - start_time
        
        for _ in range(n_signals):
            signal = TradingSignal(
                symbol=random.choice(symbols),
                signal_type=random.choice([SignalType.LONG, SignalType.SHORT]),
                strength=random.choice([SignalStrength.WEAK, SignalStrength.MODERATE, SignalStrength.STRONG]),
                confidence=random.uniform(0.5, 0.95),
                timestamp=start_time + timedelta(seconds=random.uniform(0, time_delta.total_seconds())),
                metadata={
                    'strategy': random.choice(['momentum', 'mean_reversion', 'pairs']),
                    'test_signal': True
                }
            )
            signals.append(signal)
        
        return signals
    
    def generate_momentum_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        lookback_period: int = 20
    ) -> List[TradingSignal]:
        """Generate momentum-based signals from price data"""
        
        signals = []
        
        if len(price_data) < lookback_period:
            return signals
        
        for i in range(lookback_period, len(price_data)):
            # Calculate momentum
            current_price = price_data.iloc[i]['close']
            past_price = price_data.iloc[i - lookback_period]['close']
            momentum = (current_price - past_price) / past_price
            
            # Generate signal based on momentum
            if abs(momentum) > 0.02:  # 2% threshold
                signal_type = SignalType.LONG if momentum > 0 else SignalType.SHORT
                strength = SignalStrength.STRONG if abs(momentum) > 0.05 else SignalStrength.MODERATE
                confidence = min(0.95, 0.5 + abs(momentum) * 10)
                
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=signal_type,
                    strength=strength,
                    confidence=confidence,
                    timestamp=price_data.iloc[i]['timestamp'],
                    metadata={
                        'strategy': 'momentum',
                        'momentum': momentum,
                        'lookback_period': lookback_period
                    }
                )
                signals.append(signal)
        
        return signals
    
    def generate_mean_reversion_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        lookback_period: int = 20,
        z_threshold: float = 2.0
    ) -> List[TradingSignal]:
        """Generate mean reversion signals from price data"""
        
        signals = []
        
        if len(price_data) < lookback_period:
            return signals
        
        for i in range(lookback_period, len(price_data)):
            # Calculate z-score
            recent_prices = price_data.iloc[i - lookback_period:i]['close']
            current_price = price_data.iloc[i]['close']
            
            mean_price = recent_prices.mean()
            std_price = recent_prices.std()
            
            if std_price > 0:
                z_score = (current_price - mean_price) / std_price
                
                # Generate signal based on z-score
                if abs(z_score) > z_threshold:
                    # Mean reversion: buy when price is low, sell when high
                    signal_type = SignalType.LONG if z_score < -z_threshold else SignalType.SHORT
                    strength = SignalStrength.STRONG if abs(z_score) > z_threshold * 1.5 else SignalStrength.MODERATE
                    confidence = min(0.95, 0.5 + abs(z_score) / z_threshold * 0.3)
                    
                    signal = TradingSignal(
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=strength,
                        confidence=confidence,
                        timestamp=price_data.iloc[i]['timestamp'],
                        metadata={
                            'strategy': 'mean_reversion',
                            'z_score': z_score,
                            'lookback_period': lookback_period
                        }
                    )
                    signals.append(signal)
        
        return signals


# Convenience functions for common test data
def create_sample_market_data(
    symbols: List[str] = ['AAPL', 'MSFT', 'GOOGL', 'TSLA'],
    days: int = 30,
    frequency: str = '1min'
) -> Dict[str, pd.DataFrame]:
    """Create sample market data for testing"""
    generator = MockDataGenerator()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return generator.generate_multi_asset_data(symbols, start_date, end_date, frequency)


def create_trending_data(
    symbol: str = 'AAPL',
    days: int = 10,
    trend_strength: float = 0.001
) -> pd.DataFrame:
    """Create trending data for momentum testing"""
    generator = MockDataGenerator()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return generator.generate_trending_data(symbol, start_date, end_date, trend_strength)


def create_mean_reverting_data(
    symbol: str = 'AAPL',
    days: int = 10,
    mean_reversion_speed: float = 0.1
) -> pd.DataFrame:
    """Create mean-reverting data for mean reversion testing"""
    generator = MockDataGenerator()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return generator.generate_mean_reverting_data(symbol, start_date, end_date, mean_reversion_speed)


def create_cointegrated_pair(
    symbol1: str = 'AAPL',
    symbol2: str = 'MSFT',
    days: int = 30,
    hedge_ratio: float = 1.0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Create cointegrated pair for pairs trading testing"""
    generator = MockDataGenerator()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return generator.generate_cointegrated_pair(symbol1, symbol2, start_date, end_date, hedge_ratio)
