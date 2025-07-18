"""
Simplified Integration Test for Technical Indicators Modules
============================================================

Quick validation that our specialized modules work correctly
and can integrate with the new_structure architecture.

Author: Pro Trading System
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add the indicators module to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our specialized modules
try:
    from technical_indicators import TechnicalIndicatorEngine, IndicatorConfig
    from polygon_streaming import PolygonStreamingEngine, StreamingConfig
    from feature_engineering import FeatureEngineeringPipeline
    from market_regimes import MarketRegimeDetector
    from indicator_config import IndicatorConfigManager
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def create_test_data() -> pd.DataFrame:
    """Create test OHLCV data"""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    
    # Generate realistic price data
    np.random.seed(42)
    prices = [100]
    
    for i in range(1, 100):
        change = np.random.normal(0, 0.02)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1))
    
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        volatility = 0.02
        open_price = close * (1 + np.random.normal(0, volatility/2))
        high = max(open_price, close) * (1 + np.random.uniform(0, volatility))
        low = min(open_price, close) * (1 - np.random.uniform(0, volatility))
        volume = np.random.uniform(100000, 1000000)
        
        data.append({
            'symbol': 'TEST',
            'date': date,
            'timestamp': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': int(volume)
        })
    
    return pd.DataFrame(data)

def test_technical_indicators():
    """Test technical indicator calculation"""
    print("\n🔧 Testing Technical Indicators...")
    
    # Create test data
    data = create_test_data()
    
    # Configure indicator engine
    config = IndicatorConfig(
        clickhouse_host="localhost",
        polygon_api_key="test_key"
    )
    
    engine = TechnicalIndicatorEngine(config)
    
    # Calculate indicators
    result = engine.calculate_all_indicators(data, "TEST")
    
    # Validate result
    assert result.symbol == "TEST"
    assert len(result.indicators) > 50, f"Expected > 50 indicators, got {len(result.indicators)}"
    assert result.confidence > 0, "Confidence should be > 0"
    
    # Check some specific indicators
    required_indicators = ['sma_20', 'rsi_14', 'macd_line']
    for indicator in required_indicators:
        if indicator in result.indicators:
            assert not np.isnan(result.indicators[indicator]), f"{indicator} should not be NaN"
    
    print(f"   ✅ Calculated {len(result.indicators)} indicators")
    print(f"   ✅ Regime: {result.regime}")
    print(f"   ✅ Confidence: {result.confidence:.2f}")
    
    return True

def test_enhanced_features():
    """Test feature engineering with mock data"""
    print("\n🎯 Testing Feature Engineering...")
    
    # Create enhanced test data with indicators
    data = create_test_data()
    
    # Add some mock indicators
    data['sma_20'] = data['close'].rolling(20).mean()
    data['sma_50'] = data['close'].rolling(50).mean()
    data['ema_12'] = data['close'].ewm(span=12).mean()
    data['ema_26'] = data['close'].ewm(span=26).mean()
    data['rsi_14'] = 50 + np.random.normal(0, 15, len(data))  # Mock RSI
    data['macd_line'] = data['ema_12'] - data['ema_26']
    data['macd_signal'] = data['macd_line'].ewm(span=9).mean()
    data['macd_histogram'] = data['macd_line'] - data['macd_signal']
    
    # Apply feature engineering
    pipeline = FeatureEngineeringPipeline()
    features_df = pipeline.create_all_features(data)
    
    # Validate
    original_cols = len(data.columns)
    feature_cols = len(features_df.columns)
    
    assert feature_cols > original_cols * 5, f"Expected significant feature expansion: {original_cols} -> {feature_cols}"
    
    # Check for key feature categories
    feature_names = features_df.columns.tolist()
    categories = ['momentum', 'volatility', 'trend', 'price']
    
    for category in categories:
        matching = [col for col in feature_names if category in col.lower()]
        assert len(matching) > 0, f"No features found for category: {category}"
    
    print(f"   ✅ Created {feature_cols} features from {original_cols} base columns")
    print(f"   ✅ Feature expansion: {feature_cols/original_cols:.1f}x")
    
    return True

def test_market_regimes():
    """Test market regime detection"""
    print("\n📊 Testing Market Regime Detection...")
    
    # Create test data with indicators
    data = create_test_data()
    
    # Add mock indicators
    data['sma_20'] = data['close'].rolling(20).mean()
    data['sma_50'] = data['close'].rolling(50).mean()
    
    # Detect regimes
    detector = MarketRegimeDetector()
    regime_df = detector.detect_regimes(data)
    
    # Validate
    regime_columns = ['volatility_regime', 'trend_regime', 'ensemble_regime']
    
    for column in regime_columns:
        assert column in regime_df.columns, f"Missing regime column: {column}"
    
    # Check regime values
    vol_regimes = regime_df['volatility_regime'].dropna().unique()
    valid_vol_regimes = ['low', 'medium', 'high']
    
    for regime in vol_regimes:
        assert regime in valid_vol_regimes, f"Invalid volatility regime: {regime}"
    
    print(f"   ✅ Detected regimes: {list(vol_regimes)}")
    print(f"   ✅ Current regime: {regime_df['ensemble_regime'].iloc[-1] if 'ensemble_regime' in regime_df.columns else 'Unknown'}")
    
    return True

def test_configuration():
    """Test configuration management"""
    print("\n⚙️ Testing Configuration Management...")
    
    # Initialize config manager
    config_manager = IndicatorConfigManager()
    
    # Test validation
    issues = config_manager.validate_configuration()
    assert isinstance(issues, list), "Validation should return a list"
    
    # Test production config
    prod_config = config_manager.get_production_config()
    assert 'indicators' in prod_config, "Missing indicators config"
    assert 'streaming' in prod_config, "Missing streaming config"
    
    print(f"   ✅ Configuration validation: {len(issues)} issues found")
    print("   ✅ Production config generated successfully")
    
    return True

def test_streaming_mock():
    """Test streaming engine with mock setup"""
    print("\n📡 Testing Streaming Engine (Mock)...")
    
    # Create streaming config
    config = StreamingConfig(
        polygon_api_key="test_key",
        websocket_url="ws://test.local",
        enable_ssl_verification=False
    )
    
    # Initialize engine
    engine = PolygonStreamingEngine(config)
    
    # Test basic properties
    assert engine.config.polygon_api_key == "test_key"
    assert not engine.config.enable_ssl_verification
    
    print("   ✅ Streaming engine initialized")
    print("   ✅ Configuration validated")
    print("   ✅ SSL settings configured")
    
    return True

def run_comprehensive_test():
    """Run comprehensive integration test"""
    print("🚀 Starting Comprehensive Technical Indicators Test")
    print("=" * 60)
    
    tests = [
        ("Technical Indicators", test_technical_indicators),
        ("Feature Engineering", test_enhanced_features),
        ("Market Regimes", test_market_regimes),
        ("Configuration", test_configuration),
        ("Streaming (Mock)", test_streaming_mock)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name} test...")
            success = test_func()
            if success:
                passed += 1
                print(f"✅ {test_name} test passed")
            else:
                failed += 1
                print(f"❌ {test_name} test failed")
        except Exception as e:
            failed += 1
            print(f"💥 {test_name} test error: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("🏁 Test Summary")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Technical Indicators system is ready for integration")
        
        # Generate integration report
        report = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': passed,
            'tests_failed': failed,
            'success_rate': passed/(passed+failed)*100,
            'modules_tested': [name for name, _ in tests],
            'status': 'READY' if failed == 0 else 'NEEDS_FIXES'
        }
        
        print(f"\n📋 Integration Report:")
        for key, value in report.items():
            print(f"   {key}: {value}")
        
        return True
    else:
        print(f"\n⚠️ {failed} TEST(S) FAILED")
        print("❌ Please review and fix issues before deployment")
        return False

if __name__ == "__main__":
    """Main test execution"""
    success = run_comprehensive_test()
    exit(0 if success else 1)
