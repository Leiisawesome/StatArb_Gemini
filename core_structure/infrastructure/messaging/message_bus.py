"""
Message Bus Module
==================

This module provides the MessageBus class for the 10-component architecture.
It exports the MessageBus from the unified messaging system to maintain compatibility.

This follows the principle of "fail fast, no fallbacks" - if messaging_system is not available,
the import will fail clearly rather than providing fallback behavior.
"""

# Import MessageBus from the unified messaging system - MANDATORY (NO FALLBACKS)
from .messaging_system import (
    MessageBus,
    Message,
    MessageFactory,
    MessagingSystemFactory
)

__all__ = [
    'MessageBus',
    'Message', 
    'MessageFactory',
    'MessagingSystemFactory'
]