# Regime Detection & Advanced Indicators Test Suite

This directory contains comprehensive tests for the StatArb_Gemini regime detection and advanced indicators capabilities, including all **Tier 2 enhancements**.

## 🏆 Test Categories

### **Tier 2 Enhancement #1: Advanced Regime States**
- `test_advanced_regime_states.py` - Tests 15+ granular regime classifications

### **Tier 2 Enhancement #2: Multi-Timeframe Regime Detection**
- `test_multi_timeframe_regimes.py` - Tests regime detection across 5min, 1H, 1D, 1W timeframes

### **Tier 2 Enhancement #3: ML-Based Transition Prediction**
- `test_ml_transition_prediction.py` - Tests ML-based regime transition forecasting

### **Tier 2 Enhancement #4: Advanced Multi-Timeframe & Macro Indicators**
- `test_advanced_indicators.py` - Tests 144+ indicators across multiple timeframes and macro analysis

### **Professional Regime Detection**
- `test_professional_regime_detection.py` - Professional-grade regime detection methods
- `test_regime_detection_streamlined.py` - Streamlined regime detection for quick validation
- `test_comprehensive_regime_detection.py` - Comprehensive multi-method regime analysis

### **Symbol & Data Validation**
- `test_professional_symbols_simple.py` - Tests professional symbols (VIX, DXY, TNX, etc.)

## 🚀 Running Tests

### Individual Tests
```bash
# Run specific enhancement test
python tests/regime_test/test_advanced_indicators.py
python tests/regime_test/test_advanced_regime_states.py
python tests/regime_test/test_ml_transition_prediction.py
python tests/regime_test/test_multi_timeframe_regimes.py

# Run professional regime detection
python tests/regime_test/test_regime_detection_streamlined.py
```

### All Regime Tests
```bash
# Run all regime tests (from project root)
python -m pytest tests/regime_test/ -v
```

## 📊 Test Coverage

| Enhancement | Test File | Capabilities Tested |
|-------------|-----------|-------------------|
| **Advanced Regime States** | `test_advanced_regime_states.py` | 15+ granular regime types |
| **Multi-Timeframe Detection** | `test_multi_timeframe_regimes.py` | 4 timeframes, consensus analysis |
| **ML Transition Prediction** | `test_ml_transition_prediction.py` | Multi-horizon ML forecasting |
| **Advanced Indicators** | `test_advanced_indicators.py` | 144+ indicators, macro analysis |
| **Professional Detection** | `test_regime_detection_streamlined.py` | Multi-method validation |

## 🎯 Key Features Tested

### **Regime Detection Methods**
- Markov Switching Models
- Gaussian Mixture Models
- Volatility-Based Classification
- Threshold-Based Detection
- ML-Based Classification

### **Multi-Timeframe Analysis**
- 5-minute (Entry/Exit timing)
- 1-hour (Execution focus)
- 1-day (Tactical positioning)
- 1-week (Strategic outlook)

### **Macro Indicators**
- VIX Regime Analysis (Fear/Greed)
- Yield Curve Analysis (Term structure)
- Dollar Strength Index (Currency regime)
- Commodity Trends (Gold/Oil momentum)
- Credit Spread Analysis (Risk appetite)

### **Advanced Capabilities**
- Cross-timeframe consensus
- Timeframe alignment scoring
- Cross-asset correlation
- ML transition prediction
- Dynamic risk adjustment
- Professional strategy recommendations

## 📈 Expected Results

### **Multi-Timeframe Indicators**
- **144+ indicators** calculated across symbols and timeframes
- **Alignment scores** ranging from 60-80%
- **Consensus signals** for RSI and MACD across timeframes

### **Macro Regime Analysis**
- **5 macro components** analyzed (VIX, Yield, Dollar, Commodities, Credit)
- **Cross-asset correlation** typically 15-25%
- **Macro confidence** scores based on data quality

### **ML Predictions**
- **Multi-horizon forecasts** (1D, 1W, 1M)
- **Transition probabilities** with confidence scores
- **Contributing factors** identification

## 🔧 Requirements

- ClickHouse database with market data
- Core engine components initialized
- Virtual environment activated (`ai_integration_env`)

## 📝 Notes

- Tests use real market data from ClickHouse
- Some macro symbols (VIX, DXY, TNX) may not be available in all datasets
- Tests are designed to be robust and handle missing data gracefully
- All tests demonstrate production-ready capabilities

---

**Status**: ✅ **PRODUCTION-READY** - All Tier 2 enhancements successfully implemented and tested!
