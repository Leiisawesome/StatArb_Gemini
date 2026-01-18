"""
Alpha Module - ADS Components
=============================

Core alpha components and signal maturation logic.

Components:
- SignalMaturityScore (SMS) - §1 Multiplicative signal maturation
- ERAR - §3 Expected Risk-Adjusted Return gate
- Cooldown (PVSI) - §8 PnL volatility-based cooldown
"""

# =============================================================================
# ADS COMPONENTS
# =============================================================================
from .ads_components import (
    # §1 Signal Maturity Score
    ADSSMSGateInputs,
    SignalMaturityScore,

    # §3 ERAR Gate
    ERAR,

    # §8 Cooldown
    Cooldown,

    # Pending Signal Management
    PendingSignalContext,
    PendingSignalQueue,

    # Helper functions
    compute_exhaustion,
    compute_reversal_probability,
    compute_vol_compression,
    estimate_expected_pnl,
    estimate_cvar_95,
)

__all__ = [
    'ADSSMSGateInputs',
    'SignalMaturityScore',
    'ERAR',
    'Cooldown',
    'PendingSignalContext',
    'PendingSignalQueue',
    'compute_exhaustion',
    'compute_reversal_probability',
    'compute_vol_compression',
    'estimate_expected_pnl',
    'estimate_cvar_95',
]

