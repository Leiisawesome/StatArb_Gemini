"""
Alpha Module - ADS v5.0 Simplified Components
=============================================

Core alpha components implementing the expert-reviewed simplification.

v5.0 Changes (Expert Review):
- UNIFIED REVERSAL SCORE: Replaces multiplicative SMS + 5-factor exhaustion
- REGIME-CONDITIONED Z-SCORE: Median/MAD instead of mean/std
- SIMPLE EDGE RATIO: Replaces complex ERAR CVaR modeling
- THESIS INVALIDATION: Time/trend/regime exits instead of PnL-based
- STRUCTURE CONFIRMATION: Higher low / lower high instead of indicator crossovers

Design Philosophy:
- "If it can't make money without stacked filters, there is no real edge."
- 4 orthogonal features: Stretch, Exhaustion, Flow, Volatility

Legacy Components (still available for backwards compatibility):
- SignalMaturityScore (SMS) - §1 Multiplicative signal maturation
- ERAR - §3 Expected Risk-Adjusted Return gate
- Cooldown (PVSI) - §8 PnL volatility-based cooldown

Usage (v5.0 recommended):
    from core_engine.alpha import UnifiedReversalScore, RegimeAdjustedZScore
    
    # Compute reversal score
    scorer = UnifiedReversalScore()
    score, breakdown = scorer.compute(
        stretch=2.1,      # Regime-adjusted z-score
        exhaustion=0.7,   # RSI momentum exhaustion
        flow=0.3,         # Volume-based flow signal
        volatility=0.8,   # ATR compression ratio
        regime='normal'
    )
    
    if scorer.should_trade(score, threshold=0.5):
        # Execute trade
        pass
"""

# =============================================================================
# v5.0 SIMPLIFIED COMPONENTS (RECOMMENDED)
# =============================================================================
from .simplified_components import (
    # Unified scoring (replaces SMS + 5-factor + ERAR)
    UnifiedReversalScore,
    
    # Robust z-score (replaces naive rolling mean/std)
    RegimeAdjustedZScore,
    
    # Simple edge ratio (replaces complex ERAR)
    SimpleEdgeRatio,
    
    # Thesis invalidation (for exit logic)
    ThesisInvalidation,
    
    # Helper functions
    compute_momentum_exhaustion,
    compute_flow_signal,
    compute_volatility_signal,
    check_structure_confirmation,
)

# =============================================================================
# LEGACY COMPONENTS (for backwards compatibility)
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

    # Helper functions (legacy)
    compute_exhaustion,
    compute_reversal_probability,
    compute_vol_compression,
    estimate_expected_pnl,
    estimate_cvar_95,
)

__all__ = [
    # v5.0 Simplified (recommended)
    'UnifiedReversalScore',
    'RegimeAdjustedZScore',
    'SimpleEdgeRatio',
    'ThesisInvalidation',
    'compute_momentum_exhaustion',
    'compute_flow_signal',
    'compute_volatility_signal',
    'check_structure_confirmation',
    
    # Legacy (backwards compatibility)
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

