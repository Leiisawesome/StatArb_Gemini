#!/usr/bin/env python3
"""
Regime-Aware Portfolio Management System
========================================

Phase 2: Advanced Portfolio Management & Multi-Strategy Orchestration

This system builds on Phase 1's regime detection to create an intelligent
portfolio manager that dynamically allocates capital and manages risk based
on market regimes across multiple strategies.

Key Features:
- Regime-based strategy allocation
- Dynamic risk budgeting by regime
- Cross-strategy correlation management
- Unified position sizing framework
- Performance attribution by regime and strategy
- Institutional-grade portfolio optimization

Author: Professional Quant Enhancement - Phase 2
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json

# Import Phase 1 regime detection
try:
    from ..market_regime.professional_regime_system import (
        get_professional_regime_system, 
        ProfessionalRegimeSystem
    )
    PROFESSIONAL_REGIME_AVAILABLE = True
except ImportError:
    get_professional_regime_system = None
    ProfessionalRegimeSystem = None
    PROFESSIONAL_REGIME_AVAILABLE = False

# Import existing portfolio and risk management
from .portfolio_manager import PortfolioManager, PortfolioMetrics
from .unified_portfolio_bridge import UnifiedPortfolioBridge, PortfolioState
from ..risk.unified_risk_manager import UnifiedRiskManager, RiskLimits, TradingMode

logger = logging.getLogger(__name__)

class RegimeAllocationMode(Enum):
    """Portfolio allocation modes based on regime"""
    CONSERVATIVE = "conservative"    # Low risk, stable allocations
    BALANCED = "balanced"           # Moderate risk, diversified
    AGGRESSIVE = "aggressive"       # High risk, concentrated
    ADAPTIVE = "adaptive"           # Dynamic based on regime confidence

@dataclass
class RegimeAllocationProfile:
    """Strategy allocation profile for different market regimes"""
    regime_name: str
    momentum_allocation: float      # % allocation to momentum strategy
    mean_reversion_allocation: float # % allocation to mean reversion
    pairs_trading_allocation: float  # % allocation to pairs trading
    cash_allocation: float          # % kept in cash
    risk_multiplier: float          # Risk scaling factor for this regime
    confidence_threshold: float     # Minimum confidence to use this profile
    
    def __post_init__(self):
        """Validate allocation profile"""
        total = (self.momentum_allocation + self.mean_reversion_allocation + 
                self.pairs_trading_allocation + self.cash_allocation)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Allocations must sum to 1.0, got {total}")

@dataclass
class RegimePortfolioState:
    """Extended portfolio state with regime information"""
    base_state: PortfolioState
    current_regime: str
    regime_confidence: float
    regime_duration: int            # Minutes in current regime
    allocation_profile: RegimeAllocationProfile
    strategy_suitability: Dict[str, float]  # Strategy suitability scores
    correlation_matrix: Optional[pd.DataFrame] = None
    regime_transition_probability: float = 0.0
    expected_regime_duration: int = 0

class RegimeAwarePortfolioManager:
    """
    Institutional-Grade Regime-Aware Portfolio Management System
    
    This system coordinates multiple trading strategies based on market regime
    analysis, providing dynamic allocation, risk budgeting, and performance
    attribution across different market conditions.
    """
    
    def __init__(self, 
                 initial_capital: float = 100000.0,
                 trading_mode: TradingMode = TradingMode.PAPER_TRADING,
                 allocation_mode: RegimeAllocationMode = RegimeAllocationMode.ADAPTIVE):
        
        self.initial_capital = initial_capital
        self.trading_mode = trading_mode
        self.allocation_mode = allocation_mode
        
        # Core portfolio management
        self.portfolio_bridge = UnifiedPortfolioBridge(
            initial_capital=initial_capital,
            trading_mode=trading_mode
        )
        
        # Enhanced risk management with regime awareness
        self.risk_manager = UnifiedRiskManager(
            trading_mode=trading_mode,
            initial_capital=initial_capital
        )
        
        # Phase 1 regime detection system
        self.regime_system = get_professional_regime_system() if PROFESSIONAL_REGIME_AVAILABLE else None
        
        # Regime-based allocation profiles
        self.allocation_profiles = self._initialize_allocation_profiles()
        
        # Current state
        self.current_regime_state: Optional[RegimePortfolioState] = None
        self.regime_history: List[RegimePortfolioState] = []
        
        # Strategy tracking
        self.strategy_performance: Dict[str, Dict] = {
            'momentum': {'total_return': 0.0, 'regime_performance': {}},
            'mean_reversion': {'total_return': 0.0, 'regime_performance': {}},
            'pairs_trading': {'total_return': 0.0, 'regime_performance': {}}
        }
        
        # Correlation monitoring
        self.correlation_history: List[pd.DataFrame] = []
        self.correlation_alerts: List[Dict] = []
        
        logger.info(f"🧠 Initialized Regime-Aware Portfolio Manager")
        logger.info(f"   💰 Capital: ${initial_capital:,}")
        logger.info(f"   🎯 Mode: {allocation_mode.value}")
        logger.info(f"   🔬 Regime System: {'✅ Active' if self.regime_system else '❌ Fallback'}")
    
    def _initialize_allocation_profiles(self) -> Dict[str, RegimeAllocationProfile]:
        """Initialize regime-based allocation profiles"""
        
        profiles = {}
        
        # Trending regimes - favor momentum
        profiles['trending'] = RegimeAllocationProfile(
            regime_name='trending',
            momentum_allocation=0.50,      # High momentum allocation
            mean_reversion_allocation=0.20, # Low mean reversion
            pairs_trading_allocation=0.25,  # Moderate pairs
            cash_allocation=0.05,           # Low cash
            risk_multiplier=1.2,            # Higher risk tolerance
            confidence_threshold=0.6
        )
        
        # Sideways/ranging regimes - favor mean reversion
        profiles['sideways'] = RegimeAllocationProfile(
            regime_name='sideways',
            momentum_allocation=0.15,       # Low momentum
            mean_reversion_allocation=0.45, # High mean reversion
            pairs_trading_allocation=0.30,  # High pairs trading
            cash_allocation=0.10,           # Moderate cash
            risk_multiplier=1.0,            # Normal risk
            confidence_threshold=0.6
        )
        
        # Volatile regimes - defensive allocation
        profiles['volatile'] = RegimeAllocationProfile(
            regime_name='volatile',
            momentum_allocation=0.25,       # Moderate momentum
            mean_reversion_allocation=0.25, # Moderate mean reversion
            pairs_trading_allocation=0.30,  # Higher pairs (market neutral)
            cash_allocation=0.20,           # Higher cash buffer
            risk_multiplier=0.8,            # Lower risk tolerance
            confidence_threshold=0.7
        )
        
        # Crisis regimes - very defensive
        profiles['crisis'] = RegimeAllocationProfile(
            regime_name='crisis',
            momentum_allocation=0.10,       # Very low momentum
            mean_reversion_allocation=0.15, # Low mean reversion
            pairs_trading_allocation=0.25,  # Moderate pairs
            cash_allocation=0.50,           # High cash allocation
            risk_multiplier=0.5,            # Very low risk
            confidence_threshold=0.8
        )
        
        # Default/unknown regime - balanced allocation
        profiles['balanced'] = RegimeAllocationProfile(
            regime_name='balanced',
            momentum_allocation=0.30,       # Balanced
            mean_reversion_allocation=0.30, # Balanced
            pairs_trading_allocation=0.30,  # Balanced
            cash_allocation=0.10,           # Moderate cash
            risk_multiplier=1.0,            # Normal risk
            confidence_threshold=0.5
        )
        
        logger.info(f"✅ Initialized {len(profiles)} regime allocation profiles")
        return profiles
    
    async def analyze_regime_and_allocate(self, 
                                        market_data: Dict[str, pd.DataFrame],
                                        current_prices: Dict[str, float]) -> RegimePortfolioState:
        """
        Analyze current market regime and determine optimal portfolio allocation
        
        Args:
            market_data: Market data for all symbols
            current_prices: Current market prices
            
        Returns:
            Updated regime portfolio state
        """
        
        try:
            # Update portfolio with current prices
            self.portfolio_bridge.update_market_prices(current_prices)
            
            # Get regime analysis (Phase 1 integration)
            regime_analysis = await self._get_regime_analysis(market_data)
            
            # Determine allocation profile based on regime
            allocation_profile = self._select_allocation_profile(regime_analysis)
            
            # Calculate strategy suitability scores
            strategy_suitability = self._calculate_strategy_suitability(regime_analysis)
            
            # Update correlation analysis
            correlation_matrix = self._update_correlation_analysis(market_data)
            
            # Create regime portfolio state
            current_state = self.portfolio_bridge.get_portfolio_state()
            regime_state = RegimePortfolioState(
                base_state=current_state,
                current_regime=regime_analysis.get('regime', 'unknown'),
                regime_confidence=regime_analysis.get('regime_confidence', 0.5),
                regime_duration=self._calculate_regime_duration(),
                allocation_profile=allocation_profile,
                strategy_suitability=strategy_suitability,
                correlation_matrix=correlation_matrix,
                regime_transition_probability=regime_analysis.get('transition_probability', 0.0),
                expected_regime_duration=regime_analysis.get('expected_duration', 0)
            )
            
            # Update portfolio allocations
            await self._update_portfolio_allocations(regime_state)
            
            # Store state
            self.current_regime_state = regime_state
            self.regime_history.append(regime_state)
            
            # Log regime change if applicable
            self._log_regime_analysis(regime_state)
            
            return regime_state
            
        except Exception as e:
            logger.error(f"❌ Regime analysis and allocation failed: {e}")
            # Return fallback state
            return await self._create_fallback_state(current_prices)
    
    async def _get_regime_analysis(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get regime analysis from Phase 1 system"""
        
        if not self.regime_system:
            # Fallback regime analysis
            return {
                'regime': 'balanced',
                'regime_confidence': 0.6,
                'momentum_suitability': 0.5,
                'mr_suitability': 0.5,
                'pairs_suitability': 0.5,
                'transition_probability': 0.1,
                'expected_duration': 60
            }
        
        try:
            # Use primary symbol for regime analysis (typically SPY or main trading symbol)
            primary_symbol = list(market_data.keys())[0]
            primary_data = market_data[primary_symbol]
            
            # Get comprehensive regime analysis
            analysis = self.regime_system.analyze_regime_comprehensive(
                symbol=primary_symbol,
                market_data=primary_data
            )
            
            return {
                'regime': analysis.primary_regime,
                'regime_confidence': analysis.overall_confidence,
                'momentum_suitability': getattr(analysis, 'momentum_suitability', 0.5),
                'mr_suitability': getattr(analysis, 'mr_suitability', 0.5),
                'pairs_suitability': getattr(analysis, 'pairs_suitability', 0.5),
                'transition_probability': getattr(analysis, 'regime_transition_warning', 0.1),
                'expected_duration': getattr(analysis, 'expected_regime_duration', 60),
                'risk_adjustment_factor': getattr(analysis, 'risk_adjustment_factor', 1.0)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Professional regime analysis failed, using fallback: {e}")
            return {
                'regime': 'balanced',
                'regime_confidence': 0.5,
                'momentum_suitability': 0.5,
                'mr_suitability': 0.5,
                'pairs_suitability': 0.5,
                'transition_probability': 0.2,
                'expected_duration': 30
            }
    
    def _select_allocation_profile(self, regime_analysis: Dict[str, Any]) -> RegimeAllocationProfile:
        """Select appropriate allocation profile based on regime analysis"""
        
        regime = regime_analysis.get('regime', 'balanced').lower()
        confidence = regime_analysis.get('regime_confidence', 0.5)
        
        # Map regime to allocation profile
        if 'trend' in regime or 'momentum' in regime:
            profile_key = 'trending'
        elif 'sideways' in regime or 'ranging' in regime:
            profile_key = 'sideways'
        elif 'volatile' in regime or 'unstable' in regime:
            profile_key = 'volatile'
        elif 'crisis' in regime or 'crash' in regime:
            profile_key = 'crisis'
        else:
            profile_key = 'balanced'
        
        profile = self.allocation_profiles[profile_key]
        
        # Check confidence threshold
        if confidence < profile.confidence_threshold:
            logger.info(f"⚠️ Low regime confidence ({confidence:.2f}), using balanced profile")
            profile = self.allocation_profiles['balanced']
        
        logger.debug(f"🎯 Selected allocation profile: {profile.regime_name} (confidence: {confidence:.2f})")
        return profile
    
    def _calculate_strategy_suitability(self, regime_analysis: Dict[str, Any]) -> Dict[str, float]:
        """Calculate strategy suitability scores based on regime analysis"""
        
        return {
            'momentum': regime_analysis.get('momentum_suitability', 0.5),
            'mean_reversion': regime_analysis.get('mr_suitability', 0.5),
            'pairs_trading': regime_analysis.get('pairs_suitability', 0.5)
        }
    
    def _update_correlation_analysis(self, market_data: Dict[str, pd.DataFrame]) -> Optional[pd.DataFrame]:
        """Update cross-asset correlation analysis"""
        
        try:
            if len(market_data) < 2:
                return None
            
            # Calculate returns for correlation analysis
            returns_data = {}
            for symbol, data in market_data.items():
                if len(data) >= 20:  # Need minimum data for correlation
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= 10:
                        returns_data[symbol] = returns.tail(20)  # Use last 20 returns
            
            if len(returns_data) < 2:
                return None
            
            # Create correlation matrix
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            # Store correlation history
            self.correlation_history.append(correlation_matrix)
            if len(self.correlation_history) > 100:  # Keep last 100 correlation matrices
                self.correlation_history.pop(0)
            
            # Check for high correlations (risk alert)
            self._check_correlation_alerts(correlation_matrix)
            
            return correlation_matrix
            
        except Exception as e:
            logger.warning(f"⚠️ Correlation analysis failed: {e}")
            return None
    
    def _check_correlation_alerts(self, correlation_matrix: pd.DataFrame):
        """Check for dangerous correlation levels"""
        
        try:
            # Find high correlations (excluding diagonal)
            high_corr_threshold = 0.8
            mask = np.triu(np.ones_like(correlation_matrix, dtype=bool), k=1)
            high_correlations = correlation_matrix.where(mask).abs() > high_corr_threshold
            
            if high_correlations.any().any():
                # Create correlation alert
                alert = {
                    'timestamp': datetime.now(),
                    'type': 'high_correlation',
                    'severity': 'HIGH',
                    'message': f"High correlation detected (>{high_corr_threshold})",
                    'correlation_matrix': correlation_matrix.to_dict()
                }
                
                self.correlation_alerts.append(alert)
                logger.warning(f"🚨 High correlation alert: {alert['message']}")
                
                # Keep only recent alerts
                if len(self.correlation_alerts) > 50:
                    self.correlation_alerts.pop(0)
                    
        except Exception as e:
            logger.error(f"❌ Correlation alert check failed: {e}")
    
    def _calculate_regime_duration(self) -> int:
        """Calculate how long we've been in the current regime"""
        
        if not self.regime_history:
            return 0
        
        current_regime = self.current_regime_state.current_regime if self.current_regime_state else 'unknown'
        duration = 0
        
        # Count consecutive periods in same regime
        for state in reversed(self.regime_history):
            if state.current_regime == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    async def _update_portfolio_allocations(self, regime_state: RegimePortfolioState):
        """Update portfolio allocations based on regime analysis"""
        
        try:
            profile = regime_state.allocation_profile
            
            # Create new allocation dictionary
            new_allocations = {
                'momentum': profile.momentum_allocation,
                'mean_reversion': profile.mean_reversion_allocation,
                'pairs_trading': profile.pairs_trading_allocation
            }
            
            # Apply risk adjustment based on regime confidence
            risk_adjustment = regime_state.regime_confidence * profile.risk_multiplier
            
            # Update portfolio bridge allocations
            self.portfolio_bridge.update_strategy_allocations(new_allocations)
            
            # Update risk manager with new risk profile
            await self._update_risk_profile(regime_state, risk_adjustment)
            
            logger.info(f"📊 Updated portfolio allocations for {regime_state.current_regime} regime:")
            logger.info(f"   🚀 Momentum: {profile.momentum_allocation:.1%}")
            logger.info(f"   🔄 Mean Reversion: {profile.mean_reversion_allocation:.1%}")
            logger.info(f"   ⚖️ Pairs Trading: {profile.pairs_trading_allocation:.1%}")
            logger.info(f"   💰 Cash: {profile.cash_allocation:.1%}")
            logger.info(f"   🎯 Risk Multiplier: {risk_adjustment:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update portfolio allocations: {e}")
    
    async def _update_risk_profile(self, regime_state: RegimePortfolioState, risk_adjustment: float):
        """Update risk management profile based on regime"""
        
        try:
            # Create regime-adjusted risk limits
            base_limits = self.risk_manager.risk_limits
            
            # Adjust risk limits based on regime
            adjusted_limits = RiskLimits(
                max_position_size_pct=base_limits.max_position_size_pct * risk_adjustment,
                max_portfolio_drawdown=base_limits.max_portfolio_drawdown / risk_adjustment,
                daily_loss_limit=base_limits.daily_loss_limit / risk_adjustment,
                target_portfolio_volatility=base_limits.target_portfolio_volatility * risk_adjustment,
                default_stop_loss_pct=base_limits.default_stop_loss_pct / risk_adjustment,
                default_take_profit_pct=base_limits.default_take_profit_pct * risk_adjustment
            )
            
            # Update risk manager
            self.risk_manager.risk_limits = adjusted_limits
            
            logger.debug(f"🛡️ Updated risk profile for {regime_state.current_regime} regime")
            
        except Exception as e:
            logger.error(f"❌ Failed to update risk profile: {e}")
    
    async def _create_fallback_state(self, current_prices: Dict[str, float]) -> RegimePortfolioState:
        """Create fallback regime state when analysis fails"""
        
        current_state = self.portfolio_bridge.get_portfolio_state()
        fallback_profile = self.allocation_profiles['balanced']
        
        return RegimePortfolioState(
            base_state=current_state,
            current_regime='balanced',
            regime_confidence=0.5,
            regime_duration=0,
            allocation_profile=fallback_profile,
            strategy_suitability={'momentum': 0.5, 'mean_reversion': 0.5, 'pairs_trading': 0.5}
        )
    
    def _log_regime_analysis(self, regime_state: RegimePortfolioState):
        """Log regime analysis results"""
        
        # Check for regime change
        regime_changed = (
            not self.regime_history or 
            self.regime_history[-1].current_regime != regime_state.current_regime
        )
        
        if regime_changed:
            logger.info(f"🔄 REGIME CHANGE: {regime_state.current_regime.upper()}")
            logger.info(f"   📊 Confidence: {regime_state.regime_confidence:.1%}")
            logger.info(f"   ⏱️ Expected Duration: {regime_state.expected_regime_duration} minutes")
            logger.info(f"   🎯 Strategy Suitability:")
            for strategy, suitability in regime_state.strategy_suitability.items():
                logger.info(f"      {strategy}: {suitability:.1%}")
    
    def get_performance_attribution(self) -> Dict[str, Any]:
        """Get comprehensive performance attribution by regime and strategy"""
        
        if not self.regime_history:
            return {}
        
        # Calculate performance by regime
        regime_performance = {}
        strategy_performance = {}
        
        for state in self.regime_history:
            regime = state.current_regime
            if regime not in regime_performance:
                regime_performance[regime] = {
                    'duration': 0,
                    'total_return': 0.0,
                    'count': 0
                }
            
            regime_performance[regime]['duration'] += 1
            regime_performance[regime]['count'] += 1
            # Note: Would need actual P&L tracking to calculate returns
        
        return {
            'regime_performance': regime_performance,
            'strategy_performance': self.strategy_performance,
            'correlation_alerts': len(self.correlation_alerts),
            'total_regime_changes': len(set(s.current_regime for s in self.regime_history))
        }
    
    def get_current_allocations(self) -> Dict[str, float]:
        """Get current strategy allocations"""
        
        if self.current_regime_state:
            profile = self.current_regime_state.allocation_profile
            return {
                'momentum': profile.momentum_allocation,
                'mean_reversion': profile.mean_reversion_allocation,
                'pairs_trading': profile.pairs_trading_allocation,
                'cash': profile.cash_allocation
            }
        
        return {'momentum': 0.33, 'mean_reversion': 0.33, 'pairs_trading': 0.34, 'cash': 0.0}
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get current regime summary for monitoring"""
        
        if not self.current_regime_state:
            return {'status': 'not_initialized'}
        
        state = self.current_regime_state
        
        return {
            'current_regime': state.current_regime,
            'regime_confidence': state.regime_confidence,
            'regime_duration_minutes': state.regime_duration,
            'allocation_profile': state.allocation_profile.regime_name,
            'strategy_suitability': state.strategy_suitability,
            'transition_probability': state.regime_transition_probability,
            'expected_duration': state.expected_regime_duration,
            'portfolio_value': state.base_state.total_value,
            'correlation_alerts': len(self.correlation_alerts)
        }

# Factory function for easy initialization
def create_regime_aware_portfolio_manager(
    initial_capital: float = 100000.0,
    trading_mode: TradingMode = TradingMode.PAPER_TRADING,
    allocation_mode: RegimeAllocationMode = RegimeAllocationMode.ADAPTIVE
) -> RegimeAwarePortfolioManager:
    """
    Factory function to create a regime-aware portfolio manager
    
    Args:
        initial_capital: Starting capital
        trading_mode: Trading mode (paper/live)
        allocation_mode: Allocation strategy mode
        
    Returns:
        Configured RegimeAwarePortfolioManager instance
    """
    
    return RegimeAwarePortfolioManager(
        initial_capital=initial_capital,
        trading_mode=trading_mode,
        allocation_mode=allocation_mode
    )
