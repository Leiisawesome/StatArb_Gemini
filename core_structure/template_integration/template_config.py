"""
Template Configuration Classes
=============================

Configuration classes and enums for the template integration system.

Author: Pro Quant Desk Trader
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from enum import Enum

from strategy_templates.base import TemplateRegistry, TemplateCategory

class ExecutionMode(Enum):
    """Template execution modes"""
    SINGLE_TEMPLATE = "single_template"          # Execute one template
    INHERITANCE_CHAIN = "inheritance_chain"      # Execute template + parents
    CATEGORY_BATCH = "category_batch"            # Execute all in category
    CROSS_CATEGORY = "cross_category"            # Execute across categories
    ADAPTIVE_ROUTING = "adaptive_routing"        # Route based on performance

@dataclass
class TemplateEngineConfig:
    """Comprehensive configuration for template-compatible core engine"""
    # Core dependencies
    template_registry: Optional[TemplateRegistry] = None
    
    # Template execution settings
    template_execution_mode: ExecutionMode = ExecutionMode.SINGLE_TEMPLATE
    execution_mode: ExecutionMode = ExecutionMode.SINGLE_TEMPLATE  # Alias for compatibility
    enable_inheritance_processing: bool = True
    enable_inheritance_resolution: bool = True  # Alias for compatibility
    enable_category_optimization: bool = True
    enable_performance_tracking: bool = True
    
    # Advanced execution coordination
    max_parallel_templates: int = 5
    max_concurrent_executions: int = 10  # Alias for compatibility
    template_execution_timeout_ms: int = 500
    execution_timeout_ms: float = 5000.0  # Alias for compatibility
    enable_template_load_balancing: bool = True
    
    # Category performance weights (enhanced)
    category_performance_weights: Dict[TemplateCategory, float] = field(default_factory=lambda: {
        TemplateCategory.BASE: 1.0,
        TemplateCategory.SPECIFIC: 1.2,
        TemplateCategory.COMPOSITE: 1.5
    })
    
    # Category-specific risk limits (advanced feature)
    category_risk_limits: Dict[TemplateCategory, Dict[str, float]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {"max_position": 0.05, "max_leverage": 1.5},
        TemplateCategory.SPECIFIC: {"max_position": 0.08, "max_leverage": 2.0},
        TemplateCategory.COMPOSITE: {"max_position": 0.12, "max_leverage": 2.5}
    })
    
    # Advanced inheritance settings
    inheritance_depth_limit: int = 5
    enable_performance_inheritance: bool = True
    inheritance_weight_decay: float = 0.8  # Reduce influence of deeper parents
    
    # Performance optimization settings
    enable_parallel_processing: bool = True
    cache_template_results: bool = True
    cache_size_limit: int = 1000
    
    # Resource management
    memory_limit_mb: int = 1000
    cpu_utilization_limit: float = 0.8
    enable_resource_monitoring: bool = True
    
    # Advanced monitoring settings
    enable_real_time_monitoring: bool = True
    performance_alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'execution_time_ms': 1000.0,
        'success_rate': 0.95,
        'signal_quality': 0.8,
        'latency_ms': 100.0,
        'memory_usage_mb': 500.0
    })
    
    # Template validation settings
    enable_template_validation: bool = True
    strict_inheritance_validation: bool = True
    enable_category_compliance_checks: bool = True
    
    # Load balancing and routing
    enable_adaptive_routing: bool = True
    load_balancing_strategy: str = "performance_weighted"  # Options: "round_robin", "performance_weighted", "category_optimized"
    routing_decision_interval_ms: int = 1000
    
    # Batch processing settings
    enable_batch_processing: bool = True
    batch_size_limit: int = 50
    batch_timeout_ms: int = 2000
    
    # Error handling and recovery
    enable_error_recovery: bool = True
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 1.5
    circuit_breaker_threshold: int = 10  # failures before circuit opens
    
    # Performance tuning
    enable_performance_tuning: bool = True
    auto_scaling_enabled: bool = False
    performance_optimization_interval_ms: int = 5000
    
    # Advanced analytics
    enable_detailed_analytics: bool = True
    analytics_retention_hours: int = 24
    enable_performance_prediction: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Ensure compatibility between aliases
        if self.template_execution_mode != self.execution_mode:
            self.execution_mode = self.template_execution_mode
        
        # Validate timeout settings
        if self.template_execution_timeout_ms > self.execution_timeout_ms:
            self.execution_timeout_ms = self.template_execution_timeout_ms * 10  # Convert to ms if needed
        
        # Validate inheritance settings
        if self.inheritance_depth_limit < 1:
            self.inheritance_depth_limit = 1
        
        if not (0.0 < self.inheritance_weight_decay <= 1.0):
            self.inheritance_weight_decay = 0.8
        
        # Validate performance thresholds
        if 'execution_time_ms' not in self.performance_alert_thresholds:
            self.performance_alert_thresholds['execution_time_ms'] = 1000.0
        
        # Validate category risk limits
        for category in TemplateCategory:
            if category not in self.category_risk_limits:
                self.category_risk_limits[category] = {
                    "max_position": 0.05 + (0.03 * category.value.count('_')),  # Basic heuristic
                    "max_leverage": 1.5 + (0.5 * category.value.count('_'))
                }
    
    def get_category_config(self, category: TemplateCategory) -> Dict[str, Any]:
        """Get category-specific configuration"""
        return {
            'performance_weight': self.category_performance_weights.get(category, 1.0),
            'risk_limits': self.category_risk_limits.get(category, {}),
            'batch_enabled': self.enable_batch_processing,
            'validation_enabled': self.enable_category_compliance_checks
        }
    
    def get_execution_limits(self) -> Dict[str, Any]:
        """Get execution limit configuration"""
        return {
            'max_parallel': self.max_parallel_templates,
            'timeout_ms': self.template_execution_timeout_ms,
            'inheritance_depth': self.inheritance_depth_limit,
            'retry_attempts': self.max_retry_attempts,
            'batch_size': self.batch_size_limit
        }
    
    def is_advanced_mode(self) -> bool:
        """Check if advanced features are enabled"""
        return (
            self.enable_template_load_balancing and
            self.enable_performance_inheritance and
            self.enable_adaptive_routing and
            self.enable_detailed_analytics
        )
