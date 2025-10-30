"""
Coverage-focused tests for EnhancedFeatureEngineer to achieve 100% coverage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from core_engine.processing.features.engineer import EnhancedFeatureEngineer, FeatureConfig
from core_engine.system.interfaces import ISystemComponent, IRegimeAware


class TestMissingCoverage:
    """Test methods and branches that are missing coverage"""
    
    @pytest.fixture
    def engineer(self):
        """Create feature engineer instance"""
        config = FeatureConfig(
            use_normalization=True,
            normalization_method='zscore',
            enable_cross_sectional=True,
            max_features=100,
            lookback_periods=[5, 10, 20],
            lag_periods=[1, 2, 3]
        )
        return EnhancedFeatureEngineer(config)
    
    @pytest.fixture
    def clean_sample_data(self):
        """Create clean sample data without _NoValueType issues"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'timestamp': dates,
            'open': 150.0 + np.random.randn(100) * 0.5,
            'high': 151.0 + np.random.randn(100) * 0.5,
            'low': 149.0 + np.random.randn(100) * 0.5,
            'close': 150.5 + np.random.randn(100) * 0.5,
            'volume': 1000000 + np.random.randn(100) * 100000,
            'sma_10': 150.0 + np.random.randn(100) * 0.3,
            'sma_20': 150.0 + np.random.randn(100) * 0.3,
            'rsi_14': 50.0 + np.random.randn(100) * 10,
            'bb_upper_20': 152.0 + np.random.randn(100) * 0.3,
            'bb_lower_20': 148.0 + np.random.randn(100) * 0.3,
            'atr_14': 1.0 + np.random.randn(100) * 0.1,
            'macd': np.random.randn(100) * 0.5,
            'macd_signal': np.random.randn(100) * 0.5,
            'macd_histogram': np.random.randn(100) * 0.2,
            'adx_14': 20.0 + np.random.randn(100) * 5,
            'stoch_k': 50.0 + np.random.randn(100) * 20,
            'stoch_d': 50.0 + np.random.randn(100) * 20,
            'cci_14': np.random.randn(100) * 50,
            'williams_r': -50.0 + np.random.randn(100) * 20,
            'roc_10': np.random.randn(100) * 2,
            'momentum_10': np.random.randn(100) * 2,
            'obv': np.cumsum(np.random.randn(100) * 1000),
            'volume_ma_20': 1000000 + np.random.randn(100) * 100000,
            'vwap': 150.0 + np.random.randn(100) * 0.3,
            'mfi_14': 50.0 + np.random.randn(100) * 20,
            'ad_line': np.cumsum(np.random.randn(100) * 1000),
            'return_1d': np.random.randn(100) * 0.02,
            'return_5d': np.random.randn(100) * 0.05,
            'log_return': np.random.randn(100) * 0.02,
            'price_momentum': np.random.randn(100) * 0.02,
            'volatility_20d': np.random.randn(100) * 0.01,
            'volume_change': np.random.randn(100) * 0.1,
            'hl_ratio': 1.0 + np.random.randn(100) * 0.01,
            'symbol': ['AAPL'] * 100
        })
    
    def test_create_features_with_clean_data(self, engineer, clean_sample_data):
        """Test create_features with clean data to avoid _NoValueType issues"""
        result = engineer.create_features({'AAPL': clean_sample_data})
        
        # Should return a dictionary with symbol as key
        assert isinstance(result, dict)
        assert 'AAPL' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
        
        # Should have created features
        assert len(result['AAPL'].columns) > len(clean_sample_data.columns)
    
    def test_create_price_features_clean(self, engineer, clean_sample_data):
        """Test price feature creation with clean data"""
        result = engineer._create_price_features(clean_sample_data)
        
        # Check that price features are created
        expected_features = ['return_1d', 'return_5d', 'log_return', 'price_momentum']
        for feature in expected_features:
            assert feature in result.columns
        
        # Check that original data is preserved
        assert 'close' in result.columns
        assert 'open' in result.columns
        assert 'high' in result.columns
        assert 'low' in result.columns
    
    def test_create_volatility_features_clean(self, engineer, clean_sample_data):
        """Test volatility feature creation with clean data"""
        result = engineer._create_volatility_features(clean_sample_data)
        
        # Check that volatility features are created
        assert 'vol_clustering' in result.columns
        
        # Check that original data is preserved
        assert 'close' in result.columns
    
    def test_create_momentum_features_clean(self, engineer, clean_sample_data):
        """Test momentum feature creation with clean data"""
        result = engineer._create_momentum_features(clean_sample_data)
        
        # Check that momentum features are created
        expected_features = ['momentum_20', 'momentum_50', 'trend_strength', 'macd_divergence', 'macd_bullish', 'macd_hist_momentum', 'stoch_oversold', 'stoch_overbought', 'stoch_crossover', 'roc_10_normalized']
        for feature in expected_features:
            assert feature in result.columns
        
        # Check that original data is preserved
        assert 'close' in result.columns
    
    def test_create_volume_features_clean(self, engineer, clean_sample_data):
        """Test volume feature creation with clean data"""
        result = engineer._create_volume_features(clean_sample_data)
        
        # Check that volume features are created
        expected_features = ['volume_acceleration', 'volume_price_trend', 'obv_momentum', 'obv_divergence']
        for feature in expected_features:
            assert feature in result.columns
        
        # Check that original data is preserved
        assert 'volume' in result.columns
    
    def test_create_rolling_features_clean(self, engineer, clean_sample_data):
        """Test rolling feature creation with clean data"""
        result = engineer._create_rolling_features(clean_sample_data)
        
        # Check that rolling features are created for base features
        base_features = ['close', 'volume', 'return_1d']
        for feature in base_features:
            if feature in clean_sample_data.columns:
                for period in engineer.config.lookback_periods:
                    assert f'{feature}_mean_{period}' in result.columns
                    assert f'{feature}_std_{period}' in result.columns
                    assert f'{feature}_skew_{period}' in result.columns
                    assert f'{feature}_rank_{period}' in result.columns
    
    def test_create_lag_features_clean(self, engineer, clean_sample_data):
        """Test lag feature creation with clean data"""
        result = engineer._create_lag_features(clean_sample_data)
        
        # Check that lag features are created for base features
        base_features = ['close', 'volume', 'return_1d']
        for feature in base_features:
            if feature in clean_sample_data.columns:
                for lag in engineer.config.lag_periods:
                    assert f'{feature}_lag_{lag}' in result.columns
    
    def test_create_cross_sectional_features_clean(self, engineer, clean_sample_data):
        """Test cross-sectional feature creation with clean data"""
        result = engineer._create_cross_sectional_features(clean_sample_data)
        
        # Check that cross-sectional features are created
        cs_features = ['close', 'volume', 'return_1d']
        for feature in cs_features:
            if feature in clean_sample_data.columns:
                assert f'{feature}_cs_rank' in result.columns
                assert f'{feature}_cs_zscore' in result.columns
                assert f'{feature}_cs_quintile' in result.columns
    
    def test_create_technical_features_clean(self, engineer, clean_sample_data):
        """Test technical feature creation with clean data"""
        result = engineer._create_technical_features(clean_sample_data)
        
        # Check that technical features are created
        expected_features = ['trend_strength', 'trend_direction', 'ma_crossovers']
        for feature in expected_features:
            assert feature in result.columns
        
        # Check that original data is preserved
        assert 'close' in result.columns
    
    def test_normalize_features_zscore(self, engineer):
        """Test z-score normalization"""
        # Create test data with different scales
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [100, 200, 300, 400, 500],
            'feature3': [0.1, 0.2, 0.3, 0.4, 0.5]
        })
        
        result = engineer._normalize_features(data)
        
        # Check that all features are normalized
        for col in result.columns:
            if col in data.columns:
                # Z-score normalization should have mean ~0 and std ~1
                assert abs(result[col].mean()) < 0.1
                assert abs(result[col].std() - 1.0) < 0.1
    
    def test_normalize_features_minmax(self, engineer):
        """Test min-max normalization"""
        engineer.config.normalization_method = 'minmax'
        
        # Create test data
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [100, 200, 300, 400, 500]
        })
        
        result = engineer._normalize_features(data)
        
        # Check that all features are normalized to [0, 1]
        for col in result.columns:
            if col in data.columns:
                assert result[col].min() >= 0.0
                assert result[col].max() <= 1.0
    
    def test_normalize_features_robust(self, engineer):
        """Test robust normalization"""
        engineer.config.normalization_method = 'robust'
        
        # Create test data with outliers
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5, 100],  # outlier
            'feature2': [100, 200, 300, 400, 500, 1000]  # outlier
        })
        
        result = engineer._normalize_features(data)
        
        # Check that features are normalized (robust to outliers)
        for col in result.columns:
            if col in data.columns:
                # Robust normalization should handle outliers better
                assert not result[col].isna().all()
    
    def test_normalize_features_no_normalization(self, engineer):
        """Test when normalization is disabled"""
        engineer.config.use_normalization = False
        
        # Create test data
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [100, 200, 300, 400, 500]
        })
        
        result = engineer._normalize_features(data)
        
        # Check that data is unchanged
        pd.testing.assert_frame_equal(result, data)
    
    def test_analyze_feature_importance(self, engineer):
        """Test feature importance analysis"""
        # Create test data with features
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10],
            'feature3': [0.1, 0.2, 0.3, 0.4, 0.5],
            'target': [1, 2, 3, 4, 5]  # target variable
        })
        
        result = engineer.analyze_feature_importance(data, 'target')
        
        # Check that importance scores are calculated
        assert 'feature_importance' in result
        assert len(result['feature_importance']) > 0
        
        # Check that importance scores are between 0 and 1
        for score in result['feature_importance'].values():
            assert 0 <= score <= 1
    
    def test_analyze_feature_correlation(self, engineer):
        """Test feature correlation analysis"""
        # Create test data with correlated features
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5],
            'feature2': [2, 4, 6, 8, 10],  # highly correlated with feature1
            'feature3': [0.1, 0.2, 0.3, 0.4, 0.5],  # moderately correlated
            'feature4': [5, 4, 3, 2, 1]  # negatively correlated
        })
        
        result = engineer.analyze_feature_correlation(data)
        
        # Check that correlation matrix is calculated
        assert 'correlation_matrix' in result
        assert 'high_correlations' in result
        
        # Check that high correlations are identified
        assert len(result['high_correlations']) > 0
    
    def test_analyze_feature_stability(self, engineer):
        """Test feature stability analysis"""
        # Create test data with stable and unstable features
        data = pd.DataFrame({
            'stable_feature': [1, 1.1, 1.2, 1.3, 1.4],  # stable
            'unstable_feature': [1, 10, 0.1, 100, 0.01],  # unstable
            'feature3': [1, 2, 3, 4, 5]  # moderate stability
        })
        
        result = engineer.analyze_feature_stability(data)
        
        # Check that stability scores are calculated
        assert 'stability_scores' in result
        assert len(result['stability_scores']) > 0
        
        # Check that stability scores are between 0 and 1
        for score in result['stability_scores'].values():
            assert 0 <= score <= 1
    
    def test_get_performance_metrics(self, engineer):
        """Test performance metrics retrieval"""
        # Initialize the engineer
        engineer.initialize()
        engineer.start()
        
        # Get performance metrics
        metrics = engineer.get_performance_metrics()
        
        # Check that metrics are returned
        assert isinstance(metrics, dict)
        assert 'operational_metrics' in metrics
        assert 'resource_metrics' in metrics
        assert 'business_metrics' in metrics
        assert 'health_indicators' in metrics
    
    def test_update_performance_metrics(self, engineer):
        """Test performance metrics update"""
        # Initialize the engineer
        engineer.initialize()
        engineer.start()
        
        # Update performance metrics
        engineer._update_performance_metrics()
        
        # Check that metrics are updated
        metrics = engineer.get_performance_metrics()
        assert 'operational_metrics' in metrics
    
    def test_health_check_detailed(self, engineer):
        """Test detailed health check"""
        # Initialize the engineer
        engineer.initialize()
        engineer.start()
        
        # Get health check
        health = engineer.health_check()
        
        # Check that health check returns expected structure
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'component_type' in health
        assert 'performance_metrics' in health
        assert 'error_count' in health
        assert 'last_error' in health
    
    def test_adapt_to_regime_high_volatility(self, engineer):
        """Test adaptation to high volatility regime"""
        from core_engine.system.interfaces import RegimeContext
        
        # Create high volatility regime
        regime = RegimeContext(
            primary_regime='high_volatility',
            regime_confidence=0.9,
            regime_start_time=datetime.now(),
            regime_duration_minutes=60.0
        )
        
        # Adapt to regime
        result = engineer.adapt_to_regime(regime)
        
        # Check that adaptation is successful
        assert isinstance(result, dict)
        assert 'regime_adaptation' in result
        assert 'feature_adjustments' in result
    
    def test_adapt_to_regime_low_volatility(self, engineer):
        """Test adaptation to low volatility regime"""
        from core_engine.system.interfaces import RegimeContext
        
        # Create low volatility regime
        regime = RegimeContext(
            primary_regime='low_volatility',
            regime_confidence=0.8,
            regime_start_time=datetime.now(),
            regime_duration_minutes=120.0
        )
        
        # Adapt to regime
        result = engineer.adapt_to_regime(regime)
        
        # Check that adaptation is successful
        assert isinstance(result, dict)
        assert 'regime_adaptation' in result
        assert 'feature_adjustments' in result
    
    def test_adapt_to_regime_trending(self, engineer):
        """Test adaptation to trending regime"""
        from core_engine.system.interfaces import RegimeContext
        
        # Create trending regime
        regime = RegimeContext(
            primary_regime='trending',
            regime_confidence=0.85,
            regime_start_time=datetime.now(),
            regime_duration_minutes=90.0
        )
        
        # Adapt to regime
        result = engineer.adapt_to_regime(regime)
        
        # Check that adaptation is successful
        assert isinstance(result, dict)
        assert 'regime_adaptation' in result
        assert 'feature_adjustments' in result
    
    def test_get_feature_metadata(self, engineer):
        """Test feature metadata retrieval"""
        # Get feature metadata
        metadata = engineer.get_feature_metadata()
        
        # Check that metadata is returned
        assert isinstance(metadata, dict)
        assert 'feature_categories' in metadata
        assert 'feature_descriptions' in metadata
        assert 'feature_dependencies' in metadata
    
    def test_update_feature_metadata(self, engineer):
        """Test feature metadata update"""
        # Update feature metadata
        engineer.update_feature_metadata('test_feature', {
            'category': 'test',
            'description': 'Test feature',
            'dependencies': ['close', 'volume']
        })
        
        # Get updated metadata
        metadata = engineer.get_feature_metadata()
        
        # Check that metadata is updated
        assert 'test_feature' in metadata['feature_descriptions']
        assert metadata['feature_descriptions']['test_feature'] == 'Test feature'
    
    def test_get_feature_categories(self, engineer):
        """Test feature categories retrieval"""
        # Get feature categories
        categories = engineer.get_feature_categories()
        
        # Check that categories are returned
        assert isinstance(categories, dict)
        assert 'price' in categories
        assert 'volume' in categories
        assert 'momentum' in categories
        assert 'volatility' in categories
    
    def test_get_feature_dependencies(self, engineer):
        """Test feature dependencies retrieval"""
        # Get feature dependencies
        dependencies = engineer.get_feature_dependencies()
        
        # Check that dependencies are returned
        assert isinstance(dependencies, dict)
        # Should have dependencies for various features
        assert len(dependencies) > 0
    
    def test_create_features_with_nan_values(self, engineer):
        """Test feature creation with NaN values"""
        # Create data with NaN values
        data = pd.DataFrame({
            'close': [100, 101, np.nan, 103, 104],
            'volume': [1000, 1100, 1200, np.nan, 1400],
            'sma_10': [100, 101, 102, 103, np.nan],
            'symbol': ['AAPL'] * 5
        })
        
        # Should not raise an error
        result = engineer.create_features({'AAPL': data})
        
        # Should return a DataFrame
        assert isinstance(result, dict)
        assert 'AAPL' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
    
    def test_create_features_with_inf_values(self, engineer):
        """Test feature creation with infinite values"""
        # Create data with infinite values
        data = pd.DataFrame({
            'close': [100, 101, np.inf, 103, 104],
            'volume': [1000, 1100, 1200, -np.inf, 1400],
            'sma_10': [100, 101, 102, 103, 104],
            'symbol': ['AAPL'] * 5
        })
        
        # Should not raise an error
        result = engineer.create_features({'AAPL': data})
        
        # Should return a DataFrame
        assert isinstance(result, dict)
        assert 'AAPL' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
    
    def test_create_features_with_zero_values(self, engineer):
        """Test feature creation with zero values"""
        # Create data with zero values
        data = pd.DataFrame({
            'close': [100, 101, 0, 103, 104],
            'volume': [1000, 1100, 1200, 0, 1400],
            'sma_10': [100, 101, 102, 103, 104],
            'symbol': ['AAPL'] * 5
        })
        
        # Should not raise an error
        result = engineer.create_features({'AAPL': data})
        
        # Should return a DataFrame
        assert isinstance(result, dict)
        assert 'AAPL' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
    
    def test_create_features_with_negative_values(self, engineer):
        """Test feature creation with negative values"""
        # Create data with negative values
        data = pd.DataFrame({
            'close': [100, 101, -50, 103, 104],  # negative price
            'volume': [1000, 1100, 1200, 1300, 1400],
            'sma_10': [100, 101, 102, 103, 104],
            'symbol': ['AAPL'] * 5
        })
        
        # Should not raise an error
        result = engineer.create_features({'AAPL': data})
        
        # Should return a DataFrame
        assert isinstance(result, dict)
        assert 'AAPL' in result
        assert isinstance(result['AAPL'], pd.DataFrame)
