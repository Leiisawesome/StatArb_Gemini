"""
Execution Layer - Professional API
==================================

Order execution, fill processing, and venue routing.

Author: StatArb_Gemini Architecture (Phase 4)
Date: October 23, 2025
Version: 2.0.0
"""

# Execution Components
from .execution_engine import ExecutionEngine
from .execution_manager import ExecutionManager
from .fill_processor import FillProcessor
from .execution_validator import ExecutionValidator

__all__ = [
    'ExecutionEngine',
    'ExecutionManager',
    'FillProcessor',
    'ExecutionValidator',
]

__version__ = '2.0.0'

