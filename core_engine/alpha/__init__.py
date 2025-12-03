"""
Alpha Module - ADS v3.0 Compliant Components
=============================================

Core alpha components implementing the ADS v3.0 Alpha Design Philosophy.

Components:
- SignalMaturityScore (SMS) - §1 Multiplicative signal maturation
- ERAR - §3 Expected Risk-Adjusted Return gate
- Cooldown (PVSI) - §8 PnL volatility-based cooldown
- PendingSignalQueue - Signal maturation queue management

Usage:
    from core_engine.alpha import SignalMaturityScore, ERAR, Cooldown
    
    # Create SMS for signal evaluation
    sms = SignalMaturityScore(
        exhaustion=0.7,
        reversal_prob=0.65,
        ofi_shift=0.1,
        vol_compression=0.8
    )
    
    if sms.is_mature(threshold=0.5, regime='normal'):
        # Check ERAR
        erar = ERAR(expected_pnl=15.0, cvar_95=25.0, spread_bps=2.0)
        if erar.should_trade(gamma=0.5):
            # Execute trade
            pass
"""

from .ads_components import (
    # §1 Signal Maturity Score
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

