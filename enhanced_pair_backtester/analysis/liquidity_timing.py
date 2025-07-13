import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class MarketSession(Enum):
    PRE_MARKET = "pre_market"
    OPENING = "opening"
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    CLOSING = "closing"
    AFTER_HOURS = "after_hours"

@dataclass
class LiquidityMetrics:
    """Container for liquidity metrics at a specific time"""
    timestamp: datetime
    bid_ask_spread: float
    volume: float
    volatility: float
    market_impact: float
    liquidity_score: float
    session: MarketSession
    day_of_week: int

@dataclass
class OptimalExecutionWindow:
    """Container for optimal execution timing recommendations"""
    start_time: time
    end_time: time
    expected_spread: float
    expected_volume: float
    expected_impact: float
    confidence_score: float
    session: MarketSession

class LiquidityTimingAnalyzer:
    """
    Advanced liquidity timing analysis for optimal pair execution
    
    Analyzes intraday and weekly patterns to identify:
    - Optimal execution windows
    - High/low liquidity periods
    - Market impact patterns
    - Volatility timing effects
    """
    
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
        
        # Market session definitions (ET)
        self.session_times = {
            MarketSession.PRE_MARKET: (time(4, 0), time(9, 30)),
            MarketSession.OPENING: (time(9, 30), time(10, 30)),
            MarketSession.MORNING: (time(10, 30), time(12, 0)),
            MarketSession.MIDDAY: (time(12, 0), time(14, 0)),
            MarketSession.AFTERNOON: (time(14, 0), time(15, 30)),
            MarketSession.CLOSING: (time(15, 30), time(16, 0)),
            MarketSession.AFTER_HOURS: (time(16, 0), time(20, 0))
        }
        
        # Liquidity patterns cache
        self.liquidity_patterns = {}
        self.volume_patterns = {}
        self.spread_patterns = {}
        self.volatility_patterns = {}
        
    def classify_market_session(self, timestamp: datetime) -> MarketSession:
        """Classify timestamp into market session"""
        time_only = timestamp.time()
        
        for session, (start, end) in self.session_times.items():
            if start <= time_only < end:
                return session
        
        return MarketSession.AFTER_HOURS
    
    def calculate_liquidity_metrics(self, 
                                   price_data: pd.DataFrame,
                                   volume_data: pd.DataFrame,
                                   spread_data: Optional[pd.DataFrame] = None) -> List[LiquidityMetrics]:
        """Calculate comprehensive liquidity metrics"""
        metrics = []
        
        # Ensure data is sorted by timestamp
        price_data = price_data.sort_index()
        volume_data = volume_data.sort_index()
        
        # Calculate rolling volatility
        returns = price_data.pct_change().dropna()
        volatility = returns.rolling(window=20).std() * np.sqrt(252)
        
        # Estimate spread if not provided
        if spread_data is None:
            spread_data = pd.DataFrame({'spread': self._estimate_spread(price_data)})
        
        for timestamp in price_data.index:
            if timestamp not in volume_data.index:
                continue
                
            # Calculate market impact (simplified model)
            volume = volume_data.loc[timestamp].iloc[0] if hasattr(volume_data.loc[timestamp], 'iloc') else volume_data.loc[timestamp]
            spread = spread_data.loc[timestamp].iloc[0] if hasattr(spread_data.loc[timestamp], 'iloc') else spread_data.loc[timestamp]
            vol = volatility.loc[timestamp].iloc[0] if hasattr(volatility.loc[timestamp], 'iloc') else volatility.loc[timestamp]
            
            # Skip if any metric is NaN
            if pd.isna(volume) or pd.isna(spread) or pd.isna(vol):
                continue
            
            # Market impact estimation (Kyle's lambda)
            market_impact = spread * 0.5 + vol * 0.1 / np.sqrt(max(volume, 1))
            
            # Composite liquidity score (lower is better)
            liquidity_score = (spread * 0.4 + market_impact * 0.4 + vol * 0.2)
            
            metrics.append(LiquidityMetrics(
                timestamp=timestamp,
                bid_ask_spread=spread,
                volume=volume,
                volatility=vol,
                market_impact=market_impact,
                liquidity_score=liquidity_score,
                session=self.classify_market_session(timestamp),
                day_of_week=timestamp.weekday()
            ))
        
        return metrics
    
    def _estimate_spread(self, price_data: pd.DataFrame) -> pd.Series:
        """Estimate bid-ask spread from price data"""
        # Simple spread estimation using high-low range
        if 'high' in price_data.columns and 'low' in price_data.columns:
            spread = (price_data['high'] - price_data['low']) / price_data['close']
        else:
            # Use price volatility as proxy
            returns = price_data.pct_change().abs()
            spread = returns.rolling(window=5).mean() * 2
        
        return pd.Series(spread).fillna(0.001)  # Minimum spread of 10 bps
    
    def analyze_intraday_patterns(self, metrics: List[LiquidityMetrics]) -> Dict:
        """Analyze intraday liquidity patterns"""
        if not metrics:
            return {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([
            {
                'hour': m.timestamp.hour,
                'minute': m.timestamp.minute,
                'time_bucket': f"{m.timestamp.hour:02d}:{(m.timestamp.minute//15)*15:02d}",
                'spread': m.bid_ask_spread,
                'volume': m.volume,
                'volatility': m.volatility,
                'market_impact': m.market_impact,
                'liquidity_score': m.liquidity_score,
                'session': m.session.value
            }
            for m in metrics
        ])
        
        # Group by time buckets (15-minute intervals)
        time_patterns = df.groupby('time_bucket').agg({
            'spread': ['mean', 'std', 'count'],
            'volume': ['mean', 'std'],
            'volatility': ['mean', 'std'],
            'market_impact': ['mean', 'std'],
            'liquidity_score': ['mean', 'std']
        }).round(6)
        
        # Session-based analysis
        session_patterns = df.groupby('session').agg({
            'spread': ['mean', 'std', 'min', 'max'],
            'volume': ['mean', 'std', 'min', 'max'],
            'volatility': ['mean', 'std'],
            'market_impact': ['mean', 'std'],
            'liquidity_score': ['mean', 'std']
        }).round(6)
        
        return {
            'time_patterns': time_patterns,
            'session_patterns': session_patterns,
            'best_liquidity_times': self._find_optimal_times(time_patterns),
            'worst_liquidity_times': self._find_worst_times(time_patterns)
        }
    
    def analyze_weekly_patterns(self, metrics: List[LiquidityMetrics]) -> Dict:
        """Analyze day-of-week liquidity patterns"""
        if not metrics:
            return {}
        
        df = pd.DataFrame([
            {
                'day_of_week': m.day_of_week,
                'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'][m.day_of_week],
                'spread': m.bid_ask_spread,
                'volume': m.volume,
                'volatility': m.volatility,
                'market_impact': m.market_impact,
                'liquidity_score': m.liquidity_score
            }
            for m in metrics if m.day_of_week < 5  # Only weekdays
        ])
        
        if df.empty:
            return {}
        
        weekly_patterns = df.groupby(['day_of_week', 'day_name']).agg({
            'spread': ['mean', 'std', 'count'],
            'volume': ['mean', 'std'],
            'volatility': ['mean', 'std'],
            'market_impact': ['mean', 'std'],
            'liquidity_score': ['mean', 'std']
        }).round(6)
        
        return {
            'weekly_patterns': weekly_patterns,
            'best_days': self._find_best_days(weekly_patterns),
            'worst_days': self._find_worst_days(weekly_patterns)
        }
    
    def _find_optimal_times(self, time_patterns: pd.DataFrame) -> List[str]:
        """Find times with best liquidity (lowest scores)"""
        if time_patterns.empty:
            return []
        
        try:
            liquidity_scores = time_patterns[('liquidity_score', 'mean')]
            return [str(x) for x in liquidity_scores.nsmallest(5).index.tolist()]
        except (KeyError, IndexError):
            return []
    
    def _find_worst_times(self, time_patterns: pd.DataFrame) -> List[str]:
        """Find times with worst liquidity (highest scores)"""
        if time_patterns.empty:
            return []
        
        try:
            liquidity_scores = time_patterns[('liquidity_score', 'mean')]
            return [str(x) for x in liquidity_scores.nlargest(3).index.tolist()]
        except (KeyError, IndexError):
            return []
    
    def _find_best_days(self, weekly_patterns: pd.DataFrame) -> List[str]:
        """Find days with best liquidity"""
        if weekly_patterns.empty:
            return []
        
        try:
            liquidity_scores = weekly_patterns[('liquidity_score', 'mean')]
            best_indices = liquidity_scores.nsmallest(3).index
            return [str(idx[1]) if isinstance(idx, tuple) else str(idx) for idx in best_indices]
        except (KeyError, IndexError):
            return []
    
    def _find_worst_days(self, weekly_patterns: pd.DataFrame) -> List[str]:
        """Find days with worst liquidity"""
        if weekly_patterns.empty:
            return []
        
        try:
            liquidity_scores = weekly_patterns[('liquidity_score', 'mean')]
            worst_indices = liquidity_scores.nlargest(2).index
            return [str(idx[1]) if isinstance(idx, tuple) else str(idx) for idx in worst_indices]
        except (KeyError, IndexError):
            return []
    
    def generate_execution_recommendations(self, 
                                         metrics: List[LiquidityMetrics],
                                         trade_size: float = 100000) -> List[OptimalExecutionWindow]:
        """Generate optimal execution timing recommendations"""
        if not metrics:
            return []
        
        intraday_analysis = self.analyze_intraday_patterns(metrics)
        
        if not intraday_analysis or 'time_patterns' not in intraday_analysis:
            return []
        
        time_patterns = intraday_analysis['time_patterns']
        recommendations = []
        
        # Find top 3 optimal execution windows
        liquidity_scores = time_patterns[('liquidity_score', 'mean')]
        best_times = liquidity_scores.nsmallest(3)
        
        for time_bucket, score in best_times.items():
            try:
                # Parse time bucket
                hour, minute = map(int, time_bucket.split(':'))
                start_time = time(hour, minute)
                end_time = time(hour, minute + 15) if minute < 45 else time(hour + 1, 0)
                
                # Get metrics for this time window
                spread = time_patterns.loc[time_bucket, ('spread', 'mean')]
                volume = time_patterns.loc[time_bucket, ('volume', 'mean')]
                impact = time_patterns.loc[time_bucket, ('market_impact', 'mean')]
                
                # Calculate confidence based on sample size
                sample_size = time_patterns.loc[time_bucket, ('spread', 'count')]
                confidence = min(1.0, sample_size / 100)  # Max confidence at 100+ samples
                
                # Classify session
                session = self.classify_market_session(datetime.combine(datetime.today(), start_time))
                
                recommendations.append(OptimalExecutionWindow(
                    start_time=start_time,
                    end_time=end_time,
                    expected_spread=spread,
                    expected_volume=volume,
                    expected_impact=impact,
                    confidence_score=confidence,
                    session=session
                ))
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Error processing time bucket {time_bucket}: {e}")
                continue
        
        return recommendations
    
    def calculate_execution_cost(self, 
                               timestamp: datetime,
                               trade_size: float,
                               metrics: List[LiquidityMetrics]) -> float:
        """Calculate expected execution cost for a trade at specific time"""
        # Find closest metric
        closest_metric = min(metrics, 
                           key=lambda m: abs((m.timestamp - timestamp).total_seconds()))
        
        # Cost components
        spread_cost = closest_metric.bid_ask_spread * 0.5  # Half spread
        market_impact_cost = closest_metric.market_impact * np.sqrt(trade_size / 100000)
        timing_cost = self._calculate_timing_cost(timestamp, closest_metric)
        
        total_cost = spread_cost + market_impact_cost + timing_cost
        return total_cost
    
    def _calculate_timing_cost(self, timestamp: datetime, metric: LiquidityMetrics) -> float:
        """Calculate additional cost based on timing (session and day effects)"""
        base_cost = 0.0
        
        # Session-based adjustments
        session_adjustments = {
            MarketSession.OPENING: 0.0005,  # 5 bps penalty for opening volatility
            MarketSession.CLOSING: 0.0003,  # 3 bps penalty for closing volatility
            MarketSession.PRE_MARKET: 0.001,  # 10 bps penalty for low liquidity
            MarketSession.AFTER_HOURS: 0.001,  # 10 bps penalty for low liquidity
            MarketSession.MORNING: 0.0,
            MarketSession.MIDDAY: 0.0,
            MarketSession.AFTERNOON: 0.0
        }
        
        # Day-of-week adjustments
        day_adjustments = {
            0: 0.0002,  # Monday - slight penalty
            1: 0.0,     # Tuesday - neutral
            2: 0.0,     # Wednesday - neutral
            3: 0.0,     # Thursday - neutral
            4: 0.0001   # Friday - slight penalty
        }
        
        base_cost += session_adjustments.get(metric.session, 0.0)
        base_cost += day_adjustments.get(metric.day_of_week, 0.0)
        
        return base_cost
    
    def optimize_execution_schedule(self, 
                                  total_quantity: float,
                                  target_duration_hours: float,
                                  metrics: List[LiquidityMetrics]) -> List[Tuple[datetime, float]]:
        """Optimize execution schedule across multiple time periods"""
        if not metrics or target_duration_hours <= 0:
            return []
        
        # Get execution recommendations
        recommendations = self.generate_execution_recommendations(metrics)
        
        if not recommendations:
            return []
        
        # Calculate optimal slice sizes based on liquidity
        schedule = []
        remaining_quantity = total_quantity
        
        # Sort recommendations by liquidity score (best first)
        recommendations.sort(key=lambda x: x.expected_impact)
        
        # Distribute quantity across optimal windows
        for i, window in enumerate(recommendations):
            if remaining_quantity <= 0:
                break
            
            # Calculate slice size based on expected volume and impact
            volume_factor = min(1.0, window.expected_volume / 100000)  # Max 100k base
            impact_factor = max(0.1, 1.0 - window.expected_impact * 10)  # Reduce for high impact
            
            slice_size = min(
                remaining_quantity * 0.4,  # Max 40% in one window
                total_quantity * volume_factor * impact_factor
            )
            
            if slice_size > 0:
                # Create execution timestamp
                execution_time = datetime.combine(
                    datetime.today(),
                    window.start_time
                )
                
                schedule.append((execution_time, slice_size))
                remaining_quantity -= slice_size
        
        # Handle any remaining quantity
        if remaining_quantity > 0 and schedule:
            # Add to the best window
            best_window = schedule[0]
            schedule[0] = (best_window[0], best_window[1] + remaining_quantity)
        
        return schedule
    
    def generate_liquidity_report(self, 
                                metrics: List[LiquidityMetrics],
                                symbol_pair: str = "PAIR") -> str:
        """Generate comprehensive liquidity analysis report"""
        if not metrics:
            return f"No liquidity data available for {symbol_pair}"
        
        intraday = self.analyze_intraday_patterns(metrics)
        weekly = self.analyze_weekly_patterns(metrics)
        recommendations = self.generate_execution_recommendations(metrics)
        
        report = f"""
=== LIQUIDITY TIMING ANALYSIS REPORT ===
Symbol Pair: {symbol_pair}
Analysis Period: {len(metrics)} observations
Date Range: {metrics[0].timestamp.date()} to {metrics[-1].timestamp.date()}

=== INTRADAY PATTERNS ===
"""
        
        if intraday.get('best_liquidity_times'):
            report += f"Best Execution Times: {', '.join(intraday['best_liquidity_times'])}\n"
        
        if intraday.get('worst_liquidity_times'):
            report += f"Worst Execution Times: {', '.join(intraday['worst_liquidity_times'])}\n"
        
        report += "\n=== WEEKLY PATTERNS ===\n"
        
        if weekly.get('best_days'):
            report += f"Best Trading Days: {', '.join(weekly['best_days'])}\n"
        
        if weekly.get('worst_days'):
            report += f"Worst Trading Days: {', '.join(weekly['worst_days'])}\n"
        
        report += "\n=== EXECUTION RECOMMENDATIONS ===\n"
        
        for i, rec in enumerate(recommendations, 1):
            report += f"""
Window {i}:
  Time: {rec.start_time.strftime('%H:%M')} - {rec.end_time.strftime('%H:%M')}
  Session: {rec.session.value.replace('_', ' ').title()}
  Expected Spread: {rec.expected_spread:.4f} ({rec.expected_spread*10000:.1f} bps)
  Expected Impact: {rec.expected_impact:.4f} ({rec.expected_impact*10000:.1f} bps)
  Confidence: {rec.confidence_score:.2f}
"""
        
        # Summary statistics
        avg_spread = np.mean([m.bid_ask_spread for m in metrics])
        avg_impact = np.mean([m.market_impact for m in metrics])
        avg_liquidity = np.mean([m.liquidity_score for m in metrics])
        
        report += f"""
=== SUMMARY STATISTICS ===
Average Bid-Ask Spread: {avg_spread:.4f} ({avg_spread*10000:.1f} bps)
Average Market Impact: {avg_impact:.4f} ({avg_impact*10000:.1f} bps)
Average Liquidity Score: {avg_liquidity:.4f}

=== EXECUTION COST ESTIMATES ===
Small Trade (10K): {avg_spread*0.5 + avg_impact*0.32:.4f} ({(avg_spread*0.5 + avg_impact*0.32)*10000:.1f} bps)
Medium Trade (100K): {avg_spread*0.5 + avg_impact*1.0:.4f} ({(avg_spread*0.5 + avg_impact*1.0)*10000:.1f} bps)
Large Trade (1M): {avg_spread*0.5 + avg_impact*3.16:.4f} ({(avg_spread*0.5 + avg_impact*3.16)*10000:.1f} bps)
"""
        
        return report

# Example usage and testing
if __name__ == "__main__":
    # Create sample data for testing
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='15min')
    dates = dates[(dates.time >= time(9, 30)) & (dates.time <= time(16, 0))]
    
    # Sample price data
    np.random.seed(42)
    price_data = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 0.01),
        'high': 100 + np.cumsum(np.random.randn(len(dates)) * 0.01) + 0.1,
        'low': 100 + np.cumsum(np.random.randn(len(dates)) * 0.01) - 0.1
    }, index=dates)
    
    # Sample volume data
    volume_data = pd.DataFrame({
        'volume': np.random.lognormal(10, 1, len(dates))
    }, index=dates)
    
    # Initialize analyzer
    analyzer = LiquidityTimingAnalyzer()
    
    # Calculate metrics
    metrics = analyzer.calculate_liquidity_metrics(price_data, volume_data)
    
    # Generate report
    report = analyzer.generate_liquidity_report(metrics, "TEST_PAIR")
    print(report) 