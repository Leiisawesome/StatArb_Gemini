# Migration Guide: Legacy Test Cases to Trade Engine

## 🎯 Overview

This guide shows how to migrate legacy test cases (like `momentum_strategy_backtest.py`) to leverage the advanced **trade_engine** analytics while maintaining compatibility with the **core_structure** foundation.

## 🏗️ Migration Architecture

### **Before: Legacy Structure**
```
Testing relies only on core_structure:
├── core_structure/ (foundation only)
├── Basic backtest logic
├── Simple performance metrics
└── Manual analysis
```

### **After: Trade Engine Integration**
```
Enhanced testing with trade_engine:
├── core_structure/ (foundation)
├── trade_engine/analytics/ (7 ML components)
├── Enhanced backtest logic
├── ML-powered performance metrics
└── Automated insights & predictions
```

## 📋 Step-by-Step Migration Process

### Step 1: Add Trade Engine Imports

**Before (Legacy):**
```python
# Only core_structure imports
from core_structure.unified_core_engine import (
    UnifiedCoreEngine, CoreEngineConfig, TradingMode, StrategyConfig
)
```

**After (Enhanced):**
```python
# Core structure imports (foundation)
from core_structure.unified_core_engine import (
    UnifiedCoreEngine, CoreEngineConfig, TradingMode, StrategyConfig
)

# 🆕 Trade engine imports (advanced analytics)
from trade_engine.analytics.performance_analyzer import PerformanceAnalyzer
from trade_engine.analytics.predictive_monitor import PredictiveMonitor
from trade_engine.analytics.anomaly_detector import AnomalyDetector
from trade_engine.analytics.risk_analyzer import RiskAnalyzer
from trade_engine.analytics.attribution_analyzer import AttributionAnalyzer
from trade_engine.analytics.regime_detector import RegimeDetector
from trade_engine.analytics.optimization_engine import OptimizationEngine
```

### Step 2: Enhance Configuration

**Before (Legacy):**
```python
@dataclass
class MomentumBacktestConfig:
    start_date: datetime = datetime(2025, 1, 3)
    universe: List[str] = field(default_factory=lambda: ['TSLA'])
    initial_capital: float = 100_000.0
    strategy_params: Dict[str, Any] = field(default_factory=lambda: {...})
```

**After (Enhanced):**
```python
@dataclass
class EnhancedMomentumBacktestConfig:
    # Original configuration
    start_date: datetime = datetime(2025, 1, 3)
    universe: List[str] = field(default_factory=lambda: ['TSLA'])
    initial_capital: float = 100_000.0
    strategy_params: Dict[str, Any] = field(default_factory=lambda: {...})
    
    # 🆕 Trade Engine Analytics Configuration
    enable_ml_analytics: bool = True
    enable_performance_prediction: bool = True
    enable_anomaly_detection: bool = True
    enable_risk_analytics: bool = True
    enable_attribution_analysis: bool = True
    enable_regime_detection: bool = True
    enable_optimization: bool = False  # Resource-intensive, optional
```

### Step 3: Initialize Trade Engine Components

**Before (Legacy):**
```python
async def initialize_system(self) -> bool:
    # Only core engine initialization
    self.core_engine = UnifiedCoreEngine(config=core_config)
    self.core_engine.reset_for_backtesting()
    return True
```

**After (Enhanced):**
```python
async def initialize_system(self) -> bool:
    # 1. Initialize core structure (foundation)
    success = await self._initialize_core_structure()
    if not success:
        return False
    
    # 2. 🆕 Initialize trade_engine analytics
    success = await self._initialize_trade_engine_analytics()
    if not success:
        return False
    
    return True

async def _initialize_trade_engine_analytics(self) -> bool:
    """Initialize trade_engine analytics components"""
    if self.config.enable_ml_analytics:
        self.performance_analyzer = PerformanceAnalyzer()
    
    if self.config.enable_performance_prediction:
        self.predictive_monitor = PredictiveMonitor()
    
    if self.config.enable_anomaly_detection:
        self.anomaly_detector = AnomalyDetector()
    
    # ... initialize other components based on configuration
    return True
```

### Step 4: Enhance Strategy Configuration

**Before (Legacy):**
```python
strategy_config = StrategyConfig(
    strategy_id=f"momentum_{self.results.test_id}",
    strategy_name="Momentum Strategy",
    signal_params={
        'symbols': self.config.universe,
        **self.config.strategy_params
    }
)
```

**After (Enhanced):**
```python
strategy_config = StrategyConfig(
    strategy_id=f"enhanced_momentum_{self.results.test_id}",
    strategy_name="Enhanced Momentum Strategy with ML Analytics",
    signal_params={
        'symbols': self.config.universe,
        # 🆕 Enable trade_engine analytics
        'enable_ml_analytics': self.config.enable_ml_analytics,
        'enable_performance_prediction': self.config.enable_performance_prediction,
        'enable_anomaly_detection': self.config.enable_anomaly_detection,
        **self.config.strategy_params
    },
    risk_params={
        # 🆕 Enhanced risk management with ML
        'enable_ml_risk_assessment': self.config.enable_risk_analytics,
        **original_risk_params
    }
)
```

### Step 5: Enhance Trade Processing

**Before (Legacy):**
```python
# Run core engine only
result = await self.core_engine.process_trading_cycle(slice_data, strategy_config)

# Process results
if result.success and result.execution_results:
    for exec_result in result.execution_results:
        self._capture_trade_details(exec_result, timestamp, slice_index)
```

**After (Enhanced):**
```python
# 1. Run core engine trading cycle (foundation)
result = await self.core_engine.process_trading_cycle(slice_data, strategy_config)

# 2. 🆕 Enhance with trade_engine analytics
await self._apply_trade_engine_analytics(result, slice_data, slice_index)

# 3. Process results (enhanced)
if result.success and result.execution_results:
    for exec_result in result.execution_results:
        # Enhanced trade capture with ML analytics
        await self._capture_enhanced_trade_details(exec_result, timestamp, slice_index)

async def _apply_trade_engine_analytics(self, result, slice_data: Dict, slice_index: int):
    """Apply trade_engine analytics to trading result"""
    # 🆕 Performance prediction
    if self.predictive_monitor and result.performance_metrics:
        prediction = await self.predictive_monitor.predict_performance(result.performance_metrics)
        # Store prediction results
    
    # 🆕 Anomaly detection
    if self.anomaly_detector and result.performance_metrics:
        anomaly_score = await self.anomaly_detector.detect_anomaly(result.performance_metrics)
        # Store anomaly results
    
    # 🆕 Risk analysis, attribution, regime detection...
```

### Step 6: Enhance Data Structures

**Before (Legacy):**
```python
@dataclass
class TradeDetail:
    trade_id: int
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    price: float
    momentum: float
    pnl: float = 0.0
```

**After (Enhanced):**
```python
@dataclass
class EnhancedTradeDetail:
    # Original trade data
    trade_id: int
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    price: float
    momentum: float
    pnl: float = 0.0
    
    # 🆕 ML Analytics Data
    predicted_performance: Optional[float] = None
    anomaly_score: Optional[float] = None
    risk_score: Optional[float] = None
    attribution_factors: Optional[Dict[str, float]] = None
    market_regime: Optional[str] = None
    confidence_score: Optional[float] = None
```

### Step 7: Enhance Results and Reporting

**Before (Legacy):**
```python
@dataclass
class BacktestResults:
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    trades: List[TradeDetail] = field(default_factory=list)
```

**After (Enhanced):**
```python
@dataclass
class EnhancedBacktestResults:
    # Original performance metrics
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    trades: List[EnhancedTradeDetail] = field(default_factory=list)
    
    # 🆕 ML Analytics Results
    ml_performance_insights: Dict[str, Any] = field(default_factory=dict)
    predicted_vs_actual: List[Dict[str, float]] = field(default_factory=list)
    anomaly_events: List[Dict[str, Any]] = field(default_factory=list)
    risk_analysis: Dict[str, Any] = field(default_factory=dict)
    attribution_breakdown: Dict[str, Any] = field(default_factory=dict)
    regime_changes: List[Dict[str, Any]] = field(default_factory=list)
```

## 🚀 Migration Benefits

### **Enhanced Capabilities:**
1. **🔮 Predictive Analytics**: Forecast trade outcomes and performance
2. **⚠️ Anomaly Detection**: Identify unusual market conditions and trades
3. **🎯 Risk Assessment**: ML-powered risk scoring and analysis
4. **📈 Attribution Analysis**: Factor-based performance attribution
5. **🔄 Regime Detection**: Market regime identification and adaptation
6. **⚡ Optimization**: Parameter optimization with multiple algorithms

### **Backward Compatibility:**
- ✅ Core functionality unchanged
- ✅ Original metrics still available
- ✅ Gradual enablement of ML features
- ✅ Fallback to legacy mode if trade_engine unavailable

### **Optional Features:**
- Each analytics component can be enabled/disabled independently
- Resource-intensive features (optimization) can be turned off
- Graceful degradation when components fail

## 📊 Migration Examples

### Example 1: Minimal Migration (Just Add Prediction)
```python
# Only enable performance prediction
config = EnhancedMomentumBacktestConfig(
    enable_ml_analytics=False,
    enable_performance_prediction=True,  # Only this feature
    enable_anomaly_detection=False,
    enable_risk_analytics=False,
    enable_attribution_analysis=False,
    enable_regime_detection=False
)
```

### Example 2: Full Analytics Suite
```python
# Enable all features
config = EnhancedMomentumBacktestConfig(
    enable_ml_analytics=True,
    enable_performance_prediction=True,
    enable_anomaly_detection=True,
    enable_risk_analytics=True,
    enable_attribution_analysis=True,
    enable_regime_detection=True,
    enable_optimization=True  # Resource-intensive
)
```

### Example 3: Risk-Focused Migration
```python
# Focus on risk and anomaly detection
config = EnhancedMomentumBacktestConfig(
    enable_risk_analytics=True,
    enable_anomaly_detection=True,
    enable_regime_detection=True,  # For risk context
    # Other features disabled for performance
)
```

## 🔧 Migration Checklist

### ✅ Required Changes:
- [ ] Add trade_engine imports
- [ ] Enhance configuration dataclass
- [ ] Initialize trade_engine components
- [ ] Add analytics to trading cycle
- [ ] Enhance data structures
- [ ] Update reporting

### ✅ Optional Enhancements:
- [ ] Add regime-aware data preparation
- [ ] Implement optimization suggestions
- [ ] Add real-time alerting
- [ ] Create ML model persistence
- [ ] Add cross-validation

### ✅ Testing:
- [ ] Test with analytics disabled (legacy mode)
- [ ] Test with individual components enabled
- [ ] Test with full analytics suite
- [ ] Validate performance impact
- [ ] Verify backward compatibility

## 🎯 Migration Results

After migration, your test cases will provide:

1. **All original functionality** + enhanced ML insights
2. **Predictive capabilities** for trade outcomes
3. **Automated anomaly detection** for risk management
4. **Factor attribution analysis** for strategy understanding
5. **Market regime awareness** for adaptive strategies
6. **Optimization suggestions** for parameter tuning

The migrated test case maintains full backward compatibility while providing access to the advanced trade_engine analytics suite!

## 📝 Usage Example

```python
# Run the enhanced backtest
from testing_framework.enhanced_momentum_strategy_backtest import run_enhanced_momentum_backtest, EnhancedMomentumBacktestConfig

# Create configuration
config = EnhancedMomentumBacktestConfig(
    universe=['TSLA', 'AAPL'],
    enable_ml_analytics=True,
    enable_performance_prediction=True,
    enable_anomaly_detection=True
)

# Run enhanced backtest
results = await run_enhanced_momentum_backtest(config)

# Access ML insights
print(f"Prediction Accuracy: {results.ml_performance_insights.get('prediction_accuracy', 'N/A')}")
print(f"Anomaly Events: {len(results.anomaly_events)}")
print(f"Attribution Factors: {results.attribution_breakdown}")
```

This migration approach ensures you get the best of both worlds: the proven stability of core_structure and the advanced capabilities of trade_engine!
