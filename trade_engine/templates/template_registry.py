"""
Trade Engine Template System
============================

Modern template management system for the trade_engine, replacing legacy strategy_templates.
This system provides advanced template features including ML-driven optimization, 
real-time adaptation, and professional-grade template management.

Author: Pro Quant Desk Trader
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib
from .base_template import ParameterBounds

logger = logging.getLogger(__name__)

class TradeEngineTemplateCategory(Enum):
    """Template categories for trade engine"""
    SIGNAL = "signal"
    RISK = "risk" 
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    COMPOSITE = "composite"

class TradeEngineTemplateType(Enum):
    """Types of trade engine templates"""
    ML_SIGNAL_GENERATION = "ml_signal_generation"
    ADAPTIVE_RISK_MANAGEMENT = "adaptive_risk_management"
    SMART_EXECUTION = "smart_execution"
    DYNAMIC_PORTFOLIO = "dynamic_portfolio"
    COMPLETE_STRATEGY = "complete_strategy"

class TemplateStatus(Enum):
    """Template lifecycle status"""
    DRAFT = "draft"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"

@dataclass
class TradeEngineTemplateMetadata:
    """Metadata for trade engine templates"""
    template_id: str
    name: str
    version: str
    category: TradeEngineTemplateCategory
    template_type: TradeEngineTemplateType
    status: TemplateStatus
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    ml_features: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    checksum: Optional[str] = None

@dataclass 
class TradeEngineTemplate:
    """Advanced template for trade engine strategies"""
    metadata: TradeEngineTemplateMetadata
    configuration: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    ml_config: Dict[str, Any] = field(default_factory=dict)
    risk_limits: Dict[str, Any] = field(default_factory=dict)
    _parameter_bounds: Dict[str, ParameterBounds] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            'metadata': asdict(self.metadata),
            'configuration': self.configuration,
            'parameters': self.parameters,
            'ml_config': self.ml_config,
            'risk_limits': self.risk_limits
        }
    
    def calculate_checksum(self) -> str:
        """Calculate template content checksum"""
        try:
            content = json.dumps(self.to_dict_serializable(), sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(self.metadata.template_id).encode()).hexdigest()
    
    def update_checksum(self):
        """Update template checksum"""
        self.metadata.checksum = self.calculate_checksum()
        self.metadata.updated_at = datetime.now()
    
    def to_dict_serializable(self) -> Dict[str, Any]:
        """Convert template to serializable dictionary"""
        template_dict = self.to_dict()
        
        # Convert datetime objects to strings
        template_dict['metadata']['created_at'] = self.metadata.created_at.isoformat()
        template_dict['metadata']['updated_at'] = self.metadata.updated_at.isoformat()
        
        # Convert enums to values
        template_dict['metadata']['category'] = self.metadata.category.value
        template_dict['metadata']['template_type'] = self.metadata.template_type.value
        template_dict['metadata']['status'] = self.metadata.status.value
        
        return template_dict

class TradeEngineTemplateRegistry:
    """Advanced template registry for trade engine"""
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set registry path
        if registry_path is None:
            registry_path = Path(__file__).parent / "trade_engine_templates.json"
        self.registry_path = Path(registry_path)
        
        # Template storage
        self.templates: Dict[str, TradeEngineTemplate] = {}
        self.template_index: Dict[str, List[str]] = {
            'by_category': {},
            'by_type': {},
            'by_status': {},
            'by_ml_features': {}
        }
        
        # Load existing registry
        self._load_registry()
        
        # Initialize with default templates if empty
        if not self.templates:
            self._create_default_templates()
            self._save_registry()
        
        self.logger.info(f"TradeEngineTemplateRegistry initialized with {len(self.templates)} templates")
    
    def _create_default_templates(self):
        """Create default trade engine templates"""
        
        # 1. ML Momentum Signal Template
        ml_momentum_template = TradeEngineTemplate(
            metadata=TradeEngineTemplateMetadata(
                template_id="ml_momentum_signal",
                name="ML Momentum Signal Generator",
                version="1.0.0",
                category=TradeEngineTemplateCategory.SIGNAL,
                template_type=TradeEngineTemplateType.ML_SIGNAL_GENERATION,
                status=TemplateStatus.PRODUCTION,
                description="Advanced momentum signal generation using ML models",
                author="Trade Engine Team",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["momentum", "ml", "signal"],
                ml_features=["price_momentum", "volume_analysis", "volatility_prediction"]
            ),
            configuration={
                "signal_type": "momentum",
                "ml_enabled": True,
                "lookback_period": 20,
                "prediction_horizon": 5
            },
            parameters={
                "momentum_threshold": 0.02,
                "confidence_threshold": 0.6,
                "position_size": 0.3
            },
            ml_config={
                "models": ["random_forest", "gradient_boosting"],
                "features": ["returns", "volume", "volatility"],
                "training_window": 252,
                "retraining_frequency": "weekly"
            },
            risk_limits={
                "max_position_size": 0.3,
                "stop_loss": 0.05,
                "take_profit": 0.10
            },
            _parameter_bounds={
                "momentum_threshold": ParameterBounds(min_value=0.001, max_value=0.1, data_type=float, default_value=0.02),
                "confidence_threshold": ParameterBounds(min_value=0.1, max_value=0.95, data_type=float, default_value=0.6),
                "position_size": ParameterBounds(min_value=0.01, max_value=0.5, data_type=float, default_value=0.3)
            }
        )
        
        # 2. Adaptive Risk Management Template
        adaptive_risk_template = TradeEngineTemplate(
            metadata=TradeEngineTemplateMetadata(
                template_id="adaptive_risk_management",
                name="Adaptive Risk Management",
                version="1.0.0",
                category=TradeEngineTemplateCategory.RISK,
                template_type=TradeEngineTemplateType.ADAPTIVE_RISK_MANAGEMENT,
                status=TemplateStatus.PRODUCTION,
                description="Dynamic risk management with real-time adaptation",
                author="Trade Engine Team",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["risk", "adaptive", "ml"],
                ml_features=["volatility_prediction", "correlation_analysis", "stress_testing"]
            ),
            configuration={
                "risk_type": "adaptive",
                "ml_enabled": True,
                "regime_detection": True,
                "stress_testing": True
            },
            parameters={
                "var_confidence": 0.95,
                "max_portfolio_risk": 0.02,
                "correlation_threshold": 0.7
            },
            ml_config={
                "models": ["lstm", "garch"],
                "features": ["volatility", "correlations", "market_regime"],
                "prediction_horizon": 10,
                "update_frequency": "daily"
            },
            risk_limits={
                "max_daily_loss": 0.02,
                "max_portfolio_var": 0.05,
                "max_concentration": 0.20
            },
            _parameter_bounds={
                "var_confidence": ParameterBounds(min_value=0.9, max_value=0.99, data_type=float, default_value=0.95),
                "max_portfolio_risk": ParameterBounds(min_value=0.005, max_value=0.05, data_type=float, default_value=0.02),
                "correlation_threshold": ParameterBounds(min_value=0.3, max_value=0.9, data_type=float, default_value=0.7)
            }
        )
        
        # 3. Smart Execution Template
        smart_execution_template = TradeEngineTemplate(
            metadata=TradeEngineTemplateMetadata(
                template_id="smart_execution",
                name="Smart Execution Engine",
                version="1.0.0",
                category=TradeEngineTemplateCategory.EXECUTION,
                template_type=TradeEngineTemplateType.SMART_EXECUTION,
                status=TemplateStatus.PRODUCTION,
                description="Intelligent order execution with market impact optimization",
                author="Trade Engine Team",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["execution", "optimization", "ml"],
                ml_features=["market_impact_prediction", "liquidity_analysis", "timing_optimization"]
            ),
            configuration={
                "execution_type": "smart",
                "ml_enabled": True,
                "market_impact_optimization": True,
                "liquidity_analysis": True
            },
            parameters={
                "max_market_impact": 0.001,
                "execution_time_limit": 300,
                "slice_size": 0.1
            },
            ml_config={
                "models": ["neural_network", "reinforcement_learning"],
                "features": ["volume_profile", "spread", "momentum"],
                "optimization_objective": "minimize_impact",
                "learning_rate": 0.001
            },
            risk_limits={
                "max_slippage": 0.002,
                "max_execution_time": 600,
                "min_fill_rate": 0.95
            },
            _parameter_bounds={
                "max_market_impact": ParameterBounds(min_value=0.0001, max_value=0.01, data_type=float, default_value=0.001),
                "execution_time_limit": ParameterBounds(min_value=60, max_value=1800, data_type=int, default_value=300),
                "slice_size": ParameterBounds(min_value=0.01, max_value=0.5, data_type=float, default_value=0.1)
            }
        )
        
        # Add templates to registry
        self.templates[ml_momentum_template.metadata.template_id] = ml_momentum_template
        self.templates[adaptive_risk_template.metadata.template_id] = adaptive_risk_template
        self.templates[smart_execution_template.metadata.template_id] = smart_execution_template
        
        # Update indices
        self._update_indices()
    
    def _update_indices(self):
        """Update template indices for fast lookup"""
        # Clear indices
        for key in self.template_index:
            self.template_index[key] = {}
        
        # Rebuild indices
        for template_id, template in self.templates.items():
            # By category
            category = template.metadata.category.value
            if category not in self.template_index['by_category']:
                self.template_index['by_category'][category] = []
            self.template_index['by_category'][category].append(template_id)
            
            # By type
            template_type = template.metadata.template_type.value
            if template_type not in self.template_index['by_type']:
                self.template_index['by_type'][template_type] = []
            self.template_index['by_type'][template_type].append(template_id)
            
            # By status
            status = template.metadata.status.value
            if status not in self.template_index['by_status']:
                self.template_index['by_status'][status] = []
            self.template_index['by_status'][status].append(template_id)
            
            # By ML features
            for feature in template.metadata.ml_features:
                if feature not in self.template_index['by_ml_features']:
                    self.template_index['by_ml_features'][feature] = []
                self.template_index['by_ml_features'][feature].append(template_id)
    
    def get_template(self, template_id: str) -> Optional[TradeEngineTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, 
                      category: Optional[TradeEngineTemplateCategory] = None,
                      template_type: Optional[TradeEngineTemplateType] = None,
                      status: Optional[TemplateStatus] = None) -> List[TradeEngineTemplate]:
        """List templates with optional filtering"""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.metadata.category == category]
        if template_type:
            templates = [t for t in templates if t.metadata.template_type == template_type]
        if status:
            templates = [t for t in templates if t.metadata.status == status]
        
        return templates
    
    def _load_registry(self):
        """Load registry from file"""
        try:
            if self.registry_path.exists():
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                
                # Load templates
                for template_data in data.get('templates', []):
                    metadata_data = template_data['metadata']
                    
                    # Convert string dates back to datetime
                    metadata_data['created_at'] = datetime.fromisoformat(metadata_data['created_at'])
                    metadata_data['updated_at'] = datetime.fromisoformat(metadata_data['updated_at'])
                    
                    # Convert string enums back to enum values
                    metadata_data['category'] = TradeEngineTemplateCategory(metadata_data['category'])
                    metadata_data['template_type'] = TradeEngineTemplateType(metadata_data['template_type'])
                    metadata_data['status'] = TemplateStatus(metadata_data['status'])
                    
                    metadata = TradeEngineTemplateMetadata(**metadata_data)
                    
                    template = TradeEngineTemplate(
                        metadata=metadata,
                        configuration=template_data.get('configuration', {}),
                        parameters=template_data.get('parameters', {}),
                        ml_config=template_data.get('ml_config', {}),
                        risk_limits=template_data.get('risk_limits', {})
                    )
                    
                    self.templates[template.metadata.template_id] = template
                
                # Load indices
                self.template_index = data.get('template_index', self.template_index)
                
                self.logger.info(f"Loaded {len(self.templates)} templates from trade engine registry")
            
        except Exception as e:
            self.logger.error(f"Failed to load trade engine registry: {e}")
    
    def _save_registry(self):
        """Save registry to file"""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for serialization
            templates_data = []
            for template in self.templates.values():
                template_dict = template.to_dict_serializable()
                templates_data.append(template_dict)
            
            data = {
                'templates': templates_data,
                'template_index': self.template_index,
                'version': '1.0.0',
                'created_at': datetime.now().isoformat()
            }
            
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.templates)} templates to trade engine registry")
            
        except Exception as e:
            self.logger.error(f"Failed to save trade engine registry: {e}")

# Global registry instance
_trade_engine_template_registry = None

def get_trade_engine_template_registry() -> TradeEngineTemplateRegistry:
    """Get global trade engine template registry instance"""
    global _trade_engine_template_registry
    if _trade_engine_template_registry is None:
        _trade_engine_template_registry = TradeEngineTemplateRegistry()
    return _trade_engine_template_registry
