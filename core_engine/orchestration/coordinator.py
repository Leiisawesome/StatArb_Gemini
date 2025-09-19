#!/usr/bin/env python3
"""
System Orchestrator - Core Engine
=================================

Clean implementation of the SystemOrchestrator for core_engine.
Leverages existing high-quality code from core_structure but with clean interfaces.

Migration: Preserves institutional-grade coordination while removing delegation overhead.

Author: StatArb_Gemini Core Engine Migration
Version: 1.0.0 (Clean Production)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import threading

# Leverage existing types from core_structure
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core_structure.infrastructure.system_orchestrator import (
    ModuleStatus, 
    OrchestrationConfig,
    ModuleInfo
)

# Add missing orchestration imports
try:
    from .workflow_manager import WorkflowManager, WorkflowStep, TaskPriority
except ImportError:
    WorkflowManager = WorkflowStep = TaskPriority = None

try:
    from .scheduler import TaskScheduler, ScheduledTask, ScheduleType
except ImportError:
    TaskScheduler = ScheduledTask = ScheduleType = None

try:
    from .state_manager import StateManager, SystemState, ComponentState
except ImportError:
    StateManager = SystemState = ComponentState = None

try:
    from .event_dispatcher import EventDispatcher, EventType, EventPriority
except ImportError:
    EventDispatcher = EventType = EventPriority = None

try:
    from ..types.strategy import StrategyInterface
except ImportError:
    StrategyInterface = None

logger = logging.getLogger(__name__)

class ComponentStatus(Enum):
    """Core Engine component status"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass 
class ComponentInfo:
    """Information about core engine component"""
    name: str
    status: ComponentStatus
    initialized_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None

class SystemOrchestrator:
    """
    Enhanced Core Engine Orchestration Coordinator
    Manages component lifecycle, workflow orchestration, scheduling, and system coordination
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = OrchestrationConfig(**config) if config else OrchestrationConfig()
        self.components: Dict[str, Any] = {}
        self.component_info: Dict[str, ComponentInfo] = {}
        self.is_initialized = False
        self.is_running = False
        
        logger.info("🎼 System Orchestrator initialized - Core Engine coordination ready")
    
    async def initialize(self) -> bool:
        """Initialize orchestrator"""
        try:
            self.is_initialized = True
            logger.info("✅ System Orchestrator initialized")
            return True
        except Exception as e:
            logger.error(f"❌ System Orchestrator initialization failed: {e}")
            raise
    
    def register_components(self, components: Dict[str, Any]):
        """Register all core engine components"""
        for name, component in components.items():
            self.components[name] = component
            self.component_info[name] = ComponentInfo(
                name=name,
                status=ComponentStatus.UNINITIALIZED
            )
            logger.info(f"📝 Registered component: {name}")
        
        logger.info(f"✅ Registered {len(components)} core engine components")
    
    async def start_trading_session(self) -> bool:
        """Start all components for trading session"""
        try:
            logger.info("🚀 Starting trading session - orchestrating component startup...")
            
            # Start components in dependency order
            startup_order = [
                'data',      # Data feeds first
                'regime',    # Market condition assessment
                'brokers',   # Broker connections 
                'portfolio', # Portfolio tracking
                'risk',      # Risk management (Central Hub)
                'execution', # Execution engine
                'trading',   # Trading logic
                'strategies', # Strategy management
                'analytics'  # Performance monitoring
            ]
            
            for component_name in startup_order:
                if component_name in self.components:
                    await self._start_component(component_name)
            
            self.is_running = True
            logger.info("✅ Trading session started - all components running")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading session: {e}")
            await self._emergency_stop()
            raise
    
    async def stop_trading_session(self) -> bool:
        """Stop trading session gracefully"""
        try:
            logger.info("🛑 Stopping trading session...")
            
            # Stop components in reverse order
            stop_order = [
                'analytics',
                'strategies', 
                'trading',
                'execution',
                'risk',
                'portfolio',
                'brokers',
                'regime',
                'data'
            ]
            
            for component_name in stop_order:
                if component_name in self.components:
                    await self._stop_component(component_name)
            
            self.is_running = False
            logger.info("✅ Trading session stopped gracefully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop trading session: {e}")
            return False
    
    async def emergency_shutdown(self):
        """Emergency shutdown all components immediately"""
        logger.warning("🚨 EMERGENCY SHUTDOWN - Stopping all components immediately")
        
        for component_name, component in self.components.items():
            try:
                if hasattr(component, 'emergency_stop'):
                    await component.emergency_stop()
                elif hasattr(component, 'stop'):
                    await component.stop()
                
                self.component_info[component_name].status = ComponentStatus.STOPPED
                logger.warning(f"🚨 Emergency stopped: {component_name}")
                
            except Exception as e:
                logger.error(f"🚨 Failed to emergency stop {component_name}: {e}")
                self.component_info[component_name].status = ComponentStatus.ERROR
        
        self.is_running = False
        logger.warning("🚨 EMERGENCY SHUTDOWN COMPLETE")
    
    async def _start_component(self, component_name: str):
        """Start individual component"""
        try:
            component = self.components[component_name]
            info = self.component_info[component_name]
            
            logger.info(f"🔄 Starting component: {component_name}")
            info.status = ComponentStatus.INITIALIZING
            
            # Start component if it has start method
            if hasattr(component, 'start'):
                await component.start()
            elif hasattr(component, 'startup'):
                await component.startup()
            
            info.status = ComponentStatus.RUNNING
            info.started_at = datetime.now()
            
            logger.info(f"✅ Component started: {component_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start component {component_name}: {e}")
            self.component_info[component_name].status = ComponentStatus.ERROR
            self.component_info[component_name].last_error = str(e)
            self.component_info[component_name].error_count += 1
            raise
    
    async def _stop_component(self, component_name: str):
        """Stop individual component"""
        try:
            component = self.components[component_name]
            info = self.component_info[component_name]
            
            logger.info(f"🛑 Stopping component: {component_name}")
            info.status = ComponentStatus.STOPPING
            
            # Stop component if it has stop method
            if hasattr(component, 'stop'):
                await component.stop()
            elif hasattr(component, 'shutdown'):
                await component.shutdown()
            
            info.status = ComponentStatus.STOPPED
            logger.info(f"✅ Component stopped: {component_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop component {component_name}: {e}")
            self.component_info[component_name].status = ComponentStatus.ERROR
            self.component_info[component_name].last_error = str(e)
            self.component_info[component_name].error_count += 1
    
    async def _emergency_stop(self):
        """Emergency stop during startup failure"""
        logger.warning("🚨 Emergency stop during startup failure")
        
        for component_name in self.components:
            if self.component_info[component_name].status == ComponentStatus.RUNNING:
                try:
                    await self._stop_component(component_name)
                except:
                    pass  # Best effort during emergency
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'orchestrator': {
                'initialized': self.is_initialized,
                'running': self.is_running,
                'components_count': len(self.components)
            },
            'components': {
                name: {
                    'status': info.status.value,
                    'initialized_at': info.initialized_at.isoformat() if info.initialized_at else None,
                    'started_at': info.started_at.isoformat() if info.started_at else None,
                    'error_count': info.error_count,
                    'last_error': info.last_error
                }
                for name, info in self.component_info.items()
            },
            'health': {
                'healthy_components': len([
                    info for info in self.component_info.values() 
                    if info.status == ComponentStatus.RUNNING
                ]),
                'total_components': len(self.component_info),
                'error_components': len([
                    info for info in self.component_info.values()
                    if info.status == ComponentStatus.ERROR
                ])
            }
        }
    
    def is_system_healthy(self) -> bool:
        """Check if system is healthy"""
        if not self.is_running:
            return False
        
        error_components = [
            info for info in self.component_info.values()
            if info.status == ComponentStatus.ERROR
        ]
        
        return len(error_components) == 0