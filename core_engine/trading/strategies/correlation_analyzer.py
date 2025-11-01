"""
Strategy Correlation Analyzer - Diversification Monitoring
Monitors cross-strategy correlation to ensure portfolio diversification.

Correlation Analysis:
- Daily correlation matrix between all strategies
- Rolling correlation (30-day window)
- Correlation clustering detection
- Diversification score calculation

Rebalancing Recommendations:
- Detect highly correlated strategies (>0.7)
- Suggest weight adjustments
- Alert on diversification breakdown
- Optimize strategy allocation

Correlation Categories:
- Independent (<0.3): Good diversification
- Moderate (0.3-0.7): Acceptable
- High (0.7-0.9): Reduce exposure
- Extreme (>0.9): Critical - immediate action

Integration:
- Called by StrategyManager daily
- Informs allocation decisions
- Risk management input

Author: Trading System Team
Date: October 25, 2025
Version: 1.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class CorrelationLevel(Enum):
    """Correlation level categories"""
    INDEPENDENT = "independent"       # <0.3
    MODERATE = "moderate"             # 0.3-0.7
    HIGH = "high"                     # 0.7-0.9
    EXTREME = "extreme"               # >0.9


@dataclass
class StrategyPairCorrelation:
    """
    Correlation between two strategies
    
    Attributes:
        strategy_a: First strategy ID
        strategy_b: Second strategy ID
        correlation: Correlation coefficient (-1 to 1)
        level: Correlation level
        data_points: Number of data points used
        timestamp: Calculation timestamp
    """
    strategy_a: str
    strategy_b: str
    correlation: float  # -1 to 1
    level: CorrelationLevel
    data_points: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DiversificationReport:
    """
    Portfolio diversification report
    
    Attributes:
        timestamp: Report timestamp
        diversification_score: Overall score 0-100
        strategy_count: Number of strategies
        high_correlations: List of highly correlated pairs
        recommendations: Rebalancing recommendations
        correlation_matrix: Full correlation matrix
    """
    timestamp: datetime
    diversification_score: float  # 0-100
    strategy_count: int
    high_correlations: List[StrategyPairCorrelation] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    correlation_matrix: Optional[np.ndarray] = None


class StrategyCorrelationAnalyzer:
    """
    Strategy Correlation Analyzer
    
    Monitors cross-strategy correlation to ensure diversification.
    Provides rebalancing recommendations when correlations become too high.
    
    Integration: Used by StrategyManager for allocation decisions
    """
    
    def __init__(self, strategy_manager, config: Optional[Dict] = None):
        """
        Initialize correlation analyzer
        
        Args:
            strategy_manager: StrategyManager instance
            config: Configuration dictionary
        """
        self.strategy_manager = strategy_manager
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Correlation Thresholds
        self.independent_threshold = 0.3
        self.moderate_threshold = 0.7
        self.high_threshold = 0.9
        
        # Rolling Window
        self.correlation_window_days = self.config.get('correlation_window_days', 30)
        self.min_data_points = self.config.get('min_data_points', 20)
        
        # Strategy Returns History
        # Format: {strategy_id: deque([(timestamp, return), ...])}
        self.returns_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Correlation History
        self.correlation_history: deque = deque(maxlen=1000)
        
        # State
        self.last_analysis_time: Optional[datetime] = None
        self.analysis_frequency_hours = self.config.get('analysis_frequency_hours', 24)  # Daily
        
        # Statistics
        self.total_analyses = 0
        self.high_correlation_alerts = 0
        
        self.logger.info("✅ StrategyCorrelationAnalyzer initialized")
        self.logger.info(f"   Correlation Window: {self.correlation_window_days} days")
        self.logger.info(f"   Analysis Frequency: {self.analysis_frequency_hours} hours")
        self.logger.info(f"   High Correlation Alert: >{self.moderate_threshold:.1%}")
    
    def record_strategy_return(
        self,
        strategy_id: str,
        return_value: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Record strategy return for correlation analysis
        
        Args:
            strategy_id: Strategy identifier
            return_value: Strategy return (e.g., daily return)
            timestamp: Return timestamp
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.returns_history[strategy_id].append((timestamp, return_value))
        
        self.logger.debug(f"📝 Recorded return for {strategy_id}: {return_value:.4f}")
    
    async def analyze_strategy_correlations(self) -> DiversificationReport:
        """
        Analyze correlations between all strategies
        
        Returns:
            DiversificationReport with correlation analysis
        """
        self.total_analyses += 1
        self.last_analysis_time = datetime.now()
        
        self.logger.info(f"🔍 Analyzing strategy correlations (analysis #{self.total_analyses})...")
        
        # Get active strategies
        strategies = list(self.returns_history.keys())
        strategy_count = len(strategies)
        
        if strategy_count < 2:
            self.logger.warning("Not enough strategies for correlation analysis (<2)")
            return DiversificationReport(
                timestamp=datetime.now(),
                diversification_score=100,  # Perfect diversification with <2 strategies
                strategy_count=strategy_count,
                recommendations=["Need at least 2 strategies for correlation analysis"]
            )
        
        # Get returns for correlation window
        cutoff_time = datetime.now() - timedelta(days=self.correlation_window_days)
        
        returns_data = {}
        for strategy_id in strategies:
            # Filter to window
            windowed_returns = [
                ret for ts, ret in self.returns_history[strategy_id]
                if ts >= cutoff_time
            ]
            
            if len(windowed_returns) >= self.min_data_points:
                returns_data[strategy_id] = np.array(windowed_returns)
        
        # Need at least 2 strategies with sufficient data
        if len(returns_data) < 2:
            self.logger.warning("Not enough data for correlation analysis")
            return DiversificationReport(
                timestamp=datetime.now(),
                diversification_score=50,
                strategy_count=strategy_count,
                recommendations=["Insufficient data for correlation analysis"]
            )
        
        # Calculate correlation matrix
        strategies_with_data = list(returns_data.keys())
        n_strategies = len(strategies_with_data)
        
        correlation_matrix = np.zeros((n_strategies, n_strategies))
        
        for i, strategy_a in enumerate(strategies_with_data):
            for j, strategy_b in enumerate(strategies_with_data):
                if i == j:
                    correlation_matrix[i, j] = 1.0
                elif i < j:
                    # Calculate correlation
                    returns_a = returns_data[strategy_a]
                    returns_b = returns_data[strategy_b]
                    
                    # Align returns (use common timestamps)
                    min_len = min(len(returns_a), len(returns_b))
                    returns_a = returns_a[-min_len:]
                    returns_b = returns_b[-min_len:]
                    
                    if min_len >= self.min_data_points:
                        corr = np.corrcoef(returns_a, returns_b)[0, 1]
                        correlation_matrix[i, j] = corr
                        correlation_matrix[j, i] = corr
        
        # Analyze pair correlations
        high_correlations = []
        
        for i, strategy_a in enumerate(strategies_with_data):
            for j, strategy_b in enumerate(strategies_with_data):
                if i < j:  # Only upper triangle
                    corr = correlation_matrix[i, j]
                    level = self._determine_correlation_level(corr)
                    
                    if level in [CorrelationLevel.HIGH, CorrelationLevel.EXTREME]:
                        pair_corr = StrategyPairCorrelation(
                            strategy_a=strategy_a,
                            strategy_b=strategy_b,
                            correlation=corr,
                            level=level,
                            data_points=len(returns_data[strategy_a])
                        )
                        high_correlations.append(pair_corr)
        
        # Calculate diversification score
        diversification_score = self._calculate_diversification_score(correlation_matrix)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(high_correlations, strategies_with_data)
        
        # Alert on high correlations
        if high_correlations:
            self.high_correlation_alerts += 1
            self.logger.warning(
                f"⚠️ HIGH CORRELATION ALERT: {len(high_correlations)} highly correlated strategy pairs detected"
            )
        
        # Create report
        report = DiversificationReport(
            timestamp=datetime.now(),
            diversification_score=diversification_score,
            strategy_count=n_strategies,
            high_correlations=high_correlations,
            recommendations=recommendations,
            correlation_matrix=correlation_matrix
        )
        
        # Store in history
        self.correlation_history.append(report)
        
        # Log summary
        self._log_correlation_summary(report, strategies_with_data)
        
        return report
    
    def _determine_correlation_level(self, correlation: float) -> CorrelationLevel:
        """Determine correlation level category"""
        abs_corr = abs(correlation)
        
        if abs_corr < self.independent_threshold:
            return CorrelationLevel.INDEPENDENT
        elif abs_corr < self.moderate_threshold:
            return CorrelationLevel.MODERATE
        elif abs_corr < self.high_threshold:
            return CorrelationLevel.HIGH
        else:
            return CorrelationLevel.EXTREME
    
    def _calculate_diversification_score(self, correlation_matrix: np.ndarray) -> float:
        """
        Calculate diversification score 0-100
        
        Higher score = better diversification
        Based on average absolute correlation
        """
        n = correlation_matrix.shape[0]
        
        if n < 2:
            return 100
        
        # Get upper triangle (excluding diagonal)
        upper_tri_indices = np.triu_indices(n, k=1)
        correlations = correlation_matrix[upper_tri_indices]
        
        # Average absolute correlation
        avg_abs_corr = np.mean(np.abs(correlations))
        
        # Convert to score (lower correlation = higher score)
        # Perfect diversification (corr=0) = 100
        # Perfect correlation (corr=1) = 0
        score = (1 - avg_abs_corr) * 100
        
        return max(0, min(100, score))
    
    def _generate_recommendations(
        self,
        high_correlations: List[StrategyPairCorrelation],
        strategies: List[str]
    ) -> List[str]:
        """Generate rebalancing recommendations"""
        recommendations = []
        
        if not high_correlations:
            recommendations.append("✅ Good diversification - no action needed")
            return recommendations
        
        # Analyze which strategies are involved in multiple high correlations
        strategy_corr_counts = defaultdict(int)
        for pair in high_correlations:
            strategy_corr_counts[pair.strategy_a] += 1
            strategy_corr_counts[pair.strategy_b] += 1
        
        # Sort by correlation count
        sorted_strategies = sorted(
            strategy_corr_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Generate recommendations
        if sorted_strategies:
            top_strategy, count = sorted_strategies[0]
            if count >= 3:
                recommendations.append(
                    f"🔴 CRITICAL: {top_strategy} is highly correlated with {count} other strategies - "
                    f"consider reducing allocation"
                )
            else:
                recommendations.append(
                    f"⚠️ WARNING: {top_strategy} is highly correlated with {count} other strategies"
                )
        
        # Specific pair recommendations
        for pair in high_correlations[:3]:  # Top 3
            if pair.level == CorrelationLevel.EXTREME:
                recommendations.append(
                    f"🔴 EXTREME correlation ({pair.correlation:.2f}) between "
                    f"{pair.strategy_a} and {pair.strategy_b} - consider disabling one"
                )
            else:
                recommendations.append(
                    f"⚠️ HIGH correlation ({pair.correlation:.2f}) between "
                    f"{pair.strategy_a} and {pair.strategy_b} - reduce allocations"
                )
        
        # General recommendation
        if len(high_correlations) > 5:
            recommendations.append(
                f"⚠️ Portfolio has {len(high_correlations)} highly correlated pairs - "
                f"consider strategy rebalancing"
            )
        
        return recommendations
    
    def _log_correlation_summary(self, report: DiversificationReport, strategies: List[str]):
        """Log correlation analysis summary"""
        score_icon = "🟢" if report.diversification_score >= 70 else "🟡" if report.diversification_score >= 50 else "🔴"
        
        self.logger.info(
            f"{score_icon} Diversification Score: {report.diversification_score:.1f}/100 "
            f"({report.strategy_count} strategies)"
        )
        
        if report.high_correlations:
            self.logger.warning(
                f"   High Correlations: {len(report.high_correlations)} pairs"
            )
            for pair in report.high_correlations[:3]:
                self.logger.warning(
                    f"     {pair.strategy_a} ↔ {pair.strategy_b}: "
                    f"{pair.correlation:+.3f} ({pair.level.value})"
                )
        
        if report.recommendations:
            self.logger.info(f"   Recommendations: {len(report.recommendations)}")
            for rec in report.recommendations[:3]:
                self.logger.info(f"     - {rec}")
    
    # Monitoring and Alerting
    
    async def check_correlation_alerts(self) -> bool:
        """
        Check if correlation analysis is needed
        
        Returns:
            True if analysis should be performed
        """
        if self.last_analysis_time is None:
            return True
        
        time_since_analysis = datetime.now() - self.last_analysis_time
        hours_since = time_since_analysis.total_seconds() / 3600
        
        return hours_since >= self.analysis_frequency_hours
    
    # Statistics and Reporting
    
    def get_correlation_statistics(self) -> Dict:
        """Get correlation analysis statistics"""
        latest_report = self.correlation_history[-1] if self.correlation_history else None
        
        stats = {
            'total_analyses': self.total_analyses,
            'high_correlation_alerts': self.high_correlation_alerts,
            'strategies_tracked': len(self.returns_history)
        }
        
        if latest_report:
            stats.update({
                'current_diversification_score': latest_report.diversification_score,
                'current_strategy_count': latest_report.strategy_count,
                'current_high_correlations': len(latest_report.high_correlations),
                'last_analysis': latest_report.timestamp.isoformat()
            })
        
        return stats
    
    def generate_correlation_report(self) -> str:
        """Generate correlation analysis report"""
        stats = self.get_correlation_statistics()
        latest_report = self.correlation_history[-1] if self.correlation_history else None
        
        report = [
            "=" * 60,
            "STRATEGY CORRELATION REPORT",
            "=" * 60,
            f"Total Analyses:        {stats['total_analyses']:,}",
            f"High Correlation Alerts: {stats['high_correlation_alerts']:,}",
            f"Strategies Tracked:    {stats['strategies_tracked']}",
            ""
        ]
        
        if latest_report:
            score_icon = "🟢" if latest_report.diversification_score >= 70 else "🟡" if latest_report.diversification_score >= 50 else "🔴"
            
            report.extend([
                f"CURRENT DIVERSIFICATION: {score_icon}",
                f"  Score:               {latest_report.diversification_score:.1f}/100",
                f"  Strategies:          {latest_report.strategy_count}",
                f"  High Correlations:   {len(latest_report.high_correlations)}",
                ""
            ])
            
            if latest_report.high_correlations:
                report.append("HIGH CORRELATION PAIRS:")
                for pair in latest_report.high_correlations[:10]:
                    level_icon = "🔴" if pair.level == CorrelationLevel.EXTREME else "🟠"
                    report.append(
                        f"  {level_icon} {pair.strategy_a:20s} ↔ {pair.strategy_b:20s}: "
                        f"{pair.correlation:+.3f}"
                    )
                report.append("")
            
            if latest_report.recommendations:
                report.append("RECOMMENDATIONS:")
                for rec in latest_report.recommendations:
                    report.append(f"  {rec}")
                report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)

