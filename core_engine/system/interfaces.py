"""
System Component Interfaces
==========================

Common interfaces for system components to avoid circular imports.

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Interface Definitions)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ISystemComponent(ABC):
    """Interface for system components under orchestrator control"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize component"""
    
    @abstractmethod
    async def start(self) -> bool:
        """Start component operations"""
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop component operations"""
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
