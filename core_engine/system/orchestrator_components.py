"""
Component Management Module for HierarchicalSystemOrchestrator
============================================================

Handles component registration, lifecycle management, and health monitoring.
Extracted from the main orchestrator for better maintainability.

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Modular Architecture)
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ComponentLayer(Enum):
    """Component layers in hierarchical control"""
    ORCHESTRATION = "orchestration"    # Layer 1: System control
    GOVERNANCE = "governance"          # Layer 2: Risk/Trading governance
    EXECUTION = "execution"            # Layer 3: Trading operations
    SUPPORT = "support"                # Support components


class AuthorityLevel(Enum):
    """Authority levels for different operations"""
    SYSTEM_CONTROL = "system_control"        # SystemOrchestrator only
    GOVERNANCE_CONTROL = "governance_control" # RiskManager authority
    STRATEGIC = "strategic"                  # Strategic operations
    TACTICAL = "tactical"                    # Tactical operations
    OPERATIONAL = "operational"              # Component operations
    READ_ONLY = "read_only"                 # Monitoring only


@dataclass
class ComponentRegistration:
    """Component registration with hierarchical control info"""
    
    component_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    layer: ComponentLayer = ComponentLayer.SUPPORT
    authority_level: AuthorityLevel = AuthorityLevel.READ_ONLY
    
    # Hierarchical relationships
    reports_to: Optional[str] = None  # Parent component ID
    controls: List[str] = field(default_factory=list)  # Child component IDs
    
    # Component instance and metadata
    component_instance: Optional[Any] = None
    initialization_order: int = 100  # Lower numbers initialize first
    shutdown_order: int = 100       # Lower numbers shutdown last
    
    # Status tracking
    status: str = "unregistered"
    last_heartbeat: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Authority and permissions
    allowed_operations: Set[str] = field(default_factory=set)
    required_permissions: Set[str] = field(default_factory=set)
    
    # Health monitoring
    health_check_interval: int = 30  # seconds
    max_error_count: int = 5
    
    def update_status(self, status: str, error: Optional[str] = None) -> None:
        """Update component status"""
        self.status = status
        self.last_heartbeat = datetime.now()
        
        if error:
            self.last_error = error
            self.error_count += 1


class ComponentManager:
    """Manages component registration, lifecycle, and health monitoring"""
    
    def __init__(self):
        self.component_registry: Dict[str, ComponentRegistration] = {}
        self.layer_components: Dict[ComponentLayer, List[str]] = {
            layer: [] for layer in ComponentLayer
        }
        
    def register_component(self, name: str, component: Any, 
                         layer: ComponentLayer = ComponentLayer.SUPPORT,
                         authority_level: AuthorityLevel = AuthorityLevel.READ_ONLY,
                         initialization_order: int = 100,
                         reports_to: Optional[str] = None) -> str:
        """Register component with hierarchical control"""
        
        try:
            # Check if this component instance is already registered
            for reg_id, registration in self.component_registry.items():
                if registration.component_instance is component:
                    logger.warning(f"⚠️ Component {name} already registered with id {reg_id}, skipping duplicate registration")
                    return reg_id
            
            registration = ComponentRegistration(
                name=name,
                layer=layer,
                authority_level=authority_level,
                component_instance=component,
                initialization_order=initialization_order,
                reports_to=reports_to
            )
            
            # Store registration
            self.component_registry[registration.component_id] = registration
            self.layer_components[layer].append(registration.component_id)
            
            # Set allowed operations based on authority level
            registration.allowed_operations = self._get_allowed_operations(authority_level)
            
            logger.info(f"📝 Registered {name} (Layer: {layer.value}, Authority: {authority_level.value})")
            return registration.component_id
            
        except Exception as e:
            logger.error(f"❌ Failed to register component {name}: {e}")
            return ""
    
    def _get_allowed_operations(self, authority_level: AuthorityLevel) -> Set[str]:
        """Get allowed operations for authority level"""
        
        operations_by_level = {
            AuthorityLevel.READ_ONLY: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance"
            },
            AuthorityLevel.OPERATIONAL: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance",
                "process_data", "calculate_indicators", "generate_signals", "update_positions"
            },
            AuthorityLevel.TACTICAL: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance",
                "process_data", "calculate_indicators", "generate_signals", "update_positions",
                "execute_trades", "manage_orders", "adjust_positions"
            },
            AuthorityLevel.STRATEGIC: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance",
                "process_data", "calculate_indicators", "generate_signals", "update_positions",
                "execute_trades", "manage_orders", "adjust_positions",
                "allocate_capital", "set_risk_limits", "approve_strategies"
            },
            AuthorityLevel.GOVERNANCE_CONTROL: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance",
                "process_data", "calculate_indicators", "generate_signals", "update_positions",
                "execute_trades", "manage_orders", "adjust_positions",
                "allocate_capital", "set_risk_limits", "approve_strategies",
                "authorize_trades", "emergency_stop", "override_limits"
            },
            AuthorityLevel.SYSTEM_CONTROL: {
                "health_check", "view_status", "read_data", "view_positions", "view_performance",
                "process_data", "calculate_indicators", "generate_signals", "update_positions",
                "execute_trades", "manage_orders", "adjust_positions",
                "allocate_capital", "set_risk_limits", "approve_strategies",
                "authorize_trades", "emergency_stop", "override_limits",
                "system_shutdown", "component_control", "authority_delegation"
            }
        }
        
        return operations_by_level.get(authority_level, set())
    
    async def initialize_components_hierarchically(self) -> bool:
        """Initialize components in hierarchical order with performance optimization"""
        
        try:
            # Get components sorted by initialization order
            components_by_order = sorted(
                self.component_registry.items(),
                key=lambda x: x[1].initialization_order
            )
            
            initialized_count = 0
            
            # Group components by initialization order for concurrent processing
            order_groups = {}
            for component_id, registration in components_by_order:
                order = registration.initialization_order
                if order not in order_groups:
                    order_groups[order] = []
                order_groups[order].append((component_id, registration))
            
            # Initialize components in order groups, but concurrently within each group
            for order in sorted(order_groups.keys()):
                group_components = order_groups[order]
                
                # Create initialization tasks for this order group
                init_tasks = []
                for component_id, registration in group_components:
                    # Skip if already initialized
                    if registration.status == "operational":
                        initialized_count += 1
                        continue
                    
                    init_tasks.append(self._initialize_single_component(component_id, registration))
                
                # Wait for all components in this order group to initialize
                if init_tasks:
                    results = await asyncio.gather(*init_tasks, return_exceptions=True)
                    
                    # Count successful initializations
                    for result in results:
                        if result is True:
                            initialized_count += 1
                        elif isinstance(result, Exception):
                            logger.error(f"❌ Component initialization exception: {result}")
            
            total_components = len(self.component_registry)
            success_rate = initialized_count / total_components if total_components > 0 else 0
            
            logger.info(f"Component initialization: {initialized_count}/{total_components} ({success_rate:.1%})")
            
            # Require at least 80% success rate
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Hierarchical component initialization failed: {e}")
            return False
    
    async def _initialize_single_component(self, component_id: str, registration: ComponentRegistration) -> bool:
        """Initialize a single component with proper error handling"""
        
        try:
            logger.info(f"🔄 Initializing {registration.name}...")
            registration.update_status("initializing")
            
            # Initialize component if it implements ISystemComponent
            if hasattr(registration.component_instance, 'initialize'):
                success = await registration.component_instance.initialize()
                
                if success:
                    registration.update_status("initialized")
                    logger.info(f"✅ {registration.name} initialized")
                    return True
                else:
                    registration.update_status("failed", "Initialization failed")
                    logger.error(f"❌ {registration.name} initialization failed")
                    return False
            else:
                # Assume non-interface components are ready
                registration.update_status("initialized")
                logger.info(f"✅ {registration.name} registered (no initialization required)")
                return True
                
        except Exception as e:
            registration.update_status("failed", str(e))
            logger.error(f"❌ {registration.name} initialization error: {e}")
            return False
    
    async def health_check_components(self) -> None:
        """Perform health checks on all components"""
        
        try:
            for component_id, registration in self.component_registry.items():
                if hasattr(registration.component_instance, 'health_check'):
                    try:
                        health_result = await registration.component_instance.health_check()
                        
                        if health_result.get('healthy', False):
                            registration.update_status("operational")
                        else:
                            registration.update_status("unhealthy", "Health check failed")
                            
                    except Exception as e:
                        registration.update_status("error", f"Health check error: {e}")
                        logger.warning(f"Health check failed for {registration.name}: {e}")
                else:
                    # Assume components without health_check are operational if initialized
                    if registration.status == "initialized":
                        registration.update_status("operational")
                        
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get comprehensive component status"""
        
        status_by_layer = {}
        for layer in ComponentLayer:
            layer_components = []
            for comp_id in self.layer_components[layer]:
                if comp_id in self.component_registry:
                    reg = self.component_registry[comp_id]
                    layer_components.append({
                        'id': comp_id,
                        'name': reg.name,
                        'status': reg.status,
                        'authority': reg.authority_level.value,
                        'error_count': reg.error_count,
                        'last_heartbeat': reg.last_heartbeat.isoformat() if reg.last_heartbeat else None
                    })
            status_by_layer[layer.value] = layer_components
        
        return {
            'total_components': len(self.component_registry),
            'operational_components': len([r for r in self.component_registry.values() 
                                         if r.status == 'operational']),
            'components_by_layer': status_by_layer
        }
