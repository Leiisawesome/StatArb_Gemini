#!/usr/bin/env python3
"""
Test Data Generators for Integration Testing
===========================================

Realistic historical data generators for comprehensive integration testing.
Generates market data with realistic patterns, volatility regimes, and market cycles.

Author: StatArb_Gemini Integration Testing
Phase: Integration Testing - Data Generation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class HistoricalDataGenerator:
    """
    Advanced historical data generator for integration testing
    
    Generates realistic market data with:
    - Multiple market regimes (bull, bear, sideways)
    - Realistic volatility patterns
    - Volume correlations with price movements
    - Intraday patterns and seasonality
    - Market microstructure effects
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize data generator
        
        Args:
            seed: Random seed for reproducible data
        """
        self.seed = seed
        np.random.seed(seed)
        
    def generate_single_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str = '1D',
        market_regimes: Optional[List[Dict]] = None
    ) -> pd.DataFrame:
        """
        Generate historical data for a single symbol
        
        Args:
            symbol: Symbol name (e.g., 'AAPL')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Data frequency ('1D', '1H', '1min')
            market_regimes: List of regime definitions
            
        Returns:
            DataFrame with OHLCV data
        """
        # Default market regimes if not provided
        if market_regimes is None:
            market_regimes = self._get_default_market_regimes()
        
        # Generate date range
        dates = pd.date_range(start_date, end_date, freq=timeframe)
        n_periods = len(dates)
        
        # Generate price series with regime changes
        prices = self._generate_price_series(n_periods, market_regimes)
        
        # Generate OHLCV data
        ohlcv_data = self._generate_ohlcv_from_prices(dates, prices, symbol)
        
        return ohlcv_data
    
    def generate_multi_symbol_data(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        timeframe: str = '1D',
        correlation_matrix: Optional[np.ndarray] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate correlated historical data for multiple symbols
        
        Args:
            symbols: List of symbols
            start_date: Start date
            end_date: End date
            timeframe: Data frequency
            correlation_matrix: Correlation matrix between symbols
            
        Returns:
            Dict mapping symbols to DataFrames
        """
        n_symbols = len(symbols)
        dates = pd.date_range(start_date, end_date, freq=timeframe)
        n_periods = len(dates)
        
        # Generate correlation matrix if not provided
        if correlation_matrix is None:
            correlation_matrix = self._generate_correlation_matrix(n_symbols)
        
        # Generate correlated returns
        returns = self._generate_correlated_returns(n_periods, correlation_matrix)
        
        # Generate data for each symbol
        data = {}
        for i, symbol in enumerate(symbols):
            # Generate base price series
            base_price = np.random.uniform(50, 500)  # Random starting price
            symbol_returns = returns[:, i]
            prices = base_price * (1 + symbol_returns).cumprod()
            
            # Generate OHLCV
            ohlcv = self._generate_ohlcv_from_prices(dates, prices, symbol)
            data[symbol] = ohlcv
        
        return data
    
    def generate_regime_specific_data(
        self,
        symbol: str,
        regime_periods: List[Dict],
        timeframe: str = '1D'
    ) -> pd.DataFrame:
        """
        Generate data with specific regime periods
        
        Args:
            symbol: Symbol name
            regime_periods: List of regime definitions with start/end dates
            timeframe: Data frequency
            
        Returns:
            DataFrame with regime-tagged data
        """
        all_data = []
        
        for regime_period in regime_periods:
            start_date = regime_period['start_date']
            end_date = regime_period['end_date']
            regime_type = regime_period['regime_type']
            volatility = regime_period.get('volatility', 0.02)
            trend = regime_period.get('trend', 0.0)
            
            # Generate dates for this period
            dates = pd.date_range(start_date, end_date, freq=timeframe)
            n_periods = len(dates)
            
            # Generate regime-specific returns
            returns = np.random.normal(trend, volatility, n_periods)
            prices = 100 * (1 + returns).cumprod()
            
            # Generate OHLCV
            ohlcv = self._generate_ohlcv_from_prices(dates, prices, symbol)
            ohlcv['regime'] = regime_type
            
            all_data.append(ohlcv)
        
        # Combine all periods
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data.sort_values('timestamp').reset_index(drop=True)
    
    def _get_default_market_regimes(self) -> List[Dict]:
        """Get default market regime definitions"""
        return [
            {
                'name': 'bull_market',
                'start_pct': 0.0,
                'end_pct': 0.4,
                'daily_return': 0.0008,
                'volatility': 0.015,
                'volume_multiplier': 1.0
            },
            {
                'name': 'bear_market',
                'start_pct': 0.4,
                'end_pct': 0.6,
                'daily_return': -0.0012,
                'volatility': 0.025,
                'volume_multiplier': 1.5
            },
            {
                'name': 'sideways_market',
                'start_pct': 0.6,
                'end_pct': 1.0,
                'daily_return': 0.0001,
                'volatility': 0.012,
                'volume_multiplier': 0.8
            }
        ]
    
    def _generate_price_series(self, n_periods: int, market_regimes: List[Dict]) -> np.ndarray:
        """Generate price series with regime changes"""
        prices = np.zeros(n_periods)
        prices[0] = 100.0  # Starting price
        
        for i in range(1, n_periods):
            # Determine current regime based on position in series
            position_pct = i / n_periods
            
            current_regime = None
            for regime in market_regimes:
                if regime['start_pct'] <= position_pct < regime['end_pct']:
                    current_regime = regime
                    break
            
            if current_regime is None:
                # Use last regime if we're at the end
                current_regime = market_regimes[-1]
            
            # Generate return for this period
            daily_return = np.random.normal(
                current_regime['daily_return'],
                current_regime['volatility']
            )
            
            # Apply return to price
            prices[i] = prices[i-1] * (1 + daily_return)
        
        return prices
    
    def _generate_ohlcv_from_prices(
        self,
        dates: pd.DatetimeIndex,
        prices: np.ndarray,
        symbol: str
    ) -> pd.DataFrame:
        """Generate OHLCV data from price series"""
        len(prices)
        
        # Generate realistic OHLC from close prices
        data = []
        
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Generate intraday volatility
            intraday_vol = close * 0.01  # 1% intraday volatility
            
            # Generate open price (previous close + small gap)
            if i == 0:
                open_price = close
            else:
                gap = np.random.normal(0, intraday_vol * 0.3)
                open_price = prices[i-1] + gap
            
            # Generate high and low
            high_move = abs(np.random.normal(0, intraday_vol * 0.5))
            low_move = abs(np.random.normal(0, intraday_vol * 0.5))
            
            high = max(open_price, close) + high_move
            low = min(open_price, close) - low_move
            
            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            # Generate volume (correlated with price movement)
            price_change = abs(close - open_price) / open_price if open_price > 0 else 0
            base_volume = 1000000
            volume_multiplier = 1.0 + price_change * 2.0  # Higher volume on larger moves
            volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 1.5))
            
            data.append({
                'timestamp': date,
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def _generate_correlation_matrix(self, n_symbols: int) -> np.ndarray:
        """Generate realistic correlation matrix for symbols"""
        # Start with identity matrix
        corr_matrix = np.eye(n_symbols)
        
        # Add some correlation between symbols
        for i in range(n_symbols):
            for j in range(i+1, n_symbols):
                # Random correlation between 0.3 and 0.8
                correlation = np.random.uniform(0.3, 0.8)
                corr_matrix[i, j] = correlation
                corr_matrix[j, i] = correlation
        
        return corr_matrix
    
    def _generate_correlated_returns(self, n_periods: int, correlation_matrix: np.ndarray) -> np.ndarray:
        """Generate correlated returns using Cholesky decomposition"""
        n_symbols = correlation_matrix.shape[0]
        
        # Generate independent random returns
        independent_returns = np.random.normal(0, 0.02, (n_periods, n_symbols))
        
        # Apply correlation using Cholesky decomposition
        try:
            L = np.linalg.cholesky(correlation_matrix)
            correlated_returns = independent_returns @ L.T
        except np.linalg.LinAlgError:
            # If correlation matrix is not positive definite, use independent returns
            logger.warning("Correlation matrix not positive definite, using independent returns")
            correlated_returns = independent_returns
        
        return correlated_returns


class RegimeTestDataGenerator:
    """
    Specialized data generator for regime detection testing
    
    Generates data with known regime characteristics for validation
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
    
    def generate_known_regime_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        regime_specifications: List[Dict]
    ) -> pd.DataFrame:
        """
        Generate data with known regime characteristics
        
        Args:
            symbol: Symbol name
            start_date: Start date
            end_date: End date
            regime_specifications: List of regime specs with known characteristics
            
        Returns:
            DataFrame with regime-tagged data
        """
        all_data = []
        
        for spec in regime_specifications:
            regime_name = spec['regime_name']
            start_date_regime = spec['start_date']
            end_date_regime = spec['end_date']
            daily_return = spec['daily_return']
            volatility = spec['volatility']
            trend_strength = spec.get('trend_strength', 0.5)
            
            # Generate dates for this regime
            dates = pd.date_range(start_date_regime, end_date_regime, freq='1D')
            n_periods = len(dates)
            
            # Generate regime-specific returns
            base_returns = np.random.normal(daily_return, volatility, n_periods)
            
            # Add trend component
            trend_component = np.linspace(0, trend_strength, n_periods)
            returns = base_returns + trend_component * volatility
            
            # Generate prices
            prices = 100 * (1 + returns).cumprod()
            
            # Generate OHLCV
            ohlcv = self._generate_ohlcv_from_prices(dates, prices, symbol)
            ohlcv['true_regime'] = regime_name
            ohlcv['regime_confidence'] = spec.get('confidence', 0.8)
            
            all_data.append(ohlcv)
        
        # Combine all regimes
        combined_data = pd.concat(all_data, ignore_index=True)
        return combined_data.sort_values('timestamp').reset_index(drop=True)
    
    def _generate_ohlcv_from_prices(
        self,
        dates: pd.DatetimeIndex,
        prices: np.ndarray,
        symbol: str
    ) -> pd.DataFrame:
        """Generate OHLCV data from price series (same as HistoricalDataGenerator)"""
        len(prices)
        data = []
        
        for i, (date, close) in enumerate(zip(dates, prices)):
            if i == 0:
                open_price = close
            else:
                gap = np.random.normal(0, close * 0.005)
                open_price = prices[i-1] + gap
            
            high_move = abs(np.random.normal(0, close * 0.01))
            low_move = abs(np.random.normal(0, close * 0.01))
            
            high = max(open_price, close) + high_move
            low = min(open_price, close) - low_move
            
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = int(1000000 * np.random.uniform(0.8, 1.2))
            
            data.append({
                'timestamp': date,
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close, 2),
                'volume': volume
            })
        
        return pd.DataFrame(data)


# ========================================
# Predefined Test Data Sets
# ========================================

def get_standard_test_data() -> Dict[str, pd.DataFrame]:
    """
    Get standard test data sets for integration testing
    
    Returns:
        Dict with predefined test data sets
    """
    generator = HistoricalDataGenerator(seed=42)
    
    # Single symbol data
    aapl_data = generator.generate_single_symbol_data(
        symbol='AAPL',
        start_date='2023-01-01',
        end_date='2023-12-31',
        timeframe='1D'
    )
    
    # Multi-symbol data
    multi_symbol_data = generator.generate_multi_symbol_data(
        symbols=['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY'],
        start_date='2023-01-01',
        end_date='2023-12-31',
        timeframe='1D'
    )
    
    # Regime-specific data
    regime_data = generator.generate_regime_specific_data(
        symbol='TEST',
        regime_periods=[
            {
                'start_date': '2023-01-01',
                'end_date': '2023-06-30',
                'regime_type': 'bull_market',
                'volatility': 0.015,
                'trend': 0.0008
            },
            {
                'start_date': '2023-07-01',
                'end_date': '2023-09-30',
                'regime_type': 'bear_market',
                'volatility': 0.025,
                'trend': -0.0012
            },
            {
                'start_date': '2023-10-01',
                'end_date': '2023-12-31',
                'regime_type': 'sideways_market',
                'volatility': 0.012,
                'trend': 0.0001
            }
        ]
    )
    
    return {
        'aapl_daily': aapl_data,
        'multi_symbol_daily': multi_symbol_data,
        'regime_specific': regime_data
    }


def get_known_regime_test_data() -> pd.DataFrame:
    """
    Get test data with known regime characteristics for validation
    
    Returns:
        DataFrame with known regime labels
    """
    generator = RegimeTestDataGenerator(seed=42)
    
    return generator.generate_known_regime_data(
        symbol='VALIDATION',
        start_date='2023-01-01',
        end_date='2023-12-31',
        regime_specifications=[
            {
                'regime_name': 'bull_low_vol',
                'start_date': '2023-01-01',
                'end_date': '2023-03-31',
                'daily_return': 0.001,
                'volatility': 0.012,
                'trend_strength': 0.3,
                'confidence': 0.9
            },
            {
                'regime_name': 'bear_high_vol',
                'start_date': '2023-04-01',
                'end_date': '2023-06-30',
                'daily_return': -0.0015,
                'volatility': 0.028,
                'trend_strength': -0.4,
                'confidence': 0.85
            },
            {
                'regime_name': 'sideways_normal_vol',
                'start_date': '2023-07-01',
                'end_date': '2023-12-31',
                'daily_return': 0.0002,
                'volatility': 0.015,
                'trend_strength': 0.1,
                'confidence': 0.7
            }
        ]
    )


if __name__ == "__main__":
    """
    Generate and save test data for integration testing
    """
    import os
    
    # Create test data directory
    test_data_dir = "tests/integration/test_data"
    os.makedirs(test_data_dir, exist_ok=True)
    
    # Generate standard test data
    standard_data = get_standard_test_data()
    
    for name, data in standard_data.items():
        filepath = os.path.join(test_data_dir, f"{name}.csv")
        data.to_csv(filepath, index=False)
        print(f"Generated {name}: {len(data)} rows -> {filepath}")
    
    # Generate known regime test data
    known_regime_data = get_known_regime_test_data()
    filepath = os.path.join(test_data_dir, "known_regime_validation.csv")
    known_regime_data.to_csv(filepath, index=False)
    print(f"Generated known regime data: {len(known_regime_data)} rows -> {filepath}")
    
    print("\n✅ Test data generation completed!")
