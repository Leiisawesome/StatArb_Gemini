# MarketCondition Analytics - Detection Accuracy Improvement Plan
# =============================================================

## Current Issues Analysis

### 1. Regime Detection Limitations
- **Current Logic**: Simple volatility + trend thresholds
- **Problem**: All scenarios defaulting to `high_volatility` 
- **Missing**: Multi-dimensional feature analysis

### 2. Feature Engineering Gaps
- **Limited Features**: Only volatility and trend_strength
- **Missing Macro Integration**: Fed rates, inflation data not properly weighted
- **No Cross-Asset Analysis**: VIX, bonds, commodities relationships ignored

## Improvement Recommendations

### A. Enhanced Feature Engineering (Priority 1)

#### Multi-Asset Correlation Analysis
```python
def calculate_cross_asset_features(self, data: pd.DataFrame) -> Dict:
    """Calculate sophisticated cross-asset relationships"""
    features = {}
    
    # 1. VIX Term Structure Analysis
    if 'VIX' in data['symbol'].values:
        vix_data = data[data['symbol'] == 'VIX']['close']
        features['vix_level'] = vix_data.iloc[-1] if len(vix_data) > 0 else 20
        features['vix_percentile'] = self._calculate_percentile(vix_data, lookback=252)
        features['vix_regime'] = 'crisis' if features['vix_level'] > 40 else 'normal'
    
    # 2. Equity-Bond Correlation Regime
    if 'TLT' in data['symbol'].values and 'SPY' in data['symbol'].values:
        spy_returns = data[data['symbol'] == 'SPY']['close'].pct_change()
        tlt_returns = data[data['symbol'] == 'TLT']['close'].pct_change()
        correlation = spy_returns.corr(tlt_returns)
        features['equity_bond_correlation'] = correlation
        features['flight_to_quality'] = correlation < -0.3  # Negative correlation = flight to quality
    
    # 3. Growth vs Value Dynamics
    if 'QQQ' in data['symbol'].values and 'SPY' in data['symbol'].values:
        qqq_spy_ratio = (data[data['symbol'] == 'QQQ']['close'].iloc[-1] / 
                        data[data['symbol'] == 'SPY']['close'].iloc[-1])
        features['growth_value_ratio'] = qqq_spy_ratio
        features['growth_momentum'] = qqq_spy_ratio > self._get_historical_median(qqq_spy_ratio)
    
    return features
```

#### Volume Pattern Recognition
```python
def analyze_volume_patterns(self, data: pd.DataFrame) -> Dict:
    """Detect volume-based regime indicators"""
    features = {}
    
    # Capitulation volume analysis
    volume_spike = data['volume'].rolling(5).mean() / data['volume'].rolling(20).mean()
    features['volume_spike_intensity'] = volume_spike.iloc[-1]
    features['capitulation_signal'] = volume_spike.iloc[-1] > 2.0  # 2x average volume
    
    # Distribution vs accumulation
    price_volume_correlation = data['close'].pct_change().corr(data['volume'])
    features['price_volume_correlation'] = price_volume_correlation
    features['accumulation_pattern'] = price_volume_correlation > 0.3
    
    return features
```

### B. Macro-Economic Integration (Priority 2)

#### Fed Policy Regime Detection
```python
def integrate_macro_signals(self, macro_data: Dict) -> Dict:
    """Enhanced macro signal processing"""
    features = {}
    
    # Fed Policy Stance Analysis
    fed_rate = macro_data.get('fed_funds_rate', 5.0)
    cpi = macro_data.get('cpi_yoy', 2.5)
    
    # Policy regime classification
    if fed_rate < 1.0:
        features['fed_policy_regime'] = 'emergency_accommodation'
        features['regime_risk_on'] = True
    elif fed_rate > 4.0 and cpi > 3.0:
        features['fed_policy_regime'] = 'restrictive_tightening'
        features['regime_risk_off'] = True
    else:
        features['fed_policy_regime'] = 'neutral'
    
    # Real rates analysis
    real_rate = fed_rate - cpi
    features['real_interest_rate'] = real_rate
    features['real_rate_regime'] = 'negative' if real_rate < 0 else 'positive'
    
    return features
```

### C. Machine Learning Model Enhancement (Priority 3)

#### Ensemble Regime Classification
```python
class MLEnhancedRegimeDetector:
    """ML-powered regime detection with ensemble methods"""
    
    def __init__(self):
        self.models = {
            'volatility_classifier': self._build_volatility_model(),
            'trend_classifier': self._build_trend_model(), 
            'crisis_detector': self._build_crisis_model(),
            'regime_ensemble': self._build_ensemble_model()
        }
    
    def _build_ensemble_model(self):
        """Ensemble model combining multiple signals"""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        
        # Features: [vix_level, volatility, trend_strength, volume_spike, 
        #           fed_rate, real_rate, correlation_regime, sentiment_score]
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_split=5,
            class_weight='balanced'  # Handle regime imbalance
        )
    
    async def detect_regime_ml(self, features: np.array) -> Tuple[MarketCondition, float]:
        """ML-based regime detection with confidence scoring"""
        
        # Get predictions from all models
        predictions = {}
        confidences = {}
        
        for model_name, model in self.models.items():
            pred = model.predict(features.reshape(1, -1))[0]
            conf = model.predict_proba(features.reshape(1, -1)).max()
            predictions[model_name] = pred
            confidences[model_name] = conf
        
        # Weighted ensemble decision
        final_regime = self._ensemble_vote(predictions, confidences)
        final_confidence = np.mean(list(confidences.values()))
        
        return final_regime, final_confidence
```

### D. Dynamic Threshold Adaptation (Priority 4)

#### Adaptive Regime Boundaries
```python
class AdaptiveThresholds:
    """Dynamic threshold adaptation based on market evolution"""
    
    def __init__(self):
        self.lookback_periods = {
            'short': 30,   # 30 days
            'medium': 90,  # 90 days  
            'long': 252    # 1 year
        }
    
    def calculate_adaptive_thresholds(self, historical_data: pd.DataFrame) -> Dict:
        """Calculate dynamic thresholds based on recent market behavior"""
        
        volatility = historical_data['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
        thresholds = {}
        for period_name, days in self.lookback_periods.items():
            recent_vol = volatility.tail(days)
            
            thresholds[f'high_vol_threshold_{period_name}'] = recent_vol.quantile(0.8)
            thresholds[f'crisis_vol_threshold_{period_name}'] = recent_vol.quantile(0.95)
            thresholds[f'low_vol_threshold_{period_name}'] = recent_vol.quantile(0.2)
        
        # Adaptive crisis detection based on VIX behavior
        if 'VIX' in historical_data['symbol'].values:
            vix_data = historical_data[historical_data['symbol'] == 'VIX']['close']
            thresholds['vix_crisis_threshold'] = vix_data.quantile(0.9)  # 90th percentile
            thresholds['vix_calm_threshold'] = vix_data.quantile(0.3)   # 30th percentile
        
        return thresholds
```

## Implementation Priority

### Phase 1 (Immediate - 1 week)
1. **Enhanced Feature Engineering**: Cross-asset correlations, volume patterns
2. **Macro Integration**: Fed policy regime classification
3. **Adaptive Thresholds**: Dynamic boundary calculation

### Phase 2 (Medium-term - 2-4 weeks)  
4. **ML Model Training**: Ensemble regime classifier with historical data
5. **Regime Transition Detection**: Markov chain regime switching models
6. **Alternative Data Integration**: News sentiment, options flow, institutional positioning

### Phase 3 (Advanced - 1-2 months)
7. **Deep Learning Models**: LSTM/Transformer for regime sequence modeling
8. **Real-time Calibration**: Online learning and model updating
9. **Multi-timeframe Analysis**: Regime detection across multiple time horizons

## Expected Accuracy Improvement

With these enhancements, accuracy should improve from **50% to 85%+**:

- **Current**: Simple volatility/trend (50% accuracy)
- **Phase 1**: Multi-feature + macro (70% accuracy) 
- **Phase 2**: ML ensemble (80% accuracy)
- **Phase 3**: Advanced ML + real-time adaptation (85%+ accuracy)

## Key Success Metrics

1. **Regime Detection Accuracy**: >85% on historical test periods
2. **Early Warning Capability**: Detect regime changes within 3-5 days
3. **False Positive Rate**: <15% to avoid excessive trading
4. **Regime Stability**: Minimize oscillation between regimes
5. **Crisis Detection**: 95%+ accuracy on crisis periods (most critical)