"""
Symbol-Strategy Matcher

Matches symbols with optimal strategies based on characteristics.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from .symbol_analyzer import (
    SymbolCharacteristics,
    VolatilityCategory,
    LiquidityCategory,
    TrendCategory
)


class StrategyType(Enum):
    """Strategy types for matching"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    PAIRS_TRADING = "pairs_trading"
    FACTOR = "factor"
    VOLATILITY = "volatility"
    MULTI_ASSET = "multi_asset"
    ARBITRAGE = "arbitrage"


@dataclass
class StrategyMatch:
    """Strategy match result"""
    
    symbol: str
    strategy_type: StrategyType
    suitability_score: float  # 0-100
    confidence: float  # 0-1
    
    # Component scores
    volatility_match: float  # 0-100
    liquidity_match: float  # 0-100
    trend_match: float  # 0-100
    correlation_match: float  # 0-100
    
    # Reasoning
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['strategy_type'] = self.strategy_type.value
        return data


class SymbolStrategyMatcher:
    """
    Matches symbols with optimal strategies.
    
    Features:
    - Multi-factor strategy matching
    - Suitability scoring
    - Confidence estimation
    - Detailed reasoning
    """
    
    def __init__(self):
        """Initialize matcher"""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Define strategy preferences
        self.strategy_preferences = self._define_strategy_preferences()
        
        self.logger.info("SymbolStrategyMatcher initialized")
    
    def _define_strategy_preferences(self) -> Dict[StrategyType, Dict[str, Any]]:
        """
        Define preferences for each strategy type.
        
        Returns:
            Dictionary mapping strategies to their preferences
        """
        return {
            StrategyType.MOMENTUM: {
                'volatility': [VolatilityCategory.MEDIUM, VolatilityCategory.HIGH],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.STRONG_UP, TrendCategory.STRONG_DOWN],
                'min_liquidity_score': 60.0,
                'ideal_volatility_range': (0.25, 0.50),
                'ideal_trend_strength': 0.002
            },
            StrategyType.MEAN_REVERSION: {
                'volatility': [VolatilityCategory.LOW, VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS],
                'min_liquidity_score': 70.0,
                'ideal_volatility_range': (0.15, 0.30),
                'ideal_trend_strength': 0.0005
            },
            StrategyType.STATISTICAL_ARBITRAGE: {
                'volatility': [VolatilityCategory.LOW, VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS, TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN],
                'min_liquidity_score': 80.0,
                'ideal_volatility_range': (0.15, 0.35),
                'ideal_trend_strength': 0.001
            },
            StrategyType.TREND_FOLLOWING: {
                'volatility': [VolatilityCategory.MEDIUM, VolatilityCategory.HIGH],
                'liquidity': [LiquidityCategory.MEDIUM, LiquidityCategory.HIGH],
                'trend': [TrendCategory.STRONG_UP, TrendCategory.STRONG_DOWN, 
                         TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN],
                'min_liquidity_score': 50.0,
                'ideal_volatility_range': (0.25, 0.50),
                'ideal_trend_strength': 0.0015
            },
            StrategyType.BREAKOUT: {
                'volatility': [VolatilityCategory.MEDIUM, VolatilityCategory.HIGH, VolatilityCategory.VERY_HIGH],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS, TrendCategory.MODERATE_UP],
                'min_liquidity_score': 65.0,
                'ideal_volatility_range': (0.30, 0.60),
                'ideal_trend_strength': 0.001
            },
            StrategyType.PAIRS_TRADING: {
                'volatility': [VolatilityCategory.LOW, VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS, TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN],
                'min_liquidity_score': 75.0,
                'ideal_volatility_range': (0.15, 0.35),
                'ideal_trend_strength': 0.0008
            },
            StrategyType.FACTOR: {
                'volatility': [VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.MEDIUM, LiquidityCategory.HIGH],
                'trend': [TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN, TrendCategory.SIDEWAYS],
                'min_liquidity_score': 55.0,
                'ideal_volatility_range': (0.20, 0.40),
                'ideal_trend_strength': 0.001
            },
            StrategyType.VOLATILITY: {
                'volatility': [VolatilityCategory.HIGH, VolatilityCategory.VERY_HIGH],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS, TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN],
                'min_liquidity_score': 70.0,
                'ideal_volatility_range': (0.40, 0.80),
                'ideal_trend_strength': 0.001
            },
            StrategyType.MULTI_ASSET: {
                'volatility': [VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.HIGH, LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.MODERATE_UP, TrendCategory.MODERATE_DOWN, TrendCategory.SIDEWAYS],
                'min_liquidity_score': 60.0,
                'ideal_volatility_range': (0.20, 0.40),
                'ideal_trend_strength': 0.001
            },
            StrategyType.ARBITRAGE: {
                'volatility': [VolatilityCategory.LOW, VolatilityCategory.MEDIUM],
                'liquidity': [LiquidityCategory.VERY_HIGH],
                'trend': [TrendCategory.SIDEWAYS],
                'min_liquidity_score': 85.0,
                'ideal_volatility_range': (0.10, 0.25),
                'ideal_trend_strength': 0.0003
            }
        }
    
    def match_symbol_to_strategy(
        self,
        characteristics: SymbolCharacteristics,
        strategy_type: StrategyType
    ) -> StrategyMatch:
        """
        Match a symbol to a specific strategy.
        
        Args:
            characteristics: Symbol characteristics
            strategy_type: Strategy type to match against
            
        Returns:
            StrategyMatch object with scoring and reasoning
        """
        prefs = self.strategy_preferences[strategy_type]
        
        # Calculate component scores
        vol_match = self._score_volatility_match(characteristics, prefs)
        liq_match = self._score_liquidity_match(characteristics, prefs)
        trend_match = self._score_trend_match(characteristics, prefs)
        corr_match = self._score_correlation_match(characteristics, prefs)
        
        # Calculate overall suitability
        suitability_score = (
            vol_match * 0.30 +
            liq_match * 0.30 +
            trend_match * 0.25 +
            corr_match * 0.15
        )
        
        # Calculate confidence (based on data quality)
        confidence = characteristics.data_quality_score / 100.0
        
        # Generate reasoning
        strengths = self._identify_strengths(
            characteristics, prefs, vol_match, liq_match, trend_match
        )
        weaknesses = self._identify_weaknesses(
            characteristics, prefs, vol_match, liq_match, trend_match
        )
        recommendations = self._generate_recommendations(
            characteristics, prefs, strengths, weaknesses
        )
        
        match = StrategyMatch(
            symbol=characteristics.symbol,
            strategy_type=strategy_type,
            suitability_score=suitability_score,
            confidence=confidence,
            volatility_match=vol_match,
            liquidity_match=liq_match,
            trend_match=trend_match,
            correlation_match=corr_match,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
        
        self.logger.info(
            f"Matched {characteristics.symbol} to {strategy_type.value}: "
            f"score={suitability_score:.1f}, confidence={confidence:.2f}"
        )
        
        return match
    
    def _score_volatility_match(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any]
    ) -> float:
        """Score volatility match (0-100)"""
        
        # Category match
        category_match = 100 if characteristics.volatility_category in prefs['volatility'] else 50
        
        # Range match
        ideal_range = prefs['ideal_volatility_range']
        vol = characteristics.volatility_annualized
        
        if ideal_range[0] <= vol <= ideal_range[1]:
            range_match = 100
        elif vol < ideal_range[0]:
            # Below range
            distance = (ideal_range[0] - vol) / ideal_range[0]
            range_match = max(0, 100 - distance * 100)
        else:
            # Above range
            distance = (vol - ideal_range[1]) / ideal_range[1]
            range_match = max(0, 100 - distance * 100)
        
        return (category_match * 0.4 + range_match * 0.6)
    
    def _score_liquidity_match(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any]
    ) -> float:
        """Score liquidity match (0-100)"""
        
        # Category match
        category_match = 100 if characteristics.liquidity_category in prefs['liquidity'] else 50
        
        # Score match
        min_score = prefs['min_liquidity_score']
        actual_score = characteristics.liquidity_score
        
        if actual_score >= min_score:
            score_match = 100
        else:
            score_match = (actual_score / min_score) * 100
        
        return (category_match * 0.5 + score_match * 0.5)
    
    def _score_trend_match(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any]
    ) -> float:
        """Score trend match (0-100)"""
        
        # Category match
        category_match = 100 if characteristics.trend_category in prefs['trend'] else 50
        
        # Strength match
        ideal_strength = prefs['ideal_trend_strength']
        actual_strength = abs(characteristics.trend_strength)
        
        if abs(actual_strength - ideal_strength) < ideal_strength * 0.5:
            strength_match = 100
        else:
            distance = abs(actual_strength - ideal_strength) / ideal_strength
            strength_match = max(0, 100 - distance * 50)
        
        # Consistency bonus
        consistency_bonus = characteristics.trend_consistency * 20
        
        return (category_match * 0.5 + strength_match * 0.4 + consistency_bonus * 0.1)
    
    def _score_correlation_match(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any]
    ) -> float:
        """Score correlation match (0-100)"""
        
        # Higher diversification is generally better
        return characteristics.diversification_score
    
    def _identify_strengths(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any],
        vol_match: float,
        liq_match: float,
        trend_match: float
    ) -> List[str]:
        """Identify symbol strengths for strategy"""
        
        strengths = []
        
        if vol_match >= 80:
            strengths.append(
                f"Excellent volatility match ({characteristics.volatility_category.value})"
            )
        
        if liq_match >= 80:
            strengths.append(
                f"High liquidity (score: {characteristics.liquidity_score:.1f})"
            )
        
        if trend_match >= 80:
            strengths.append(
                f"Strong trend characteristics ({characteristics.trend_category.value})"
            )
        
        if characteristics.data_quality_score >= 90:
            strengths.append("Excellent data quality")
        
        return strengths
    
    def _identify_weaknesses(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any],
        vol_match: float,
        liq_match: float,
        trend_match: float
    ) -> List[str]:
        """Identify symbol weaknesses for strategy"""
        
        weaknesses = []
        
        if vol_match < 50:
            weaknesses.append(
                f"Volatility mismatch ({characteristics.volatility_category.value})"
            )
        
        if liq_match < 50:
            weaknesses.append(
                f"Low liquidity (score: {characteristics.liquidity_score:.1f})"
            )
        
        if trend_match < 50:
            weaknesses.append(
                f"Trend mismatch ({characteristics.trend_category.value})"
            )
        
        if characteristics.data_quality_score < 70:
            weaknesses.append("Data quality concerns")
        
        return weaknesses
    
    def _generate_recommendations(
        self,
        characteristics: SymbolCharacteristics,
        prefs: Dict[str, Any],
        strengths: List[str],
        weaknesses: List[str]
    ) -> List[str]:
        """Generate recommendations"""
        
        recommendations = []
        
        if len(strengths) >= 3:
            recommendations.append("Strong candidate - proceed with optimization")
        elif len(strengths) >= 2:
            recommendations.append("Good candidate - test with conservative parameters")
        else:
            recommendations.append("Marginal candidate - consider alternatives")
        
        if len(weaknesses) >= 2:
            recommendations.append("Monitor performance closely during testing")
        
        return recommendations
    
    def find_best_strategies(
        self,
        characteristics: SymbolCharacteristics,
        top_n: int = 3
    ) -> List[StrategyMatch]:
        """
        Find best strategies for a symbol.
        
        Args:
            characteristics: Symbol characteristics
            top_n: Number of top strategies to return
            
        Returns:
            List of top N strategy matches, sorted by suitability
        """
        matches = []
        
        for strategy_type in StrategyType:
            match = self.match_symbol_to_strategy(characteristics, strategy_type)
            matches.append(match)
        
        # Sort by suitability score
        matches.sort(key=lambda m: m.suitability_score, reverse=True)
        
        return matches[:top_n]
    
    def create_compatibility_matrix(
        self,
        symbol_characteristics: Dict[str, SymbolCharacteristics]
    ) -> Dict[str, Dict[StrategyType, float]]:
        """
        Create symbol-strategy compatibility matrix.
        
        Args:
            symbol_characteristics: Dictionary of symbol characteristics
            
        Returns:
            Nested dictionary: symbol -> strategy -> suitability_score
        """
        self.logger.info(
            f"Creating compatibility matrix for {len(symbol_characteristics)} symbols"
        )
        
        matrix = {}
        
        for symbol, characteristics in symbol_characteristics.items():
            matrix[symbol] = {}
            
            for strategy_type in StrategyType:
                match = self.match_symbol_to_strategy(characteristics, strategy_type)
                matrix[symbol][strategy_type] = match.suitability_score
        
        self.logger.info("Compatibility matrix created")
        
        return matrix
    
    def get_optimal_assignments(
        self,
        compatibility_matrix: Dict[str, Dict[StrategyType, float]],
        min_score: float = 60.0
    ) -> Dict[StrategyType, List[str]]:
        """
        Get optimal symbol assignments for each strategy.
        
        Args:
            compatibility_matrix: Symbol-strategy compatibility matrix
            min_score: Minimum suitability score
            
        Returns:
            Dictionary mapping strategies to lists of suitable symbols
        """
        assignments = {strategy: [] for strategy in StrategyType}
        
        for symbol, scores in compatibility_matrix.items():
            for strategy, score in scores.items():
                if score >= min_score:
                    assignments[strategy].append((symbol, score))
        
        # Sort symbols by score for each strategy
        for strategy in assignments:
            assignments[strategy].sort(key=lambda x: x[1], reverse=True)
            # Keep only symbols (not scores)
            assignments[strategy] = [sym for sym, score in assignments[strategy]]
        
        self.logger.info(
            f"Generated optimal assignments: "
            f"{sum(len(syms) for syms in assignments.values())} total assignments"
        )
        
        return assignments


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    from .symbol_analyzer import SymbolCharacteristics, VolatilityCategory, LiquidityCategory, TrendCategory
    from datetime import datetime
    
    # Create sample characteristics
    sample_char = SymbolCharacteristics(
        symbol="NVDA",
        analysis_date=datetime.now(),
        volatility_annualized=0.35,
        volatility_category=VolatilityCategory.MEDIUM,
        volatility_percentile=0.6,
        intraday_volatility=0.02,
        avg_daily_volume=5_000_000_000,
        avg_daily_trades=50000,
        liquidity_score=85.0,
        liquidity_category=LiquidityCategory.VERY_HIGH,
        bid_ask_spread_bps=3.0,
        trend_strength=0.002,
        trend_category=TrendCategory.STRONG_UP,
        trend_consistency=0.65,
        momentum_score=75.0,
        market_correlation=0.7,
        sector_correlation=0.8,
        diversification_score=30.0,
        market_cap=2_000_000_000_000,
        avg_price=450.0,
        price_stability=0.85,
        returns_skewness=0.1,
        returns_kurtosis=3.5,
        max_drawdown=0.25,
        overall_quality_score=85.0,
        data_quality_score=95.0
    )
    
    matcher = SymbolStrategyMatcher()
    
    # Find best strategies
    best_strategies = matcher.find_best_strategies(sample_char, top_n=3)
    
    print(f"\nTop 3 strategies for {sample_char.symbol}:")
    for i, match in enumerate(best_strategies, 1):
        print(f"{i}. {match.strategy_type.value}: {match.suitability_score:.1f}")
        print(f"   Strengths: {', '.join(match.strengths)}")

