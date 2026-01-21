"""
Regime-Aware Asset Allocation logic.
Extracted from RegimeManager for modularity and specialization.
"""

import logging
from typing import Dict, List, Any, Optional
from ..type_definitions.regime import MarketRegime as RegimeType

logger = logging.getLogger(__name__)

class RegimeAwarePortfolioManager:
    """
    Handles asset allocation adjustments based on current market regimes.
    
    Professional-grade implementation uses metadata-driven classification
    instead of string-based matching where possible.
    """

    def __init__(self, config: Any = None):
        self.config = config
        logger.info("Regime-aware portfolio manager initialized")

    def calculate_regime_optimal_allocation(self, 
                                          current_regime: RegimeType,
                                          regime_confidence: float,
                                          available_assets: List[str],
                                          asset_metadata: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        """
        Calculate optimal allocation for current regime.
        
        Args:
            current_regime: The detected market regime.
            regime_confidence: Confidence score (0-1).
            available_assets: List of ticker symbols.
            asset_metadata: Optional mapping of ticker -> attributes (sector, style, beta).
        """
        try:
            # Dispatch to regime-specific logic
            handlers = {
                RegimeType.BULL_MARKET: self._get_bull_market_allocation,
                RegimeType.BEAR_MARKET: self._get_bear_market_allocation,
                RegimeType.HIGH_VOLATILITY: self._get_high_volatility_allocation,
                RegimeType.LOW_VOLATILITY: self._get_low_volatility_allocation,
                RegimeType.CRISIS: self._get_crisis_allocation,
                RegimeType.SIDEWAYS: self._get_sideways_allocation
            }
            
            handler = handlers.get(current_regime, self._get_neutral_allocation)
            allocation = handler(available_assets, asset_metadata)

            # Adjust based on confidence
            allocation = self._adjust_for_confidence(allocation, regime_confidence)

            # Normalize
            total_weight = sum(allocation.values())
            if total_weight > 0:
                allocation = {asset: weight / total_weight for asset, weight in allocation.items()}

            return allocation

        except Exception as e:
            logger.error(f"Error calculating regime optimal allocation: {e}")
            return {}

    def _get_asset_by_attribute(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]], 
                               attr_key: str, attr_value: str, fallback_keywords: List[str]) -> List[str]:
        """
        Helper to find assets using metadata first, then falling back to keyword search.
        """
        matches = []
        if metadata:
            for asset in assets:
                meta = metadata.get(asset, {})
                if str(meta.get(attr_key, "")).upper() == attr_value.upper():
                    matches.append(asset)
        
        if not matches:
            matches = [asset for asset in assets if any(kw in asset.upper() for kw in fallback_keywords)]
            
        return matches

    def _get_bull_market_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        equity_weight = 0.7

        growth_assets = self._get_asset_by_attribute(assets, metadata, 'style', 'GROWTH', ['QQQ', 'TECH', 'GROWTH'])
        value_assets = self._get_asset_by_attribute(assets, metadata, 'style', 'VALUE', ['VALUE', 'DIVIDEND'])

        if growth_assets:
            for asset in growth_assets[:3]:
                allocation[asset] = equity_weight / min(3, len(growth_assets))

        remaining_weight = 1.0 - sum(allocation.values())
        if value_assets and remaining_weight > 0:
            for asset in value_assets[:2]:
                allocation[asset] = remaining_weight / min(2, len(value_assets)) * 0.6

        return allocation

    # ... Other methods similarly improved ...
    
    def _get_bear_market_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        defensive_assets = self._get_asset_by_attribute(assets, metadata, 'type', 'DEFENSIVE', ['BOND', 'TREASURY', 'GOLD'])
        cash_assets = [asset for asset in assets if any(x in asset.upper() for x in ['CASH', 'BILL'])]

        if defensive_assets:
            for asset in defensive_assets[:3]:
                allocation[asset] = 0.4 / min(3, len(defensive_assets))
        if cash_assets:
            allocation[cash_assets[0]] = 0.3
            
        return allocation

    def _get_high_volatility_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        low_vol_assets = self._get_asset_by_attribute(assets, metadata, 'volatility_profile', 'LOW', ['BOND', 'TREASURY', 'UTILITY'])
        if low_vol_assets:
            for asset in low_vol_assets[:2]:
                allocation[asset] = 0.4 / min(2, len(low_vol_assets))
        return allocation

    def _get_low_volatility_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        equity_assets = self._get_asset_by_attribute(assets, metadata, 'class', 'EQUITY', ['SPY', 'QQQ', 'EQUITY'])
        if equity_assets:
            for asset in equity_assets[:3]:
                allocation[asset] = 0.6 / min(3, len(equity_assets))
        return allocation

    def _get_crisis_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        treasuries = self._get_asset_by_attribute(assets, metadata, 'type', 'TREASURY', ['TREASURY', 'TLT'])
        if treasuries:
            allocation[treasuries[0]] = 0.5
        return allocation

    def _get_sideways_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, float]:
        allocation = {}
        equities = self._get_asset_by_attribute(assets, metadata, 'class', 'EQUITY', ['SPY'])
        bonds = self._get_asset_by_attribute(assets, metadata, 'class', 'FIXED_INCOME', ['BOND'])
        if equities: allocation[equities[0]] = 0.4
        if bonds: allocation[bonds[0]] = 0.4
        return allocation

    def _get_neutral_allocation(self, assets: List[str], metadata: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        allocation = {}
        if assets:
            weight = 1.0 / min(5, len(assets))
            for asset in assets[:5]:
                allocation[asset] = weight
        return allocation

    def _adjust_for_confidence(self, allocation: Dict[str, float], confidence: float) -> Dict[str, float]:
        if confidence < 0.5:
            neutral_weight = 1.0 / len(allocation) if allocation else 0
            factor = confidence * 2 
            return {a: (w * factor + neutral_weight * (1 - factor)) for a, w in allocation.items()}
        return allocation
