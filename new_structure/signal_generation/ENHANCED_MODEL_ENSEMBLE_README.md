# Enhanced Model Ensemble Documentation

## Overview

The Enhanced Model Ensemble is a professional-grade ensemble framework that combines multiple AI/ML models for signal generation in trading systems. It now supports 7 different model types with advanced features like dynamic weighting, performance tracking, and real-time prediction capabilities.

## Supported Model Types

### 1. Kalman Filter Model (`KALMAN_FILTER`)
- **Purpose**: Time-series prediction with state estimation and noise filtering
- **Use Cases**: Price trend tracking, momentum estimation, noise reduction
- **Key Features**:
  - Process and observation noise modeling
  - Adaptive state estimation
  - Confidence based on state variance
  - Real-time state updates

**Configuration Example**:
```python
ModelConfig(
    model_type=ModelType.KALMAN_FILTER,
    name="kalman_price_tracker",
    weight=0.2,
    hyperparameters={
        'process_noise': 0.1,
        'observation_noise': 0.05,
        'initial_state_variance': 1.0
    }
)
```

### 2. HMM Regime Model (`HMM_REGIME`)
- **Purpose**: Market regime detection (bull/bear/sideways markets)
- **Use Cases**: Adaptive strategy selection, regime-based position sizing
- **Key Features**:
  - Multi-state regime modeling
  - Configurable regime thresholds
  - Regime transition tracking
  - Confidence based on regime stability

**Configuration Example**:
```python
ModelConfig(
    model_type=ModelType.HMM_REGIME,
    name="regime_detector",
    weight=0.2,
    hyperparameters={
        'n_states': 3,
        'bull_threshold': 0.01,
        'bear_threshold': -0.01
    }
)
```

### 3. Custom Model (`CUSTOM`)
- **Purpose**: Extensible framework for user-defined prediction algorithms
- **Use Cases**: Proprietary algorithms, specialized indicators, custom logic
- **Key Features**:
  - Flexible predictor interface
  - Support for any callable function
  - Custom fit/predict methods
  - Plugin architecture

**Configuration Example**:
```python
def custom_predictor(X):
    # Your custom logic here
    return predictions

ModelConfig(
    model_type=ModelType.CUSTOM,
    name="momentum_custom",
    weight=0.2,
    hyperparameters={
        'custom_predictor': custom_predictor
    }
)
```

### 4. Ensemble Voting Model (`ENSEMBLE_VOTING`)
- **Purpose**: Meta-ensemble that combines other models using voting strategies
- **Use Cases**: Hierarchical ensembling, consensus building, uncertainty quantification
- **Key Features**:
  - Multiple voting strategies (majority, weighted, unanimous)
  - Dynamic model weights
  - Sub-model management
  - Consensus scoring

**Configuration Example**:
```python
ModelConfig(
    model_type=ModelType.ENSEMBLE_VOTING,
    name="voting_ensemble",
    weight=0.2,
    hyperparameters={
        'voting_strategy': 'majority'  # or 'weighted', 'unanimous'
    }
)
```

### 5. Scikit-Learn Models
- **Random Forest** (`RANDOM_FOREST`)
- **Gradient Boosting** (`GRADIENT_BOOST`)  
- **Logistic Regression** (`LOGISTIC_REGRESSION`)

These models use standard scikit-learn implementations with configurable hyperparameters.

## Key Features

### Dynamic Model Weighting
- Performance-based weight adjustment
- Exponential decay for recent performance emphasis
- Automatic weight normalization
- Configurable weight constraints

### Real-time Performance Tracking
- Exponentially weighted metrics
- Accuracy, precision, recall calculation
- Confidence and uncertainty quantification
- Model drift detection

### Advanced Prediction Pipeline
- Parallel model execution (sub-100ms latency)
- Prediction caching with TTL
- Graceful error handling
- Comprehensive result metadata

### Model Management
- Individual model training
- Batch training capabilities
- Model status monitoring
- Health check reporting

## Usage Examples

### Basic Ensemble Setup
```python
from model_ensemble import ModelEnsemble, ModelConfig, ModelType

# Define model configurations
models = [
    ModelConfig(
        model_type=ModelType.KALMAN_FILTER,
        name="kalman_tracker",
        weight=0.3,
        hyperparameters={'process_noise': 0.1}
    ),
    ModelConfig(
        model_type=ModelType.HMM_REGIME,
        name="regime_detector",
        weight=0.3,
        hyperparameters={'n_states': 3}
    ),
    ModelConfig(
        model_type=ModelType.RANDOM_FOREST,
        name="rf_classifier",
        weight=0.4,
        hyperparameters={'n_estimators': 100}
    )
]

# Initialize ensemble
ensemble = ModelEnsemble(models)
```

### Training Models
```python
# Train all models
training_results = ensemble.train_all_models(X_train, y_train)

# Train individual model
success = ensemble.train_model("kalman_tracker", X_train, y_train)
```

### Making Predictions
```python
# Prepare features
features = {
    'returns_1d': 0.015,
    'returns_5d': 0.08,
    'volatility_5d': 0.018,
    'rsi_14': 65.0,
    'macd': 1.2,
    'volume_ratio': 1.3
}

# Get ensemble prediction
result = await ensemble.predict(features)

print(f"Prediction: {result.prediction}")
print(f"Confidence: {result.confidence:.3f}")
print(f"Uncertainty: {result.uncertainty:.3f}")
print(f"Consensus: {result.consensus_score:.3f}")
```

### Performance Tracking
```python
# Record actual outcome
ensemble.record_outcome(features, actual_outcome, prediction_result)

# Get ensemble health
health = ensemble.get_ensemble_health()
print(f"Active models: {health['active_models']}")
print(f"Average accuracy: {health['average_accuracy']:.3f}")
```

### Model Information
```python
# Get detailed model info
info = ensemble.get_model_info("kalman_tracker")
print(f"Model type: {info['type']}")
print(f"Status: {info['status']}")
print(f"Is fitted: {info['is_fitted']}")
print(f"Current weight: {info['weight']:.3f}")
```

## EnsembleResult Structure

The prediction result contains comprehensive metadata:

```python
@dataclass
class EnsembleResult:
    prediction: Union[int, float]           # Final ensemble prediction
    confidence: float                       # Ensemble confidence score
    uncertainty: float                      # Prediction uncertainty
    model_contributions: Dict[str, float]   # Each model's contribution
    individual_predictions: Dict[str, Union[int, float]]  # Individual model predictions
    model_weights: Dict[str, float]         # Current model weights
    consensus_score: float                  # Agreement among models
    prediction_time_ms: float               # Prediction latency
    model_versions: Dict[str, str]          # Model version tracking
    timestamp: datetime                     # Prediction timestamp
```

## Integration with Technical Indicators

The ensemble integrates seamlessly with the `TechnicalIndicatorEngine`:

```python
# From technical indicators to ensemble prediction
indicators = technical_engine.calculate_indicators(market_data)
features = feature_pipeline.transform(indicators)
prediction = await model_ensemble.predict(features)
```

## Production Considerations

### Performance Optimization
- Parallel model execution
- Prediction caching
- Efficient feature preprocessing
- Memory-efficient data structures

### Monitoring and Alerting
- Model performance degradation detection
- Automatic model disabling for poor performers
- Comprehensive logging and metrics
- Health check endpoints

### Scalability
- Thread-safe operations
- Configurable thread pool
- Memory management
- Graceful shutdown procedures

## Testing

Run the comprehensive test suite:

```bash
python test_model_ensemble.py
```

This will test:
- Model initialization and training
- Prediction accuracy
- Performance tracking
- Error handling
- Integration scenarios

## Advanced Features

### Custom Model Development
Extend the `BaseModel` class for custom implementations:

```python
class MyCustomModel(BaseModel):
    def fit(self, X, y):
        # Custom training logic
        self.is_fitted = True
    
    def predict(self, X):
        # Custom prediction logic
        return predictions
```

### Voting Ensemble Configuration
Create hierarchical ensembles:

```python
# Add models to voting ensemble
ensemble.add_model_to_voting_ensemble(
    voting_model_name="meta_ensemble",
    model_to_add="kalman_tracker",
    weight=0.4
)
```

### Performance Tuning
Optimize for your specific use case:

```python
# Adjust cache settings
ensemble.cache_ttl_seconds = 30

# Configure weight update frequency
ensemble.model_weights.decay_rate = 0.98

# Set performance thresholds
config.min_accuracy_threshold = 0.6
```

## Architecture Integration

The Enhanced Model Ensemble fits into the broader architecture as follows:

```
Market Data → Technical Indicators → Feature Engineering → Model Ensemble → Trading Signals
```

Each component in this pipeline is modular and can be independently optimized while maintaining the overall system performance and reliability.
