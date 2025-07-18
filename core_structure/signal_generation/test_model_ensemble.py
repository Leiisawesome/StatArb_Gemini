"""
Test script for the enhanced ModelEnsemble with new model types
================================================================

This script demonstrates the functionality of the new model implementations:
- KalmanFilterModel
- HMMRegimeModel  
- CustomModel
- EnsembleVotingModel

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
import asyncio
from datetime import datetime
import logging
from typing import Dict, List

# Import the enhanced model ensemble
from model_ensemble import (
    ModelEnsemble, ModelConfig, ModelType, ModelStatus,
    KalmanFilterModel, HMMRegimeModel, CustomModel, EnsembleVotingModel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_data(n_samples: int = 1000) -> tuple:
    """Generate sample financial data for testing"""
    np.random.seed(42)
    
    # Generate price returns
    returns_1d = np.random.normal(0.001, 0.02, n_samples)
    returns_5d = np.cumsum(returns_1d.reshape(-1, 5), axis=1)[:, -1][:n_samples//5]
    returns_20d = np.cumsum(returns_1d.reshape(-1, 20), axis=1)[:, -1][:n_samples//20]
    
    # Pad to same length
    n_min = min(len(returns_1d), len(returns_5d), len(returns_20d))
    returns_1d = returns_1d[:n_min]
    returns_5d = returns_5d[:n_min] 
    returns_20d = returns_20d[:n_min]
    
    # Generate other features
    volatility_5d = np.abs(np.random.normal(0.015, 0.005, n_min))
    volatility_20d = np.abs(np.random.normal(0.025, 0.008, n_min))
    rsi_14 = np.random.uniform(20, 80, n_min)
    macd = np.random.normal(0, 1.5, n_min)
    volume_ratio = np.random.lognormal(0, 0.3, n_min)
    
    # Create feature matrix
    X = np.column_stack([
        returns_1d, returns_5d, returns_20d,
        volatility_5d, volatility_20d,
        rsi_14, macd, volume_ratio
    ])
    
    # Generate binary targets (1 for positive returns, 0 for negative)
    y = (returns_1d > 0).astype(int)
    
    return X, y

def create_sample_custom_predictor():
    """Create a simple custom predictor function"""
    def simple_momentum_predictor(X: np.ndarray) -> np.ndarray:
        """Simple momentum-based predictor"""
        predictions = []
        for i in range(X.shape[0]):
            # Use returns and RSI for prediction
            returns_1d = X[i, 0] if X.shape[1] > 0 else 0
            rsi_14 = X[i, 5] if X.shape[1] > 5 else 50
            
            # Simple logic: buy if recent returns positive and RSI not overbought
            prediction = 1 if returns_1d > 0 and rsi_14 < 70 else 0
            predictions.append(prediction)
            
        return np.array(predictions)
    
    return simple_momentum_predictor

async def test_model_ensemble():
    """Test the enhanced model ensemble"""
    logger.info("Starting ModelEnsemble test...")
    
    # Generate sample data
    X, y = generate_sample_data(500)
    logger.info(f"Generated sample data: X shape {X.shape}, y shape {y.shape}")
    
    # Create model configurations
    models = [
        ModelConfig(
            model_type=ModelType.KALMAN_FILTER,
            name="kalman_price_tracker",
            weight=0.2,
            hyperparameters={
                'process_noise': 0.1,
                'observation_noise': 0.05,
                'initial_state_variance': 1.0
            }
        ),
        ModelConfig(
            model_type=ModelType.HMM_REGIME,
            name="regime_detector",
            weight=0.2,
            hyperparameters={
                'n_states': 3,
                'bull_threshold': 0.01,
                'bear_threshold': -0.01
            }
        ),
        ModelConfig(
            model_type=ModelType.CUSTOM,
            name="momentum_custom",
            weight=0.2,
            hyperparameters={
                'custom_predictor': create_sample_custom_predictor()
            }
        ),
        ModelConfig(
            model_type=ModelType.ENSEMBLE_VOTING,
            name="voting_ensemble",
            weight=0.2,
            hyperparameters={
                'voting_strategy': 'majority'
            }
        )
    ]
    
    # Add sklearn models if available
    try:
        from sklearn.ensemble import RandomForestClassifier
        models.append(
            ModelConfig(
                model_type=ModelType.RANDOM_FOREST,
                name="random_forest",
                weight=0.2,
                hyperparameters={
                    'n_estimators': 50,
                    'max_depth': 5,
                    'random_state': 42
                }
            )
        )
    except ImportError:
        logger.warning("Sklearn not available, skipping RandomForest")
    
    # Initialize ensemble
    ensemble = ModelEnsemble(models)
    logger.info(f"Initialized ensemble with {len(ensemble.models)} models")
    
    # Train all models
    logger.info("Training models...")
    training_results = ensemble.train_all_models(X[:400], y[:400])  # Use first 400 samples for training
    
    for model_name, success in training_results.items():
        status = "✓" if success else "✗"
        logger.info(f"  {status} {model_name}: {'Success' if success else 'Failed'}")
    
    # Test predictions
    logger.info("Testing predictions...")
    test_features = {
        'returns_1d': 0.015,
        'returns_5d': 0.08,
        'returns_20d': 0.12,
        'volatility_5d': 0.018,
        'volatility_20d': 0.025,
        'rsi_14': 65.0,
        'macd': 1.2,
        'volume_ratio': 1.3
    }
    
    # Make prediction
    result = await ensemble.predict(test_features)
    
    if result:
        logger.info(f"Ensemble prediction: {result.prediction}")
        logger.info(f"Confidence: {result.confidence:.3f}")
        logger.info(f"Uncertainty: {result.uncertainty:.3f}")
        logger.info(f"Consensus score: {result.consensus_score:.3f}")
        logger.info(f"Prediction time: {result.prediction_time_ms:.2f}ms")
        
        logger.info("Individual model predictions:")
        for model_name, prediction in result.individual_predictions.items():
            weight = result.model_weights.get(model_name, 0.0)
            contribution = result.model_contributions.get(model_name, 0.0)
            logger.info(f"  {model_name}: {prediction} (weight: {weight:.3f}, contribution: {contribution:.3f})")
    else:
        logger.error("Prediction failed!")
    
    # Test model info
    logger.info("\nModel information:")
    for model_name in ensemble.models.keys():
        info = ensemble.get_model_info(model_name)
        if info:
            logger.info(f"  {model_name}:")
            logger.info(f"    Type: {info['type']}")
            logger.info(f"    Status: {info['status']}")
            logger.info(f"    Fitted: {info['is_fitted']}")
            logger.info(f"    Weight: {info['weight']:.3f}")
            logger.info(f"    Performance: {info['performance_score']:.3f}")
            
            # Model-specific info
            if 'current_regime' in info:
                logger.info(f"    Current regime: {info['current_regime']}")
            if 'state_mean' in info:
                logger.info(f"    State mean: {info['state_mean']:.3f}")
    
    # Test ensemble health
    health = ensemble.get_ensemble_health()
    logger.info(f"\nEnsemble health:")
    logger.info(f"  Total models: {health.get('model_count', 0)}")
    logger.info(f"  Active models: {health.get('active_models', 0)}")
    logger.info(f"  Average accuracy: {health.get('average_accuracy', 0.0):.3f}")
    logger.info(f"  Cache size: {health.get('cache_size', 0)}")
    
    # Test batch predictions
    logger.info("\nTesting batch predictions...")
    test_X = X[400:410]  # Use next 10 samples
    test_y = y[400:410]
    
    for i in range(len(test_X)):
        features = {
            'returns_1d': test_X[i, 0],
            'returns_5d': test_X[i, 1] if test_X.shape[1] > 1 else 0,
            'returns_20d': test_X[i, 2] if test_X.shape[1] > 2 else 0,
            'volatility_5d': test_X[i, 3] if test_X.shape[1] > 3 else 0,
            'volatility_20d': test_X[i, 4] if test_X.shape[1] > 4 else 0,
            'rsi_14': test_X[i, 5] if test_X.shape[1] > 5 else 50,
            'macd': test_X[i, 6] if test_X.shape[1] > 6 else 0,
            'volume_ratio': test_X[i, 7] if test_X.shape[1] > 7 else 1
        }
        
        prediction_result = await ensemble.predict(features)
        if prediction_result:
            # Record outcome for performance tracking
            ensemble.record_outcome(features, test_y[i], prediction_result)
            
            actual = test_y[i]
            predicted = prediction_result.prediction
            correct = "✓" if int(predicted) == actual else "✗"
            logger.info(f"  Sample {i}: Predicted {predicted}, Actual {actual} {correct}")
    
    # Shutdown ensemble
    ensemble.shutdown()
    logger.info("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_model_ensemble())
