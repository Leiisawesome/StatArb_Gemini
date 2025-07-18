"""
AI-Powered Insights and Recommendations Engine

Professional-grade AI insights system providing:
- Intelligent pattern detection
- Automated insights generation
- Performance recommendations
- Risk alerts and suggestions
- Market regime analysis
- Strategy optimization recommendations

Author: Pro Quant Desk Trader
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging


class InsightType(Enum):
    """Types of insights"""
    PERFORMANCE = "performance"
    RISK = "risk"
    MARKET = "market"
    STRATEGY = "strategy"
    OPTIMIZATION = "optimization"


class InsightSeverity(Enum):
    """Insight severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Insight:
    """AI-generated insight"""
    insight_id: str
    insight_type: InsightType
    severity: InsightSeverity
    title: str
    description: str
    confidence: float
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Recommendation:
    """AI-generated recommendation"""
    recommendation_id: str
    title: str
    description: str
    action_items: List[str] = field(default_factory=list)
    expected_impact: str = ""
    confidence: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Pattern:
    """Detected pattern"""
    pattern_id: str
    pattern_type: str
    description: str
    strength: float
    detected_at: datetime = field(default_factory=datetime.now)


class PatternDetector:
    """Pattern detection system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def detect_performance_patterns(self, 
                                  returns: pd.Series) -> List[Pattern]:
        """Detect performance patterns"""
        patterns = []
        
        if len(returns) < 20:
            return patterns
        
        # Detect trend patterns
        recent_returns = returns.tail(20)
        trend_strength = recent_returns.corr(pd.Series(range(len(recent_returns))))
        
        if abs(trend_strength) > 0.7:
            pattern = Pattern(
                pattern_id=f"trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                pattern_type="trend",
                description=f"{'Upward' if trend_strength > 0 else 'Downward'} trend detected",
                strength=abs(trend_strength)
            )
            patterns.append(pattern)
        
        # Detect volatility patterns
        volatility = returns.rolling(20).std()
        if len(volatility) > 1:
            vol_change = volatility.iloc[-1] / volatility.iloc[-2] - 1
            
            if abs(vol_change) > 0.5:
                pattern = Pattern(
                    pattern_id=f"volatility_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    pattern_type="volatility",
                    description=f"Volatility {'spike' if vol_change > 0 else 'drop'} detected",
                    strength=abs(vol_change)
                )
                patterns.append(pattern)
        
        return patterns


class InsightsEngine:
    """AI insights generation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pattern_detector = PatternDetector()
        
    def generate_performance_insights(self, 
                                    portfolio_data: pd.DataFrame) -> List[Insight]:
        """Generate performance insights"""
        insights = []
        
        if 'returns' not in portfolio_data.columns or len(portfolio_data) < 10:
            return insights
        
        returns = portfolio_data['returns']
        
        # Analyze recent performance
        recent_return = returns.tail(5).mean()
        overall_return = returns.mean()
        
        if recent_return < overall_return * 0.5:
            insight = Insight(
                insight_id=f"perf_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                insight_type=InsightType.PERFORMANCE,
                severity=InsightSeverity.WARNING,
                title="Recent Performance Decline",
                description="Portfolio performance has declined significantly in recent periods",
                confidence=0.8,
                supporting_data={
                    'recent_return': recent_return,
                    'overall_return': overall_return,
                    'decline_ratio': recent_return / overall_return
                }
            )
            insights.append(insight)
        
        # Analyze volatility
        volatility = returns.std()
        if volatility > 0.05:  # 5% daily volatility threshold
            insight = Insight(
                insight_id=f"vol_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                insight_type=InsightType.RISK,
                severity=InsightSeverity.WARNING,
                title="High Volatility Detected",
                description="Portfolio volatility is above normal levels",
                confidence=0.9,
                supporting_data={'volatility': volatility}
            )
            insights.append(insight)
        
        return insights
    
    def generate_risk_insights(self, 
                             portfolio_data: pd.DataFrame) -> List[Insight]:
        """Generate risk insights"""
        insights = []
        
        if 'returns' not in portfolio_data.columns:
            return insights
        
        returns = portfolio_data['returns']
        
        # Calculate drawdown
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        if max_drawdown < -0.1:  # 10% drawdown threshold
            insight = Insight(
                insight_id=f"dd_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                insight_type=InsightType.RISK,
                severity=InsightSeverity.CRITICAL,
                title="Significant Drawdown Alert",
                description="Portfolio has experienced a significant drawdown",
                confidence=1.0,
                supporting_data={'max_drawdown': max_drawdown}
            )
            insights.append(insight)
        
        return insights


class RecommendationEngine:
    """AI recommendation generation engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def generate_optimization_recommendations(self, 
                                           insights: List[Insight]) -> List[Recommendation]:
        """Generate optimization recommendations based on insights"""
        recommendations = []
        
        for insight in insights:
            if insight.insight_type == InsightType.PERFORMANCE:
                if "decline" in insight.title.lower():
                    recommendation = Recommendation(
                        recommendation_id=f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        title="Performance Optimization",
                        description="Consider adjusting position sizes or strategy parameters",
                        action_items=[
                            "Review recent trades for performance attribution",
                            "Consider reducing position sizes temporarily",
                            "Evaluate strategy parameters for optimization"
                        ],
                        expected_impact="Potential improvement in risk-adjusted returns",
                        confidence=0.7
                    )
                    recommendations.append(recommendation)
            
            elif insight.insight_type == InsightType.RISK:
                if "volatility" in insight.title.lower():
                    recommendation = Recommendation(
                        recommendation_id=f"risk_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        title="Risk Management",
                        description="Implement volatility-based position sizing",
                        action_items=[
                            "Reduce position sizes during high volatility periods",
                            "Implement dynamic stop-loss levels",
                            "Consider hedging strategies"
                        ],
                        expected_impact="Reduced portfolio volatility and drawdown risk",
                        confidence=0.8
                    )
                    recommendations.append(recommendation)
        
        return recommendations
    
    def generate_strategy_recommendations(self, 
                                        performance_data: pd.DataFrame) -> List[Recommendation]:
        """Generate strategy-specific recommendations"""
        recommendations = []
        
        # Example strategy recommendation
        recommendation = Recommendation(
            recommendation_id=f"strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="Strategy Diversification",
            description="Consider adding complementary strategies to improve risk-adjusted returns",
            action_items=[
                "Analyze correlation with existing strategies",
                "Backtest potential new strategies",
                "Implement gradual allocation to new strategies"
            ],
            expected_impact="Improved diversification and reduced correlation risk",
            confidence=0.6
        )
        recommendations.append(recommendation)
        
        return recommendations 