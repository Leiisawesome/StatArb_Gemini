"""
AI Model Registry for StatArb Trading System

This module provides comprehensive model lifecycle management including
registration, versioning, deployment, monitoring, and governance.
"""

import asyncio
import json
import logging
import pickle
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import uuid

from ...infrastructure.config.ai_config import ModelConfig, AIConfig

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model lifecycle status"""
    TRAINING = "training"
    VALIDATION = "validation"
    TESTING = "testing"
    STAGING = "staging"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"
    ARCHIVED = "archived"


class ModelType(Enum):
    """Model type categories"""
    SIGNAL_GENERATION = "signal_generation"
    REGIME_DETECTION = "regime_detection"
    RISK_PREDICTION = "risk_prediction"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    EXECUTION_OPTIMIZATION = "execution_optimization"
    ANOMALY_DETECTION = "anomaly_detection"
    NLP_SENTIMENT = "nlp_sentiment"
    FORECASTING = "forecasting"


@dataclass
class ModelMetadata:
    """Extended model metadata"""
    
    # Performance metrics
    training_metrics: Dict[str, float]
    validation_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    
    # Data information
    training_data_hash: str
    feature_importance: Dict[str, float]
    data_drift_score: Optional[float] = None
    
    # Model artifacts
    artifacts: Dict[str, str]  # artifact_name -> file_path
    dependencies: List[str]
    
    # Governance
    creator: str
    approver: Optional[str] = None
    compliance_status: str = "pending"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class ModelRegistry:
    """
    Comprehensive model registry with lifecycle management,
    versioning, deployment, and monitoring capabilities.
    """
    
    def __init__(self, config: AIConfig, storage_path: Optional[str] = None):
        self.config = config
        self.storage_path = Path(storage_path or config.model_storage_path)
        self.registry_db_path = self.storage_path / "registry.json"
        self.models: Dict[str, Dict[str, ModelConfig]] = {}  # model_name -> {version -> config}
        self.metadata: Dict[str, Dict[str, ModelMetadata]] = {}  # model_name -> {version -> metadata}
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.deployment_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize storage
        self._initialize_storage()
        self._load_registry()
    
    def _initialize_storage(self):
        """Initialize storage directories"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "models").mkdir(exist_ok=True)
        (self.storage_path / "metadata").mkdir(exist_ok=True)
        (self.storage_path / "artifacts").mkdir(exist_ok=True)
        (self.storage_path / "backups").mkdir(exist_ok=True)
    
    def _load_registry(self):
        """Load registry from persistent storage"""
        if self.registry_db_path.exists():
            try:
                with open(self.registry_db_path, 'r') as f:
                    data = json.load(f)
                
                # Load model configs
                for model_name, versions in data.get("models", {}).items():
                    self.models[model_name] = {}
                    for version, config_data in versions.items():
                        self.models[model_name][version] = ModelConfig.from_dict(config_data)
                
                # Load metadata
                for model_name, versions in data.get("metadata", {}).items():
                    self.metadata[model_name] = {}
                    for version, meta_data in versions.items():
                        self.metadata[model_name][version] = ModelMetadata(**meta_data)
                
                # Load performance history
                self.performance_history = data.get("performance_history", {})
                self.deployment_history = data.get("deployment_history", {})
                
                logger.info(f"Loaded registry with {len(self.models)} models")
                
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.models = {}
                self.metadata = {}
    
    def _save_registry(self):
        """Save registry to persistent storage"""
        try:
            data = {
                "models": {
                    model_name: {
                        version: config.to_dict() 
                        for version, config in versions.items()
                    }
                    for model_name, versions in self.models.items()
                },
                "metadata": {
                    model_name: {
                        version: asdict(meta)
                        for version, meta in versions.items()
                    }
                    for model_name, versions in self.metadata.items()
                },
                "performance_history": self.performance_history,
                "deployment_history": self.deployment_history,
                "last_updated": datetime.now().isoformat()
            }
            
            # Create backup first
            if self.registry_db_path.exists():
                backup_path = self.storage_path / "backups" / f"registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.registry_db_path, backup_path)
            
            # Save registry
            with open(self.registry_db_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug("Registry saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_model(self, model_config: ModelConfig, metadata: ModelMetadata,
                      model_artifacts: Dict[str, Any]) -> str:
        """Register a new model or version"""
        try:
            # Generate model ID if not provided
            if not model_config.model_id:
                model_config.model_id = f"{model_config.model_name}_{uuid.uuid4().hex[:8]}"
            
            # Set version if not provided
            if not model_config.model_version:
                latest_version = self.get_latest_version(model_config.model_name)
                if latest_version:
                    version_num = int(latest_version.split('.')[-1]) + 1
                    model_config.model_version = f"1.0.{version_num}"
                else:
                    model_config.model_version = "1.0.0"
            
            # Create model storage directory
            model_dir = self.storage_path / "models" / model_config.model_name / model_config.model_version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model artifacts
            saved_artifacts = {}
            for artifact_name, artifact_data in model_artifacts.items():
                artifact_path = model_dir / f"{artifact_name}"
                
                if isinstance(artifact_data, (str, Path)):
                    # Copy file
                    shutil.copy2(artifact_data, artifact_path)
                else:
                    # Save object
                    with open(artifact_path, 'wb') as f:
                        pickle.dump(artifact_data, f)
                
                saved_artifacts[artifact_name] = str(artifact_path)
            
            # Update metadata with artifact paths
            metadata.artifacts = saved_artifacts
            
            # Update model config paths
            model_config.model_path = str(model_dir)
            model_config.metadata_path = str(model_dir / "metadata.json")
            
            # Save metadata
            with open(model_config.metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            
            # Add to registry
            if model_config.model_name not in self.models:
                self.models[model_config.model_name] = {}
                self.metadata[model_config.model_name] = {}
            
            self.models[model_config.model_name][model_config.model_version] = model_config
            self.metadata[model_config.model_name][model_config.model_version] = metadata
            
            # Save registry
            self._save_registry()
            
            logger.info(f"Registered model {model_config.model_name} v{model_config.model_version}")
            return model_config.model_id
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise
    
    def get_model(self, model_name: str, version: Optional[str] = None) -> Optional[ModelConfig]:
        """Get model configuration"""
        if model_name not in self.models:
            return None
        
        if version is None:
            version = self.get_latest_version(model_name)
        
        return self.models[model_name].get(version)
    
    def get_model_metadata(self, model_name: str, version: Optional[str] = None) -> Optional[ModelMetadata]:
        """Get model metadata"""
        if model_name not in self.metadata:
            return None
        
        if version is None:
            version = self.get_latest_version(model_name)
        
        return self.metadata[model_name].get(version)
    
    def get_latest_version(self, model_name: str) -> Optional[str]:
        """Get latest version of a model"""
        if model_name not in self.models:
            return None
        
        versions = list(self.models[model_name].keys())
        if not versions:
            return None
        
        # Sort versions (assumes semantic versioning)
        sorted_versions = sorted(versions, key=lambda v: [int(x) for x in v.split('.')])
        return sorted_versions[-1]
    
    def list_models(self, model_type: Optional[ModelType] = None,
                   status: Optional[ModelStatus] = None) -> List[ModelConfig]:
        """List models with optional filtering"""
        results = []
        
        for model_name, versions in self.models.items():
            for version, config in versions.items():
                # Apply filters
                if model_type and config.model_type != model_type.value:
                    continue
                
                if status and config.status != status.value:
                    continue
                
                results.append(config)
        
        return results
    
    def update_model_status(self, model_name: str, version: str, 
                          new_status: ModelStatus) -> bool:
        """Update model status"""
        try:
            if (model_name in self.models and 
                version in self.models[model_name]):
                
                old_status = self.models[model_name][version].status
                self.models[model_name][version].status = new_status.value
                self.models[model_name][version].updated_at = datetime.now()
                
                # Log deployment if transitioning to deployed
                if new_status == ModelStatus.DEPLOYED:
                    self._log_deployment(model_name, version, old_status)
                
                self._save_registry()
                logger.info(f"Updated {model_name} v{version} status: {old_status} -> {new_status.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update model status: {e}")
        
        return False
    
    def deploy_model(self, model_name: str, version: Optional[str] = None,
                    deployment_config: Optional[Dict[str, Any]] = None) -> bool:
        """Deploy a model"""
        try:
            if version is None:
                version = self.get_latest_version(model_name)
            
            model_config = self.get_model(model_name, version)
            if not model_config:
                raise ValueError(f"Model {model_name} v{version} not found")
            
            # Validate model is ready for deployment
            if model_config.status not in [ModelStatus.STAGING.value, ModelStatus.TESTING.value]:
                raise ValueError(f"Model status {model_config.status} not ready for deployment")
            
            # Update deployment timestamp
            model_config.deployed_at = datetime.now()
            
            # Update status
            success = self.update_model_status(model_name, version, ModelStatus.DEPLOYED)
            
            if success:
                logger.info(f"Successfully deployed {model_name} v{version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            return False
    
    def retire_model(self, model_name: str, version: str) -> bool:
        """Retire a deployed model"""
        try:
            success = self.update_model_status(model_name, version, ModelStatus.DEPRECATED)
            
            if success:
                # Log retirement
                if model_name not in self.deployment_history:
                    self.deployment_history[model_name] = []
                
                self.deployment_history[model_name].append({
                    "version": version,
                    "action": "retired",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "Manual retirement"
                })
                
                self._save_registry()
                logger.info(f"Retired {model_name} v{version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to retire model: {e}")
            return False
    
    def delete_model(self, model_name: str, version: str, 
                    force: bool = False) -> bool:
        """Delete a model version"""
        try:
            if (model_name not in self.models or 
                version not in self.models[model_name]):
                return False
            
            model_config = self.models[model_name][version]
            
            # Safety check - don't delete deployed models
            if model_config.status == ModelStatus.DEPLOYED.value and not force:
                raise ValueError("Cannot delete deployed model without force=True")
            
            # Remove model files
            model_dir = Path(model_config.model_path)
            if model_dir.exists():
                shutil.rmtree(model_dir)
            
            # Remove from registry
            del self.models[model_name][version]
            del self.metadata[model_name][version]
            
            # Clean up empty model entry
            if not self.models[model_name]:
                del self.models[model_name]
                del self.metadata[model_name]
            
            self._save_registry()
            logger.info(f"Deleted {model_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False
    
    def track_performance(self, model_name: str, version: str,
                         metrics: Dict[str, float]) -> None:
        """Track model performance metrics"""
        try:
            performance_key = f"{model_name}:{version}"
            
            if performance_key not in self.performance_history:
                self.performance_history[performance_key] = []
            
            self.performance_history[performance_key].append({
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics
            })
            
            # Keep only recent performance data (configurable window)
            max_entries = 1000
            if len(self.performance_history[performance_key]) > max_entries:
                self.performance_history[performance_key] = \
                    self.performance_history[performance_key][-max_entries:]
            
            self._save_registry()
            
        except Exception as e:
            logger.error(f"Failed to track performance: {e}")
    
    def get_performance_history(self, model_name: str, version: str,
                              days: int = 30) -> List[Dict[str, Any]]:
        """Get model performance history"""
        performance_key = f"{model_name}:{version}"
        
        if performance_key not in self.performance_history:
            return []
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered_history = []
        for entry in self.performance_history[performance_key]:
            entry_date = datetime.fromisoformat(entry["timestamp"])
            if entry_date >= cutoff_date:
                filtered_history.append(entry)
        
        return filtered_history
    
    def compare_models(self, model_name: str, versions: List[str],
                      metric: str = "accuracy") -> Dict[str, float]:
        """Compare performance across model versions"""
        comparison = {}
        
        for version in versions:
            metadata = self.get_model_metadata(model_name, version)
            if metadata:
                # Try validation metrics first, then test metrics
                if metric in metadata.validation_metrics:
                    comparison[version] = metadata.validation_metrics[metric]
                elif metric in metadata.test_metrics:
                    comparison[version] = metadata.test_metrics[metric]
        
        return comparison
    
    def _log_deployment(self, model_name: str, version: str, old_status: str):
        """Log model deployment"""
        if model_name not in self.deployment_history:
            self.deployment_history[model_name] = []
        
        self.deployment_history[model_name].append({
            "version": version,
            "action": "deployed",
            "timestamp": datetime.now().isoformat(),
            "previous_status": old_status
        })
    
    def get_deployment_history(self, model_name: str) -> List[Dict[str, Any]]:
        """Get deployment history for a model"""
        return self.deployment_history.get(model_name, [])
    
    def health_check(self) -> Dict[str, Any]:
        """Perform registry health check"""
        try:
            total_models = sum(len(versions) for versions in self.models.values())
            deployed_models = len([
                config for versions in self.models.values()
                for config in versions.values()
                if config.status == ModelStatus.DEPLOYED.value
            ])
            
            # Check storage
            storage_size = sum(
                f.stat().st_size for f in self.storage_path.rglob('*') if f.is_file()
            ) / (1024 * 1024)  # MB
            
            return {
                "status": "healthy",
                "total_models": total_models,
                "deployed_models": deployed_models,
                "storage_size_mb": round(storage_size, 2),
                "registry_path": str(self.registry_db_path),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
