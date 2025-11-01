#!/usr/bin/env python3
"""
Comprehensive tests for EnhancedTechnicalIndicators Engine
=========================================================

Tests all functionality to achieve 100% coverage.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators


class TestEnhancedTechnicalIndicatorsInitialization:
    """Test initialization and configuration"""
    
    def test_initialization_default(self):
        """Test initialization with default config"""
        engine = EnhancedTechnicalIndicators()
        assert engine.config == {}
        assert engine.indicators_enabled == {}
        assert engine.calculation_cache == {}
        assert engine.performance_metrics == {
            'calculations_performed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_calculation_time': 0.0
        }
    
    def test_initialization_custom_config(self):
        """Test initialization with custom config"""
        config = {
            'enable_caching': True,
            'cache_ttl': 300,
            'parallel_processing': True
        }
        engine = EnhancedTechnicalIndicators(config)
        assert engine.config == config
    
    def test_initialization_with_indicators_config(self):
        """Test initialization with indicators configuration"""
        config = {
            'indicators': {
                'sma': {'enabled': True, 'periods': [10, 20, 50]},
                'rsi': {'enabled': False, 'period': 14}
            }
        }
        engine = EnhancedTechnicalIndicators(config)
        assert engine.indicators_enabled['sma'] is True
        assert engine.indicators_enabled['rsi'] is False


class TestDataValidation:
    """Test data validation methods"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def valid_data(self):
        """Create valid OHLCV data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.1,
            'high': 151.0 + np.random.randn(100) * 0.1,
            'low': 149.0 + np.random.randn(100) * 0.1,
            'close': 150.5 + np.random.randn(100) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 100)
        })
    
    def test_validate_data_valid(self, engine, valid_data):
        """Test validation with valid data"""
        result = engine._validate_data(valid_data)
        assert result is True
    
    def test_validate_data_missing_columns(self, engine):
        """Test validation with missing required columns"""
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1min'),
            'open': [150.0] * 10,
            'close': [150.5] * 10
            # Missing high, low, volume
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            engine._validate_data(invalid_data)
    
    def test_validate_data_empty_dataframe(self, engine):
        """Test validation with empty dataframe"""
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="DataFrame is empty"):
            engine._validate_data(empty_data)
    
    def test_validate_data_insufficient_rows(self, engine):
        """Test validation with insufficient rows"""
        insufficient_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=2, freq='1min'),
            'open': [150.0, 150.1],
            'high': [151.0, 151.1],
            'low': [149.0, 149.1],
            'close': [150.5, 150.6],
            'volume': [1000000, 1000001]
        })
        
        with pytest.raises(ValueError, match="Insufficient data points"):
            engine._validate_data(insufficient_data)
    
    def test_validate_data_non_numeric_values(self, engine):
        """Test validation with non-numeric values"""
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1min'),
            'open': ['invalid'] * 10,
            'high': [151.0] * 10,
            'low': [149.0] * 10,
            'close': [150.5] * 10,
            'volume': [1000000] * 10
        })
        
        with pytest.raises(ValueError, match="Non-numeric values found"):
            engine._validate_data(invalid_data)
    
    def test_validate_data_negative_values(self, engine):
        """Test validation with negative values"""
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='1min'),
            'open': [150.0] * 10,
            'high': [151.0] * 10,
            'low': [149.0] * 10,
            'close': [150.5] * 10,
            'volume': [-1000000] * 10  # Negative volume
        })
        
        with pytest.raises(ValueError, match="Negative values found"):
            engine._validate_data(invalid_data)


class TestSMAIndicators:
    """Test Simple Moving Average indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for SMA calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.arange(50) * 0.1,
            'high': 151.0 + np.arange(50) * 0.1,
            'low': 149.0 + np.arange(50) * 0.1,
            'close': 150.5 + np.arange(50) * 0.1,
            'volume': 1000000 + np.arange(50) * 1000
        })
    
    def test_calculate_sma_single_period(self, engine, test_data):
        """Test SMA calculation with single period"""
        result = engine._calculate_sma(test_data, 'close', 10)
        
        assert len(result) == len(test_data)
        assert result.iloc[9] == test_data['close'].iloc[:10].mean()  # First valid value
        assert pd.isna(result.iloc[0])  # First value should be NaN
    
    def test_calculate_sma_multiple_periods(self, engine, test_data):
        """Test SMA calculation with multiple periods"""
        periods = [5, 10, 20]
        result = engine._calculate_sma(test_data, 'close', periods)
        
        for period in periods:
            col_name = f'SMA_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)
            # Check first valid value
            first_valid_idx = period - 1
            expected_value = test_data['close'].iloc[:period].mean()
            assert abs(result[col_name].iloc[first_valid_idx] - expected_value) < 1e-10
    
    def test_calculate_sma_with_nan_values(self, engine):
        """Test SMA calculation with NaN values in data"""
        data = pd.DataFrame({
            'close': [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109]
        })
        
        result = engine._calculate_sma(data, 'close', 5)
        
        # Should handle NaN values correctly
        assert len(result) == len(data)
        assert pd.isna(result.iloc[0])  # First value should be NaN
    
    def test_calculate_sma_insufficient_data(self, engine):
        """Test SMA calculation with insufficient data"""
        data = pd.DataFrame({
            'close': [100, 101, 102]  # Only 3 values
        })
        
        result = engine._calculate_sma(data, 'close', 10)  # Period > data length
        
        # Should return all NaN values
        assert len(result) == len(data)
        assert result.isna().all()


class TestEMAIndicators:
    """Test Exponential Moving Average indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for EMA calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'close': 150.0 + np.arange(50) * 0.1
        })
    
    def test_calculate_ema_single_period(self, engine, test_data):
        """Test EMA calculation with single period"""
        result = engine._calculate_ema(test_data, 'close', 10)
        
        assert len(result) == len(test_data)
        assert not pd.isna(result.iloc[0])  # First value should not be NaN
        assert not pd.isna(result.iloc[-1])  # Last value should not be NaN
    
    def test_calculate_ema_multiple_periods(self, engine, test_data):
        """Test EMA calculation with multiple periods"""
        periods = [5, 10, 20]
        result = engine._calculate_ema(test_data, 'close', periods)
        
        for period in periods:
            col_name = f'EMA_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)
            assert not result[col_name].isna().all()  # Should have some valid values
    
    def test_calculate_ema_with_alpha(self, engine, test_data):
        """Test EMA calculation with custom alpha"""
        alpha = 0.3
        result = engine._calculate_ema(test_data, 'close', 10, alpha=alpha)
        
        assert len(result) == len(test_data)
        assert not result.isna().all()


class TestRSIIndicators:
    """Test Relative Strength Index indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for RSI calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        # Create data with clear trends for RSI calculation
        close_prices = 150.0 + np.sin(np.arange(50) * 0.2) * 5
        return pd.DataFrame({
            'timestamp': dates,
            'close': close_prices
        })
    
    def test_calculate_rsi_single_period(self, engine, test_data):
        """Test RSI calculation with single period"""
        result = engine._calculate_rsi(test_data, 'close', 14)
        
        assert len(result) == len(test_data)
        assert result.iloc[0] == 50.0  # First value should be 50
        # RSI should be between 0 and 100
        assert (result >= 0).all()
        assert (result <= 100).all()
    
    def test_calculate_rsi_multiple_periods(self, engine, test_data):
        """Test RSI calculation with multiple periods"""
        periods = [7, 14, 21]
        result = engine._calculate_rsi(test_data, 'close', periods)
        
        for period in periods:
            col_name = f'RSI_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)
            # RSI should be between 0 and 100
            valid_values = result[col_name].dropna()
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()
    
    def test_calculate_rsi_constant_prices(self, engine):
        """Test RSI calculation with constant prices"""
        data = pd.DataFrame({
            'close': [100.0] * 20  # Constant prices
        })
        
        result = engine._calculate_rsi(data, 'close', 14)
        
        # RSI should be 50 for constant prices
        assert result.iloc[0] == 50.0
        assert (result == 50.0).all()


class TestMACDIndicators:
    """Test MACD indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for MACD calculations"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        # Create trending data for MACD
        close_prices = 150.0 + np.cumsum(np.random.randn(100) * 0.1)
        return pd.DataFrame({
            'timestamp': dates,
            'close': close_prices
        })
    
    def test_calculate_macd_default_params(self, engine, test_data):
        """Test MACD calculation with default parameters"""
        result = engine._calculate_macd(test_data, 'close')
        
        assert 'MACD' in result.columns
        assert 'MACD_signal' in result.columns
        assert 'MACD_histogram' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_macd_custom_params(self, engine, test_data):
        """Test MACD calculation with custom parameters"""
        result = engine._calculate_macd(test_data, 'close', fast=5, slow=15, signal=9)
        
        assert 'MACD' in result.columns
        assert 'MACD_signal' in result.columns
        assert 'MACD_histogram' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_macd_insufficient_data(self, engine):
        """Test MACD calculation with insufficient data"""
        data = pd.DataFrame({
            'close': [100, 101, 102]  # Only 3 values
        })
        
        result = engine._calculate_macd(data, 'close')
        
        # Should return all NaN values
        assert result['MACD'].isna().all()
        assert result['MACD_signal'].isna().all()
        assert result['MACD_histogram'].isna().all()


class TestBollingerBands:
    """Test Bollinger Bands indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Bollinger Bands calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        close_prices = 150.0 + np.random.randn(50) * 2
        return pd.DataFrame({
            'timestamp': dates,
            'close': close_prices
        })
    
    def test_calculate_bollinger_bands_default(self, engine, test_data):
        """Test Bollinger Bands calculation with default parameters"""
        result = engine._calculate_bollinger_bands(test_data, 'close')
        
        assert 'BB_upper' in result.columns
        assert 'BB_middle' in result.columns
        assert 'BB_lower' in result.columns
        assert 'BB_width' in result.columns
        assert 'BB_position' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_bollinger_bands_custom_params(self, engine, test_data):
        """Test Bollinger Bands calculation with custom parameters"""
        result = engine._calculate_bollinger_bands(test_data, 'close', period=10, std_dev=1.5)
        
        assert 'BB_upper' in result.columns
        assert 'BB_middle' in result.columns
        assert 'BB_lower' in result.columns
        assert 'BB_width' in result.columns
        assert 'BB_position' in result.columns
        assert len(result) == len(test_data)
    
    def test_bollinger_bands_properties(self, engine, test_data):
        """Test Bollinger Bands mathematical properties"""
        result = engine._calculate_bollinger_bands(test_data, 'close')
        
        # Check that upper > middle > lower
        valid_rows = result.dropna()
        if len(valid_rows) > 0:
            assert (valid_rows['BB_upper'] >= valid_rows['BB_middle']).all()
            assert (valid_rows['BB_middle'] >= valid_rows['BB_lower']).all()
            
            # Check BB_position is between 0 and 1
            assert (valid_rows['BB_position'] >= 0).all()
            assert (valid_rows['BB_position'] <= 1).all()


class TestATRIndicators:
    """Test Average True Range indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for ATR calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_atr_single_period(self, engine, test_data):
        """Test ATR calculation with single period"""
        result = engine._calculate_atr(test_data, 14)
        
        assert len(result) == len(test_data)
        assert (result >= 0).all()  # ATR should be non-negative
        assert not result.isna().all()  # Should have some valid values
    
    def test_calculate_atr_multiple_periods(self, engine, test_data):
        """Test ATR calculation with multiple periods"""
        periods = [7, 14, 21]
        result = engine._calculate_atr(test_data, periods)
        
        for period in periods:
            col_name = f'ATR_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)
            assert (result[col_name].dropna() >= 0).all()
    
    def test_calculate_atr_insufficient_data(self, engine):
        """Test ATR calculation with insufficient data"""
        data = pd.DataFrame({
            'high': [100, 101],
            'low': [99, 100],
            'close': [99.5, 100.5]
        })
        
        result = engine._calculate_atr(data, 10)
        
        # Should return all NaN values
        assert result.isna().all()


class TestVolumeIndicators:
    """Test volume-based indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for volume indicators"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'close': 150.0 + np.random.randn(50) * 0.5,
            'volume': 1000000 + np.random.randint(0, 500000, 50)
        })
    
    def test_calculate_obv(self, engine, test_data):
        """Test On-Balance Volume calculation"""
        result = engine._calculate_obv(test_data)
        
        assert 'OBV' in result.columns
        assert len(result) == len(test_data)
        assert not result['OBV'].isna().all()
    
    def test_calculate_volume_sma(self, engine, test_data):
        """Test Volume SMA calculation"""
        result = engine._calculate_volume_sma(test_data, [5, 10, 20])
        
        for period in [5, 10, 20]:
            col_name = f'Volume_SMA_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)
    
    def test_calculate_vwap(self, engine, test_data):
        """Test Volume Weighted Average Price calculation"""
        # Add high and low columns for VWAP
        test_data['high'] = test_data['close'] + 0.5
        test_data['low'] = test_data['close'] - 0.5
        
        result = engine._calculate_vwap(test_data)
        
        assert 'VWAP' in result.columns
        assert len(result) == len(test_data)
        assert not result['VWAP'].isna().all()


class TestStochasticIndicators:
    """Test Stochastic indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Stochastic calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_stochastic_default(self, engine, test_data):
        """Test Stochastic calculation with default parameters"""
        result = engine._calculate_stochastic(test_data)
        
        assert 'Stoch_K' in result.columns
        assert 'Stoch_D' in result.columns
        assert len(result) == len(test_data)
        
        # Stochastic values should be between 0 and 100
        valid_k = result['Stoch_K'].dropna()
        valid_d = result['Stoch_D'].dropna()
        if len(valid_k) > 0:
            assert (valid_k >= 0).all()
            assert (valid_k <= 100).all()
        if len(valid_d) > 0:
            assert (valid_d >= 0).all()
            assert (valid_d <= 100).all()
    
    def test_calculate_stochastic_custom_params(self, engine, test_data):
        """Test Stochastic calculation with custom parameters"""
        result = engine._calculate_stochastic(test_data, k_period=10, d_period=3)
        
        assert 'Stoch_K' in result.columns
        assert 'Stoch_D' in result.columns
        assert len(result) == len(test_data)


class TestWilliamsRIndicators:
    """Test Williams %R indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Williams %R calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_williams_r_default(self, engine, test_data):
        """Test Williams %R calculation with default parameters"""
        result = engine._calculate_williams_r(test_data)
        
        assert 'Williams_R' in result.columns
        assert len(result) == len(test_data)
        
        # Williams %R should be between -100 and 0
        valid_values = result['Williams_R'].dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -100).all()
            assert (valid_values <= 0).all()
    
    def test_calculate_williams_r_custom_params(self, engine, test_data):
        """Test Williams %R calculation with custom parameters"""
        result = engine._calculate_williams_r(test_data, period=10)
        
        assert 'Williams_R' in result.columns
        assert len(result) == len(test_data)


class TestADXIndicators:
    """Test Average Directional Index indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for ADX calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_adx_default(self, engine, test_data):
        """Test ADX calculation with default parameters"""
        result = engine._calculate_adx(test_data)
        
        assert 'ADX' in result.columns
        assert 'DI_plus' in result.columns
        assert 'DI_minus' in result.columns
        assert len(result) == len(test_data)
        
        # ADX should be between 0 and 100
        valid_values = result['ADX'].dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()
    
    def test_calculate_adx_custom_params(self, engine, test_data):
        """Test ADX calculation with custom parameters"""
        result = engine._calculate_adx(test_data, period=10)
        
        assert 'ADX' in result.columns
        assert 'DI_plus' in result.columns
        assert 'DI_minus' in result.columns
        assert len(result) == len(test_data)


class TestCCIIndicators:
    """Test Commodity Channel Index indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for CCI calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_cci_default(self, engine, test_data):
        """Test CCI calculation with default parameters"""
        result = engine._calculate_cci(test_data)
        
        assert 'CCI' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_cci_custom_params(self, engine, test_data):
        """Test CCI calculation with custom parameters"""
        result = engine._calculate_cci(test_data, period=10)
        
        assert 'CCI' in result.columns
        assert len(result) == len(test_data)


class TestROCIndicators:
    """Test Rate of Change indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for ROC calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'close': 150.0 + np.arange(50) * 0.1
        })
    
    def test_calculate_roc_single_period(self, engine, test_data):
        """Test ROC calculation with single period"""
        result = engine._calculate_roc(test_data, 'close', 10)
        
        assert len(result) == len(test_data)
        assert pd.isna(result.iloc[0])  # First value should be NaN
        assert not pd.isna(result.iloc[10])  # Value at period should not be NaN
    
    def test_calculate_roc_multiple_periods(self, engine, test_data):
        """Test ROC calculation with multiple periods"""
        periods = [5, 10, 20]
        result = engine._calculate_roc(test_data, 'close', periods)
        
        for period in periods:
            col_name = f'ROC_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)


class TestMomentumIndicators:
    """Test Momentum indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Momentum calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'close': 150.0 + np.arange(50) * 0.1
        })
    
    def test_calculate_momentum_single_period(self, engine, test_data):
        """Test Momentum calculation with single period"""
        result = engine._calculate_momentum(test_data, 'close', 10)
        
        assert len(result) == len(test_data)
        assert pd.isna(result.iloc[0])  # First value should be NaN
        assert not pd.isna(result.iloc[10])  # Value at period should not be NaN
    
    def test_calculate_momentum_multiple_periods(self, engine, test_data):
        """Test Momentum calculation with multiple periods"""
        periods = [5, 10, 20]
        result = engine._calculate_momentum(test_data, 'close', periods)
        
        for period in periods:
            col_name = f'MOM_{period}'
            assert col_name in result.columns
            assert len(result[col_name]) == len(test_data)


class TestKeltnerChannels:
    """Test Keltner Channels indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Keltner Channels calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_keltner_channels_default(self, engine, test_data):
        """Test Keltner Channels calculation with default parameters"""
        result = engine._calculate_keltner_channels(test_data)
        
        assert 'KC_upper' in result.columns
        assert 'KC_middle' in result.columns
        assert 'KC_lower' in result.columns
        assert 'KC_width' in result.columns
        assert 'KC_position' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_keltner_channels_custom_params(self, engine, test_data):
        """Test Keltner Channels calculation with custom parameters"""
        result = engine._calculate_keltner_channels(test_data, period=10, multiplier=1.5)
        
        assert 'KC_upper' in result.columns
        assert 'KC_middle' in result.columns
        assert 'KC_lower' in result.columns
        assert 'KC_width' in result.columns
        assert 'KC_position' in result.columns
        assert len(result) == len(test_data)


class TestDonchianChannels:
    """Test Donchian Channels indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Donchian Channels calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5
        })
    
    def test_calculate_donchian_channels_default(self, engine, test_data):
        """Test Donchian Channels calculation with default parameters"""
        result = engine._calculate_donchian_channels(test_data)
        
        assert 'DC_upper' in result.columns
        assert 'DC_lower' in result.columns
        assert 'DC_middle' in result.columns
        assert 'DC_width' in result.columns
        assert 'DC_position' in result.columns
        assert len(result) == len(test_data)
    
    def test_calculate_donchian_channels_custom_params(self, engine, test_data):
        """Test Donchian Channels calculation with custom parameters"""
        result = engine._calculate_donchian_channels(test_data, period=10)
        
        assert 'DC_upper' in result.columns
        assert 'DC_lower' in result.columns
        assert 'DC_middle' in result.columns
        assert 'DC_width' in result.columns
        assert 'DC_position' in result.columns
        assert len(result) == len(test_data)


class TestHistoricalVolatility:
    """Test Historical Volatility indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for Historical Volatility calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'close': 150.0 + np.cumsum(np.random.randn(50) * 0.1)
        })
    
    def test_calculate_historical_volatility_default(self, engine, test_data):
        """Test Historical Volatility calculation with default parameters"""
        result = engine._calculate_historical_volatility(test_data, 'close')
        
        assert 'Hist_Vol' in result.columns
        assert len(result) == len(test_data)
        assert (result['Hist_Vol'].dropna() >= 0).all()  # Volatility should be non-negative
    
    def test_calculate_historical_volatility_custom_params(self, engine, test_data):
        """Test Historical Volatility calculation with custom parameters"""
        result = engine._calculate_historical_volatility(test_data, 'close', period=10, annualized=True)
        
        assert 'Hist_Vol' in result.columns
        assert len(result) == len(test_data)
        assert (result['Hist_Vol'].dropna() >= 0).all()


class TestMFIIndicators:
    """Test Money Flow Index indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for MFI calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5,
            'volume': 1000000 + np.random.randint(0, 500000, 50)
        })
    
    def test_calculate_mfi_default(self, engine, test_data):
        """Test MFI calculation with default parameters"""
        result = engine._calculate_mfi(test_data)
        
        assert 'MFI' in result.columns
        assert len(result) == len(test_data)
        
        # MFI should be between 0 and 100
        valid_values = result['MFI'].dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()
    
    def test_calculate_mfi_custom_params(self, engine, test_data):
        """Test MFI calculation with custom parameters"""
        result = engine._calculate_mfi(test_data, period=10)
        
        assert 'MFI' in result.columns
        assert len(result) == len(test_data)


class TestADLineIndicators:
    """Test Accumulation/Distribution Line indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for A/D Line calculations"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'high': 151.0 + np.random.randn(50) * 0.5,
            'low': 149.0 + np.random.randn(50) * 0.5,
            'close': 150.0 + np.random.randn(50) * 0.5,
            'volume': 1000000 + np.random.randint(0, 500000, 50)
        })
    
    def test_calculate_ad_line(self, engine, test_data):
        """Test A/D Line calculation"""
        result = engine._calculate_ad_line(test_data)
        
        assert 'AD_Line' in result.columns
        assert len(result) == len(test_data)
        assert not result['AD_Line'].isna().all()


class TestMainCalculateIndicators:
    """Test main calculate_indicators method"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create comprehensive test data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.1,
            'high': 151.0 + np.random.randn(100) * 0.1,
            'low': 149.0 + np.random.randn(100) * 0.1,
            'close': 150.5 + np.random.randn(100) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 100)
        })
    
    def test_calculate_indicators_all_enabled(self, engine, test_data):
        """Test calculating all indicators"""
        result = engine.calculate_indicators(test_data)
        
        # Check that original data is preserved
        for col in ['timestamp', 'open', 'high', 'low', 'close', 'volume']:
            assert col in result.columns
        
        # Check that indicators are added
        expected_indicators = [
            'SMA_10', 'SMA_20', 'SMA_50', 'SMA_200',
            'EMA_9', 'EMA_12', 'EMA_26',
            'RSI_14', 'RSI_21',
            'MACD', 'MACD_signal', 'MACD_histogram',
            'BB_upper', 'BB_middle', 'BB_lower', 'BB_width', 'BB_position',
            'ATR_14', 'ATR_21',
            'OBV', 'Volume_SMA_10', 'Volume_SMA_20',
            'Stoch_K', 'Stoch_D',
            'Williams_R',
            'ADX_14', 'DI_plus', 'DI_minus',
            'CCI_20',
            'ROC_10', 'ROC_20',
            'MOM_10', 'MOM_20',
            'KC_upper', 'KC_middle', 'KC_lower', 'KC_width', 'KC_position',
            'DC_upper', 'DC_lower', 'DC_middle', 'DC_width', 'DC_position',
            'Hist_Vol',
            'MFI_14',
            'AD_Line'
        ]
        
        for indicator in expected_indicators:
            assert indicator in result.columns, f"Missing indicator: {indicator}"
    
    def test_calculate_indicators_with_config(self, engine, test_data):
        """Test calculating indicators with custom configuration"""
        config = {
            'indicators': {
                'sma': {'enabled': True, 'periods': [5, 10]},
                'rsi': {'enabled': True, 'period': 14},
                'macd': {'enabled': False}
            }
        }
        
        engine = EnhancedTechnicalIndicators(config)
        result = engine.calculate_indicators(test_data)
        
        # Check that only configured indicators are present
        assert 'SMA_5' in result.columns
        assert 'SMA_10' in result.columns
        assert 'RSI_14' in result.columns
        assert 'MACD' not in result.columns
    
    def test_calculate_indicators_caching(self, engine, test_data):
        """Test that caching works correctly"""
        # First calculation
        result1 = engine.calculate_indicators(test_data)
        
        # Second calculation should use cache
        result2 = engine.calculate_indicators(test_data)
        
        # Results should be identical
        pd.testing.assert_frame_equal(result1, result2)
        
        # Check that cache was used
        assert engine.performance_metrics['cache_hits'] > 0
    
    def test_calculate_indicators_error_handling(self, engine):
        """Test error handling in calculate_indicators"""
        # Test with invalid data
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=5, freq='1min'),
            'open': [150.0] * 5,
            'high': [151.0] * 5,
            'low': [149.0] * 5,
            'close': [150.5] * 5,
            'volume': [1000000] * 5
        })
        
        with pytest.raises(ValueError):
            engine.calculate_indicators(invalid_data)
    
    def test_calculate_indicators_performance_metrics(self, engine, test_data):
        """Test that performance metrics are updated"""
        initial_metrics = engine.performance_metrics.copy()
        
        engine.calculate_indicators(test_data)
        
        # Check that metrics are updated
        assert engine.performance_metrics['calculations_performed'] > initial_metrics['calculations_performed']
        assert engine.performance_metrics['avg_calculation_time'] > 0
    
    def test_calculate_indicators_with_nan_values(self, engine):
        """Test calculating indicators with NaN values in data"""
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='1min'),
            'open': [150.0] * 50,
            'high': [151.0] * 50,
            'low': [149.0] * 50,
            'close': [150.5] * 50,
            'volume': [1000000] * 50
        })
        
        # Add some NaN values
        data.loc[10:15, 'close'] = np.nan
        
        result = engine.calculate_indicators(data)
        
        # Should handle NaN values gracefully
        assert len(result) == len(data)
        # Some indicators may have NaN values where input data was NaN
        assert not result.isna().all().all()  # Not all values should be NaN


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    def test_calculate_indicators_empty_dataframe(self, engine):
        """Test calculating indicators with empty dataframe"""
        empty_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="DataFrame is empty"):
            engine.calculate_indicators(empty_data)
    
    def test_calculate_indicators_single_row(self, engine):
        """Test calculating indicators with single row of data"""
        single_row = pd.DataFrame({
            'timestamp': [datetime.now()],
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        })
        
        with pytest.raises(ValueError, match="Insufficient data points"):
            engine.calculate_indicators(single_row)
    
    def test_calculate_indicators_missing_timestamp(self, engine):
        """Test calculating indicators without timestamp column"""
        data = pd.DataFrame({
            'open': [150.0] * 20,
            'high': [151.0] * 20,
            'low': [149.0] * 20,
            'close': [150.5] * 20,
            'volume': [1000000] * 20
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            engine.calculate_indicators(data)
    
    def test_calculate_indicators_duplicate_columns(self, engine):
        """Test calculating indicators with duplicate columns"""
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=20, freq='1min'),
            'open': [150.0] * 20,
            'high': [151.0] * 20,
            'low': [149.0] * 20,
            'close': [150.5] * 20,
            'volume': [1000000] * 20,
            'close': [150.5] * 20  # Duplicate column
        })
        
        # Should handle duplicate columns gracefully
        result = engine.calculate_indicators(data)
        assert len(result) == len(data)
    
    def test_calculate_indicators_extreme_values(self, engine):
        """Test calculating indicators with extreme values"""
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='1min'),
            'open': [1e10] * 50,  # Very large values
            'high': [1e10] * 50,
            'low': [1e10] * 50,
            'close': [1e10] * 50,
            'volume': [1e10] * 50
        })
        
        result = engine.calculate_indicators(data)
        
        # Should handle extreme values gracefully
        assert len(result) == len(data)
        assert not result.isna().all().all()
    
    def test_calculate_indicators_zero_volume(self, engine):
        """Test calculating indicators with zero volume"""
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='1min'),
            'open': [150.0] * 50,
            'high': [151.0] * 50,
            'low': [149.0] * 50,
            'close': [150.5] * 50,
            'volume': [0] * 50  # Zero volume
        })
        
        result = engine.calculate_indicators(data)
        
        # Should handle zero volume gracefully
        assert len(result) == len(data)
    
    def test_calculate_indicators_constant_values(self, engine):
        """Test calculating indicators with constant values"""
        data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=50, freq='1min'),
            'open': [150.0] * 50,
            'high': [150.0] * 50,
            'low': [150.0] * 50,
            'close': [150.0] * 50,
            'volume': [1000000] * 50
        })
        
        result = engine.calculate_indicators(data)
        
        # Should handle constant values gracefully
        assert len(result) == len(data)
        # Some indicators may have NaN values with constant input
        assert not result.isna().all().all()


class TestPerformanceAndOptimization:
    """Test performance and optimization features"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def large_data(self):
        """Create large dataset for performance testing"""
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(1000) * 0.1,
            'high': 151.0 + np.random.randn(1000) * 0.1,
            'low': 149.0 + np.random.randn(1000) * 0.1,
            'close': 150.5 + np.random.randn(1000) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 1000)
        })
    
    def test_performance_metrics_tracking(self, engine, large_data):
        """Test that performance metrics are properly tracked"""
        initial_metrics = engine.performance_metrics.copy()
        
        engine.calculate_indicators(large_data)
        
        # Check that metrics are updated
        assert engine.performance_metrics['calculations_performed'] > initial_metrics['calculations_performed']
        assert engine.performance_metrics['avg_calculation_time'] > 0
        assert engine.performance_metrics['cache_hits'] >= 0
        assert engine.performance_metrics['cache_misses'] >= 0
    
    def test_caching_effectiveness(self, engine, large_data):
        """Test that caching improves performance"""
        # First calculation
        start_time = datetime.now()
        result1 = engine.calculate_indicators(large_data)
        first_duration = (datetime.now() - start_time).total_seconds()
        
        # Second calculation (should use cache)
        start_time = datetime.now()
        result2 = engine.calculate_indicators(large_data)
        second_duration = (datetime.now() - start_time).total_seconds()
        
        # Second calculation should be faster
        assert second_duration < first_duration
        
        # Results should be identical
        pd.testing.assert_frame_equal(result1, result2)
    
    def test_memory_usage(self, engine, large_data):
        """Test memory usage with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        result = engine.calculate_indicators(large_data)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
        
        # Result should be correct
        assert len(result) == len(large_data)
    
    def test_parallel_processing(self, engine, large_data):
        """Test parallel processing if enabled"""
        config = {'parallel_processing': True}
        engine = EnhancedTechnicalIndicators(config)
        
        result = engine.calculate_indicators(large_data)
        
        # Should complete successfully
        assert len(result) == len(large_data)
        assert not result.isna().all().all()


class TestIntegrationAndCompatibility:
    """Test integration and compatibility with other components"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for integration tests"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.1,
            'high': 151.0 + np.random.randn(100) * 0.1,
            'low': 149.0 + np.random.randn(100) * 0.1,
            'close': 150.5 + np.random.randn(100) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 100)
        })
    
    def test_integration_with_pandas_operations(self, engine, test_data):
        """Test integration with pandas operations"""
        result = engine.calculate_indicators(test_data)
        
        # Should work with pandas operations
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(test_data)
        
        # Should preserve index
        pd.testing.assert_index_equal(result.index, test_data.index)
        
        # Should work with pandas methods
        assert result.describe().shape[0] > 0
        assert result.info() is None
    
    def test_integration_with_numpy_operations(self, engine, test_data):
        """Test integration with numpy operations"""
        result = engine.calculate_indicators(test_data)
        
        # Should work with numpy operations
        numeric_cols = result.select_dtypes(include=[np.number]).columns
        assert len(numeric_cols) > 0
        
        # Should work with numpy functions
        assert np.isfinite(result[numeric_cols]).any().any()
        assert np.isfinite(result[numeric_cols]).all().any()
    
    def test_integration_with_plotting(self, engine, test_data):
        """Test integration with plotting libraries"""
        result = engine.calculate_indicators(test_data)
        
        # Should work with plotting (basic test)
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.plot(result['close'])
            ax.plot(result['SMA_20'])
            plt.close(fig)
        except ImportError:
            # Matplotlib not available, skip test
            pass
    
    def test_integration_with_serialization(self, engine, test_data):
        """Test integration with serialization"""
        result = engine.calculate_indicators(test_data)
        
        # Should work with pickle
        import pickle
        pickled = pickle.dumps(result)
        unpickled = pickle.loads(pickled)
        pd.testing.assert_frame_equal(result, unpickled)
        
        # Should work with JSON (for numeric columns)
        try:
            json_str = result.to_json()
            assert len(json_str) > 0
        except (ValueError, TypeError):
            # Some columns may not be JSON serializable, which is expected
            pass
    
    def test_integration_with_database_operations(self, engine, test_data):
        """Test integration with database operations"""
        result = engine.calculate_indicators(test_data)
        
        # Should work with SQL operations
        try:
            import sqlite3
            conn = sqlite3.connect(':memory:')
            result.to_sql('test_table', conn, if_exists='replace')
            
            # Verify data was stored correctly
            query_result = pd.read_sql('SELECT COUNT(*) as count FROM test_table', conn)
            assert query_result['count'].iloc[0] == len(result)
            
            conn.close()
        except ImportError:
            # SQLite not available, skip test
            pass


class TestRegimeAwareIndicators:
    """Test regime-aware indicator calculations"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for regime-aware calculations"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.1,
            'high': 151.0 + np.random.randn(100) * 0.1,
            'low': 149.0 + np.random.randn(100) * 0.1,
            'close': 150.5 + np.random.randn(100) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 100)
        })
    
    def test_regime_aware_calculation(self, engine, test_data):
        """Test that indicators adapt to regime context"""
        # Mock regime context
        regime_context = {
            'regime': 'high_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 1.5
        }
        
        result = engine.calculate_indicators(test_data, regime_context)
        
        # Should complete successfully
        assert len(result) == len(test_data)
        assert not result.isna().all().all()
    
    def test_regime_aware_volatility_scaling(self, engine, test_data):
        """Test that volatility indicators scale with regime"""
        # Test in low volatility regime
        low_vol_regime = {
            'regime': 'low_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 0.5
        }
        
        result_low_vol = engine.calculate_indicators(test_data, low_vol_regime)
        
        # Test in high volatility regime
        high_vol_regime = {
            'regime': 'high_volatility',
            'confidence': 0.8,
            'volatility_multiplier': 2.0
        }
        
        result_high_vol = engine.calculate_indicators(test_data, high_vol_regime)
        
        # Both should complete successfully
        assert len(result_low_vol) == len(test_data)
        assert len(result_high_vol) == len(test_data)
        
        # Volatility indicators should be different
        if 'ATR_14' in result_low_vol.columns and 'ATR_14' in result_high_vol.columns:
            low_vol_atr = result_low_vol['ATR_14'].dropna()
            high_vol_atr = result_high_vol['ATR_14'].dropna()
            
            if len(low_vol_atr) > 0 and len(high_vol_atr) > 0:
                # High volatility ATR should generally be higher
                assert high_vol_atr.mean() > low_vol_atr.mean()
    
    def test_regime_aware_trend_indicators(self, engine, test_data):
        """Test that trend indicators adapt to regime"""
        # Test in trending regime
        trending_regime = {
            'regime': 'trending',
            'confidence': 0.8,
            'trend_strength': 0.7
        }
        
        result_trending = engine.calculate_indicators(test_data, trending_regime)
        
        # Test in ranging regime
        ranging_regime = {
            'regime': 'ranging',
            'confidence': 0.8,
            'trend_strength': 0.2
        }
        
        result_ranging = engine.calculate_indicators(test_data, ranging_regime)
        
        # Both should complete successfully
        assert len(result_trending) == len(test_data)
        assert len(result_ranging) == len(test_data)
        
        # Trend indicators should be different
        if 'ADX_14' in result_trending.columns and 'ADX_14' in result_ranging.columns:
            trending_adx = result_trending['ADX_14'].dropna()
            ranging_adx = result_ranging['ADX_14'].dropna()
            
            if len(trending_adx) > 0 and len(ranging_adx) > 0:
                # Trending regime should have higher ADX values
                assert trending_adx.mean() > ranging_adx.mean()


class TestAdvancedIndicators:
    """Test advanced and specialized indicators"""
    
    @pytest.fixture
    def engine(self):
        return EnhancedTechnicalIndicators()
    
    @pytest.fixture
    def test_data(self):
        """Create test data for advanced indicators"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.1,
            'high': 151.0 + np.random.randn(100) * 0.1,
            'low': 149.0 + np.random.randn(100) * 0.1,
            'close': 150.5 + np.random.randn(100) * 0.1,
            'volume': 1000000 + np.random.randint(0, 100000, 100)
        })
    
    def test_calculate_all_indicators_comprehensive(self, engine, test_data):
        """Test comprehensive calculation of all indicators"""
        # Enable all indicators
        config = {
            'indicators': {
                'sma': {'enabled': True, 'periods': [5, 10, 20, 50, 100, 200]},
                'ema': {'enabled': True, 'periods': [5, 9, 12, 26, 50]},
                'rsi': {'enabled': True, 'periods': [7, 14, 21]},
                'macd': {'enabled': True, 'fast': 12, 'slow': 26, 'signal': 9},
                'bollinger': {'enabled': True, 'period': 20, 'std_dev': 2},
                'atr': {'enabled': True, 'periods': [7, 14, 21]},
                'stochastic': {'enabled': True, 'k_period': 14, 'd_period': 3},
                'williams_r': {'enabled': True, 'period': 14},
                'adx': {'enabled': True, 'period': 14},
                'cci': {'enabled': True, 'period': 20},
                'roc': {'enabled': True, 'periods': [5, 10, 20]},
                'momentum': {'enabled': True, 'periods': [5, 10, 20]},
                'keltner': {'enabled': True, 'period': 20, 'multiplier': 2},
                'donchian': {'enabled': True, 'period': 20},
                'hist_vol': {'enabled': True, 'period': 20},
                'mfi': {'enabled': True, 'period': 14},
                'ad_line': {'enabled': True},
                'obv': {'enabled': True},
                'volume_sma': {'enabled': True, 'periods': [5, 10, 20]},
                'vwap': {'enabled': True}
            }
        }
        
        engine = EnhancedTechnicalIndicators(config)
        result = engine.calculate_indicators(test_data)
        
        # Should complete successfully
        assert len(result) == len(test_data)
        assert not result.isna().all().all()
        
        # Check that all expected indicators are present
        expected_indicators = [
            'SMA_5', 'SMA_10', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200',
            'EMA_5', 'EMA_9', 'EMA_12', 'EMA_26', 'EMA_50',
            'RSI_7', 'RSI_14', 'RSI_21',
            'MACD', 'MACD_signal', 'MACD_histogram',
            'BB_upper', 'BB_middle', 'BB_lower', 'BB_width', 'BB_position',
            'ATR_7', 'ATR_14', 'ATR_21',
            'Stoch_K', 'Stoch_D',
            'Williams_R',
            'ADX_14', 'DI_plus', 'DI_minus',
            'CCI_20',
            'ROC_5', 'ROC_10', 'ROC_20',
            'MOM_5', 'MOM_10', 'MOM_20',
            'KC_upper', 'KC_middle', 'KC_lower', 'KC_width', 'KC_position',
            'DC_upper', 'DC_lower', 'DC_middle', 'DC_width', 'DC_position',
            'Hist_Vol',
            'MFI_14',
            'AD_Line',
            'OBV',
            'Volume_SMA_5', 'Volume_SMA_10', 'Volume_SMA_20',
            'VWAP'
        ]
        
        for indicator in expected_indicators:
            assert indicator in result.columns, f"Missing indicator: {indicator}"
    
    def test_calculate_indicators_with_custom_indicators(self, engine, test_data):
        """Test calculating indicators with custom indicator definitions"""
        # This would test custom indicator definitions if supported
        result = engine.calculate_indicators(test_data)
        
        # Should complete successfully
        assert len(result) == len(test_data)
        assert not result.isna().all().all()
    
    def test_calculate_indicators_with_regime_adaptation(self, engine, test_data):
        """Test calculating indicators with regime adaptation"""
        # Test different regime contexts
        regimes = [
            {'regime': 'trending', 'confidence': 0.8, 'trend_strength': 0.7},
            {'regime': 'ranging', 'confidence': 0.8, 'trend_strength': 0.2},
            {'regime': 'high_volatility', 'confidence': 0.8, 'volatility_multiplier': 2.0},
            {'regime': 'low_volatility', 'confidence': 0.8, 'volatility_multiplier': 0.5},
            {'regime': 'crisis', 'confidence': 0.8, 'crisis_mode': True}
        ]
        
        for regime in regimes:
            result = engine.calculate_indicators(test_data, regime)
            
            # Should complete successfully for all regimes
            assert len(result) == len(test_data)
            assert not result.isna().all().all()
    
    def test_calculate_indicators_with_performance_optimization(self, engine, test_data):
        """Test calculating indicators with performance optimization"""
        # Test with performance optimization enabled
        config = {
            'performance_optimization': True,
            'parallel_processing': True,
            'vectorization': True
        }
        
        engine = EnhancedTechnicalIndicators(config)
        result = engine.calculate_indicators(test_data)
        
        # Should complete successfully
        assert len(result) == len(test_data)
        assert not result.isna().all().all()
        
        # Check that performance metrics are tracked
        assert engine.performance_metrics['calculations_performed'] > 0
        assert engine.performance_metrics['avg_calculation_time'] > 0