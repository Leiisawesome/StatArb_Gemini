#!/usr/bin/env python3
"""
ML Model Registry
Phase 3: Advanced Analytics & Optimization - Batch 1
"""

import logging
import json
import pickle
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Machine Learning Model Registry for versioning and management"""
    
    def __init__(self, registry_path: str = "models"):
        self.registry_path = registry_path
        self.models = {}
        self.active_models = {}
        
        # Ensure registry directory exists
        os.makedirs(registry_path, exist_ok=True)
        os.makedirs(f"{registry_path}/models", exist_ok=True)
        os.makedirs(f"{registry_path}/metadata", exist_ok=True)
        
        self._load_registry()
        logger.info(f"Initialized ModelRegistry at {registry_path}")
    
    def register_model(self, model_id: str, model_type: str, model_object: Any,
                      performance_metrics: Dict, version: str = None) -> str:
        """Register a new model version"""
        
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create model metadata
        model_metadata = {
            'model_id': model_id,
            'version': version,
            'model_type': model_type,
            'performance_metrics': performance_metrics,
            'created_at': datetime.now().isoformat(),
            'is_active': False
        }
        
        # Initialize model list if not exists
        if model_id not in self.models:
            self.models[model_id] = []
        
        # Add version to model
        self.models[model_id].append(model_metadata)
        
        # Save model file
        model_filename = f"{self.registry_path}/models/{model_id}_{version}.pkl"
        with open(model_filename, 'wb') as f:
            pickle.dump(model_object, f)
        
        # Save metadata
        metadata_filename = f"{self.registry_path}/metadata/{model_id}_{version}.json"
        with open(metadata_filename, 'w') as f:
            json.dump(model_metadata, f, indent=2)
        
        logger.info(f"Registered model: {model_id} v{version}")
        return version
    
    def activate_model(self, model_id: str, version: str) -> bool:
        """Activate a specific model version"""
        
        if model_id not in self.models:
            logger.error(f"Model {model_id} not found in registry")
            return False
        
        # Find the version
        target_version = None
        for model_metadata in self.models[model_id]:
            if model_metadata['version'] == version:
                target_version = model_metadata
                break
        
        if target_version is None:
            logger.error(f"Version {version} not found for model {model_id}")
            return False
        
        # Deactivate current active model
        if model_id in self.active_models:
            self.active_models[model_id]['is_active'] = False
        
        # Activate new version
        target_version['is_active'] = True
        self.active_models[model_id] = target_version
        
        logger.info(f"Activated model: {model_id} v{version}")
        return True
    
    def get_active_model(self, model_id: str) -> Optional[Dict]:
        """Get the currently active model version"""
        return self.active_models.get(model_id)
    
    def load_model(self, model_id: str, version: str = None) -> Optional[Any]:
        """Load a model from registry"""
        
        if version is None:
            # Load active model
            active_model = self.get_active_model(model_id)
            if active_model is None:
                logger.error(f"No active model found for {model_id}")
                return None
            version = active_model['version']
        
        # Find model file
        model_filename = f"{self.registry_path}/models/{model_id}_{version}.pkl"
        
        if not os.path.exists(model_filename):
            logger.error(f"Model file not found: {model_filename}")
            return None
        
        try:
            with open(model_filename, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Loaded model: {model_id} v{version}")
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_id} v{version}: {e}")
            return None
    
    def list_models(self) -> List[str]:
        """List all registered model IDs"""
        return list(self.models.keys())
    
    def list_versions(self, model_id: str) -> List[Dict]:
        """List all versions of a specific model"""
        return self.models.get(model_id, [])
    
    def get_model_summary(self) -> Dict:
        """Get registry summary"""
        total_models = len(self.models)
        total_versions = sum(len(versions) for versions in self.models.values())
        active_models = len(self.active_models)
        
        return {
            'total_models': total_models,
            'total_versions': total_versions,
            'active_models': active_models,
            'registry_path': self.registry_path
        }
    
    def _load_registry(self):
        """Load existing registry from disk"""
        metadata_path = f"{self.registry_path}/metadata"
        
        if not os.path.exists(metadata_path):
            return
        
        for filename in os.listdir(metadata_path):
            if filename.endswith('.json'):
                try:
                    with open(f"{metadata_path}/{filename}", 'r') as f:
                        metadata = json.load(f)
                    
                    # Add to registry
                    model_id = metadata['model_id']
                    if model_id not in self.models:
                        self.models[model_id] = []
                    
                    self.models[model_id].append(metadata)
                    
                    if metadata.get('is_active', False):
                        self.active_models[model_id] = metadata
                        
                except Exception as e:
                    logger.error(f"Error loading metadata {filename}: {e}")
        
        logger.info(f"Loaded {len(self.models)} models from registry")
