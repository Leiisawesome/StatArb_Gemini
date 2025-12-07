"""
Broker adapters for real broker integration
"""

try:
    from .ibkr_adapter import IBKRAdapter
    _IBKR_AVAILABLE = True
except ImportError:
    _IBKR_AVAILABLE = False
    IBKRAdapter = None

__all__ = ['IBKRAdapter'] if _IBKR_AVAILABLE else []
