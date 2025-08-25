# Testing Framework

This directory contains focused backtesting utilities for core trading strategies in the StatArb_Gemini system.

## 🎯 Core Strategy Tests

### Available Backtests

- **`advanced_momentum_backtest.py`** - ✅ **PRIMARY** - Advanced momentum strategy with comprehensive risk management
  - Multi-period momentum (20/50/100 periods with weighted signals)
  - ATR-based stop-loss (2x ATR) and take-profit (3x ATR)
  - Market regime detection and trend filters
  - Dynamic position sizing with volatility adjustment
  - Trailing stops (1.5%) and comprehensive risk management
  - Real ClickHouse data integration

- **`mean_reversion_strategy_backtest.py`** - Mean reversion strategy backtesting
  - RSI-based signals with Bollinger Bands
  - Volume confirmation and volatility filtering
  - Conservative risk management
  - Real market data processing

## 🚀 Quick Start

### Run Advanced Momentum Backtest
```bash
PYTHONPATH=/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini ./ai_integration_env/bin/python testing_framework/advanced_momentum_backtest.py
```

### Run Mean Reversion Backtest
```bash
PYTHONPATH=/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini ./ai_integration_env/bin/python testing_framework/mean_reversion_strategy_backtest.py
```

## 📊 Test Features

Both backtests include:
- ✅ Real ClickHouse data processing
- ✅ Advanced risk management systems
- ✅ Comprehensive performance metrics
- ✅ Detailed trade analysis and reporting
- ✅ Professional parameter tuning
- ✅ ATR-based stops
- ✅ Portfolio tracking
- ✅ Comprehensive performance metrics

## 📋 Documentation

- **`MIGRATION_SUCCESS_SUMMARY.md`** - Migration completion summary
- **`MISSION_ACCOMPLISHED_SUMMARY.md`** - Project completion summary
- **`LOG_ANALYSIS_CRITICAL_ISSUES.md`** - Critical issues analysis
- **`README_SIMPLIFIED_BACKTESTING.md`** - Simplified backtesting guide

## 🎯 Recommended Usage

1. **Start with Advanced Momentum**: Use `advanced_momentum_backtest.py` for sophisticated trading strategy testing
2. **Compare with Basic**: Use `clean_enhanced_momentum_backtest.py` to see the difference
3. **Analyze Results**: Use `trade_analysis.py` for detailed trade analysis
4. **Run Full Suite**: Use `run_all_tests.py` for comprehensive testing

## ⚠️ Notes

- The advanced momentum backtest is the current recommended implementation
- All backtests include synthetic data generation for testing
- Real ClickHouse data integration is available but requires proper database setup
