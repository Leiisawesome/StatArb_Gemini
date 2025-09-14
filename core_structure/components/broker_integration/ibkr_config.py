#!/usr/bin/env python3
"""
IBKR Configuration - Backward Compatibility Placeholder
======================================================

This module provides backward compatibility for IBKR configuration.
The configuration has been moved to the unified configuration system.

MIGRATION NOTICE:
IBKR configuration is now part of the unified configuration system:
core_structure/configuration/

Author: Professional Trading System Architecture
Version: 3.0.0 (Compatibility Placeholder)
"""

# Backward compatibility placeholder
from core_structure.config import get_config

class IBKRConfig:
    """Legacy IBKR configuration - redirects to unified system"""
    def __init__(self):
        # Placeholder for IBKR-specific configuration
        self.host = "localhost"
        self.port = 7497
        self.client_id = 1
        self.timeout = 30
        self.connection_timeout = 30  # Add missing connection_timeout attribute
        self.broker_name = "interactive_brokers"  # Add missing broker_name attribute

class IBKRSetupHelper:
    """Legacy IBKR setup helper - placeholder"""
    @staticmethod
    def setup():
        return IBKRConfig()

__all__ = ["IBKRConfig", "IBKRSetupHelper"]
