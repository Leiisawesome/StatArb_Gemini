#!/usr/bin/env python3
"""
Training Pipeline
Phase 3: Advanced Analytics & Optimization - Batch 1
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)

class TrainingPipeline:
    """ML model training pipeline"""
    
    def __init__(self):
        self.models = {}
        self.training_history = []
        self.best_models = {}
        
        logger.info("Initialized TrainingPipeline")
    
    def prepare_data(self, features: pd.DataFrame, target_column: str = 'target',
                    test_size: float = 0.2, random_state: int = 42) -> Tuple:
        """Prepare data for training"""
        
        if target_column not in features.columns:
            logger.error(f"Target column '{target_column}' not found in features")
            return None, None, None, None
        
        # Remove rows with NaN values
        features_clean = features.dropna()
        
        if features_clean.empty:
            logger.error("No valid data after cleaning")
            return None, None, None, None
        
        # Separate features and target
        X = features_clean.drop(columns=[target_column])
        y = features_clean[target_column]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, shuffle=False
        )
        
        logger.info(f"Prepared data: {len(X_train)} train, {len(X_test)} test samples")
        return X_train, X_test, y_train, y_test
    
    def train_model(self, model_id: str, model_object: Any, X_train: pd.DataFrame,
                   y_train: pd.Series, model_type: str = "unknown") -> Dict:
        """Train a model and return performance metrics"""
        
        try:
            # Train model
            model_object.fit(X_train, y_train)
            
            # Make predictions
            y_pred = model_object.predict(X_train)
            
            # Calculate metrics
            metrics = self._calculate_metrics(y_train, y_pred)
            
            # Store model
            self.models[model_id] = {
                'model': model_object,
                'model_type': model_type,
                'features': list(X_train.columns),
                'training_metrics': metrics,
                'trained_at': datetime.now()
            }
            
            # Store training history
            training_record = {
                'model_id': model_id,
                'model_type': model_type,
                'training_metrics': metrics,
                'trained_at': datetime.now(),
                'features_count': len(X_train.columns),
                'samples_count': len(X_train)
            }
            self.training_history.append(training_record)
            
            logger.info(f"Trained model {model_id}: {metrics['accuracy']:.3f} accuracy")
            return metrics
            
        except Exception as e:
            logger.error(f"Error training model {model_id}: {e}")
            return {}
    
    def evaluate_model(self, model_id: str, X_test: pd.DataFrame, y_test: pd.Series) -> Dict:
        """Evaluate a trained model"""
        
        if model_id not in self.models:
            logger.error(f"Model {model_id} not found")
            return {}
        
        try:
            model = self.models[model_id]['model']
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            metrics = self._calculate_metrics(y_test, y_pred)
            
            # Store evaluation results
            self.models[model_id]['evaluation_metrics'] = metrics
            
            logger.info(f"Evaluated model {model_id}: {metrics['accuracy']:.3f} accuracy")
            return metrics
            
        except Exception as e:
            logger.error(f"Error evaluating model {model_id}: {e}")
            return {}
    
    def _calculate_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict:
        """Calculate performance metrics"""
        
        try:
            metrics = {
                'accuracy': accuracy_score(y_true, y_pred),
                'precision': precision_score(y_true, y_pred, average='weighted'),
                'recall': recall_score(y_true, y_pred, average='weighted'),
                'f1_score': f1_score(y_true, y_pred, average='weighted')
            }
        except Exception as e:
            logger.warning(f"Error calculating metrics: {e}")
            metrics = {
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0
            }
        
        return metrics
    
    def get_best_model(self, metric: str = 'accuracy') -> Optional[str]:
        """Get the best performing model based on metric"""
        
        if not self.models:
            return None
        
        best_model_id = None
        best_score = -1
        
        for model_id, model_info in self.models.items():
            if 'evaluation_metrics' in model_info:
                score = model_info['evaluation_metrics'].get(metric, 0)
                if score > best_score:
                    best_score = score
                    best_model_id = model_id
        
        return best_model_id
    
    def get_training_summary(self) -> Dict:
        """Get training pipeline summary"""
        return {
            'total_models': len(self.models),
            'training_history_count': len(self.training_history),
            'best_model': self.get_best_model(),
            'model_types': list(set(info['model_type'] for info in self.models.values()))
        }
