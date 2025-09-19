"""
Performance Engine - Drawdown Tracker
Advanced drawdown analysis and underwater equity tracking
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict, deque
import threading

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class DrawdownType(Enum):
    """Types of drawdown analysis"""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    UNDERWATER = "underwater"
    ROLLING = "rolling"
    CONDITIONAL = "conditional"


class DrawdownPeriod(Enum):
    """Drawdown measurement periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class RecoveryPhase(Enum):
    """Recovery phase classification"""
    IN_DRAWDOWN = "in_drawdown"
    RECOVERING = "recovering"
    NEW_HIGH = "new_high"
    FULLY_RECOVERED = "fully_recovered"


@dataclass
class DrawdownEvent:
    """Individual drawdown event"""
    
    # Event identification
    event_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    recovery_date: Optional[datetime] = None
    
    # Drawdown metrics
    peak_value: float = 0.0
    trough_value: float = 0.0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    
    # Duration metrics
    drawdown_duration: int = 0  # Days in drawdown
    recovery_duration: int = 0  # Days to recover
    total_duration: int = 0  # Total days from start to recovery
    
    # Performance during drawdown
    drawdown_returns: List[float] = field(default_factory=list)
    recovery_returns: List[float] = field(default_factory=list)
    
    # Classification
    phase: RecoveryPhase = RecoveryPhase.IN_DRAWDOWN
    severity_rank: int = 0  # Rank among all drawdowns (1 = worst)
    
    # Context
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    portfolio_exposure: float = 0.0
    
    # Metadata
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UnderwaterMetrics:
    """Underwater equity metrics"""
    
    # Current underwater status
    is_underwater: bool = False
    current_underwater_days: int = 0
    current_underwater_depth: float = 0.0
    
    # Historical underwater metrics
    total_underwater_days: int = 0
    max_underwater_period: int = 0
    avg_underwater_depth: float = 0.0
    max_underwater_depth: float = 0.0
    
    # Recovery metrics
    avg_recovery_time: float = 0.0
    median_recovery_time: float = 0.0
    fastest_recovery: int = 0
    slowest_recovery: int = 0
    
    # Time series data
    underwater_periods: List[Tuple[datetime, datetime, float]] = field(default_factory=list)
    
    # Performance metrics
    underwater_percentage: float = 0.0  # % of time underwater
    recovery_efficiency: float = 0.0  # Average return during recovery periods


@dataclass
class DrawdownConfig:
    """Drawdown tracker configuration"""
    
    # Analysis settings
    drawdown_type: DrawdownType = DrawdownType.ABSOLUTE
    measurement_period: DrawdownPeriod = DrawdownPeriod.DAILY
    
    # Detection thresholds
    min_drawdown_threshold: float = 0.01  # 1% minimum drawdown to track
    significance_threshold: float = 0.05  # 5% significant drawdown
    severe_threshold: float = 0.20  # 20% severe drawdown
    
    # Analysis parameters
    rolling_window: int = 252  # Days for rolling analysis
    confidence_levels: List[float] = field(default_factory=lambda: [0.95, 0.99])
    
    # Recovery settings
    recovery_threshold: float = 0.0  # Recovery when back to break-even
    new_high_threshold: float = 0.001  # 0.1% above previous high
    
    # Performance calculation
    business_days_per_year: int = 252
    
    # Advanced settings
    enable_conditional_analysis: bool = True
    enable_stress_testing: bool = True
    enable_scenario_analysis: bool = True


class DrawdownAnalyzer:
    """Analyze individual drawdown events"""
    
    def __init__(self, config: DrawdownConfig):
        self.config = config
        
        logger.info("Drawdown analyzer initialized")
    
    def identify_drawdown_events(self, returns: Union[pd.Series, np.ndarray],
                                dates: Optional[pd.DatetimeIndex] = None) -> List[DrawdownEvent]:
        """Identify all drawdown events in return series"""
        
        try:
            if isinstance(returns, pd.Series):
                returns_array = returns.values
                dates_array = returns.index
            else:
                returns_array = returns
                dates_array = dates or pd.date_range(start='2020-01-01', periods=len(returns_array))
            
            if len(returns_array) == 0:
                return []
            
            # Calculate cumulative wealth
            cumulative_returns = np.cumprod(1 + returns_array)
            
            # Calculate running maximum (peaks)
            running_max = np.maximum.accumulate(cumulative_returns)
            
            # Calculate drawdown series
            drawdown_series = (cumulative_returns - running_max) / running_max
            
            # Identify drawdown events
            events = []
            current_event = None
            event_counter = 0
            
            for i, (date, drawdown, cum_ret, peak) in enumerate(zip(
                dates_array, drawdown_series, cumulative_returns, running_max
            )):
                
                if drawdown < -self.config.min_drawdown_threshold:
                    # In drawdown
                    if current_event is None:
                        # Start new drawdown event
                        event_counter += 1
                        current_event = DrawdownEvent(
                            event_id=f"DD_{event_counter:03d}",
                            start_date=date,
                            peak_value=peak,
                            trough_value=cum_ret,
                            max_drawdown=drawdown,
                            current_drawdown=drawdown,
                            phase=RecoveryPhase.IN_DRAWDOWN
                        )
                        current_event.drawdown_returns.append(returns_array[i])
                    else:
                        # Continue existing drawdown
                        current_event.trough_value = min(current_event.trough_value, cum_ret)
                        current_event.max_drawdown = min(current_event.max_drawdown, drawdown)
                        current_event.current_drawdown = drawdown
                        current_event.drawdown_returns.append(returns_array[i])
                        current_event.drawdown_duration += 1
                
                else:
                    # Not in drawdown or recovering
                    if current_event is not None:
                        if drawdown >= -self.config.recovery_threshold:
                            # Fully recovered
                            current_event.end_date = date
                            current_event.recovery_date = date
                            current_event.phase = RecoveryPhase.FULLY_RECOVERED
                            current_event.total_duration = (date - current_event.start_date).days
                            events.append(current_event)
                            current_event = None
                        else:
                            # Still recovering
                            current_event.phase = RecoveryPhase.RECOVERING
                            current_event.recovery_returns.append(returns_array[i])
                            current_event.recovery_duration += 1
            
            # Handle ongoing drawdown
            if current_event is not None:
                current_event.end_date = dates_array[-1]
                events.append(current_event)
            
            # Rank events by severity
            events.sort(key=lambda x: x.max_drawdown)
            for rank, event in enumerate(events, 1):
                event.severity_rank = rank
            
            logger.debug(f"Identified {len(events)} drawdown events")
            
            return events
            
        except Exception as e:
            logger.error(f"Error identifying drawdown events: {e}")
            return []
    
    def calculate_drawdown_statistics(self, events: List[DrawdownEvent]) -> Dict[str, Any]:
        """Calculate comprehensive drawdown statistics"""
        
        try:
            if not events:
                return {}
            
            # Basic statistics
            max_drawdowns = [abs(event.max_drawdown) for event in events]
            durations = [event.drawdown_duration for event in events if event.drawdown_duration > 0]
            recovery_durations = [event.recovery_duration for event in events if event.recovery_duration > 0]
            total_durations = [event.total_duration for event in events if event.total_duration > 0]
            
            stats = {
                'total_events': len(events),
                'avg_max_drawdown': np.mean(max_drawdowns) if max_drawdowns else 0.0,
                'median_max_drawdown': np.median(max_drawdowns) if max_drawdowns else 0.0,
                'worst_drawdown': max(max_drawdowns) if max_drawdowns else 0.0,
                'best_drawdown': min(max_drawdowns) if max_drawdowns else 0.0,
                
                'avg_drawdown_duration': np.mean(durations) if durations else 0.0,
                'median_drawdown_duration': np.median(durations) if durations else 0.0,
                'max_drawdown_duration': max(durations) if durations else 0,
                'min_drawdown_duration': min(durations) if durations else 0,
                
                'avg_recovery_duration': np.mean(recovery_durations) if recovery_durations else 0.0,
                'median_recovery_duration': np.median(recovery_durations) if recovery_durations else 0.0,
                'max_recovery_duration': max(recovery_durations) if recovery_durations else 0,
                'min_recovery_duration': min(recovery_durations) if recovery_durations else 0,
                
                'avg_total_duration': np.mean(total_durations) if total_durations else 0.0,
                'median_total_duration': np.median(total_durations) if total_durations else 0.0
            }
            
            # Severity classification
            significant_events = [e for e in events if abs(e.max_drawdown) >= self.config.significance_threshold]
            severe_events = [e for e in events if abs(e.max_drawdown) >= self.config.severe_threshold]
            
            stats.update({
                'significant_drawdowns': len(significant_events),
                'severe_drawdowns': len(severe_events),
                'significant_percentage': len(significant_events) / len(events) * 100,
                'severe_percentage': len(severe_events) / len(events) * 100
            })
            
            # Recovery efficiency
            recovered_events = [e for e in events if e.phase == RecoveryPhase.FULLY_RECOVERED]
            if recovered_events:
                recovery_efficiencies = []
                for event in recovered_events:
                    if event.recovery_returns and event.drawdown_returns:
                        drawdown_loss = abs(sum(event.drawdown_returns))
                        recovery_gain = sum(event.recovery_returns)
                        if drawdown_loss > 0:
                            efficiency = recovery_gain / drawdown_loss
                            recovery_efficiencies.append(efficiency)
                
                if recovery_efficiencies:
                    stats['avg_recovery_efficiency'] = np.mean(recovery_efficiencies)
                    stats['median_recovery_efficiency'] = np.median(recovery_efficiencies)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating drawdown statistics: {e}")
            return {}
    
    def analyze_conditional_drawdowns(self, events: List[DrawdownEvent],
                                    market_data: Optional[Dict[str, pd.Series]] = None) -> Dict[str, Any]:
        """Analyze drawdowns conditional on market conditions"""
        
        try:
            if not events:
                return {}
            
            analysis = {
                'by_severity': {},
                'by_duration': {},
                'by_market_conditions': {}
            }
            
            # Analyze by severity
            severity_buckets = {
                'minor': [e for e in events if abs(e.max_drawdown) < 0.05],
                'moderate': [e for e in events if 0.05 <= abs(e.max_drawdown) < 0.15],
                'severe': [e for e in events if 0.15 <= abs(e.max_drawdown) < 0.30],
                'extreme': [e for e in events if abs(e.max_drawdown) >= 0.30]
            }
            
            for severity, bucket_events in severity_buckets.items():
                if bucket_events:
                    durations = [e.drawdown_duration for e in bucket_events]
                    analysis['by_severity'][severity] = {
                        'count': len(bucket_events),
                        'avg_duration': np.mean(durations),
                        'avg_recovery': np.mean([e.recovery_duration for e in bucket_events if e.recovery_duration > 0])
                    }
            
            # Analyze by duration
            duration_buckets = {
                'short': [e for e in events if e.drawdown_duration <= 30],
                'medium': [e for e in events if 30 < e.drawdown_duration <= 90],
                'long': [e for e in events if 90 < e.drawdown_duration <= 180],
                'extended': [e for e in events if e.drawdown_duration > 180]
            }
            
            for duration_type, bucket_events in duration_buckets.items():
                if bucket_events:
                    drawdowns = [abs(e.max_drawdown) for e in bucket_events]
                    analysis['by_duration'][duration_type] = {
                        'count': len(bucket_events),
                        'avg_drawdown': np.mean(drawdowns),
                        'max_drawdown': max(drawdowns)
                    }
            
            # Analyze by market conditions (if provided)
            if market_data:
                for condition_name, condition_data in market_data.items():
                    condition_analysis = self._analyze_drawdowns_vs_condition(events, condition_data)
                    analysis['by_market_conditions'][condition_name] = condition_analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in conditional drawdown analysis: {e}")
            return {}
    
    def _analyze_drawdowns_vs_condition(self, events: List[DrawdownEvent],
                                      condition_data: pd.Series) -> Dict[str, Any]:
        """Analyze drawdowns against specific market condition"""
        
        try:
            # Categorize market conditions
            condition_values = []
            for event in events:
                if event.start_date in condition_data.index:
                    condition_values.append(condition_data.loc[event.start_date])
            
            if not condition_values:
                return {}
            
            # Split into high/low conditions
            median_condition = np.median(condition_values)
            
            high_condition_events = []
            low_condition_events = []
            
            for event, condition_val in zip(events, condition_values):
                if condition_val >= median_condition:
                    high_condition_events.append(event)
                else:
                    low_condition_events.append(event)
            
            analysis = {}
            
            # Analyze high condition events
            if high_condition_events:
                high_drawdowns = [abs(e.max_drawdown) for e in high_condition_events]
                high_durations = [e.drawdown_duration for e in high_condition_events]
                
                analysis['high_condition'] = {
                    'count': len(high_condition_events),
                    'avg_drawdown': np.mean(high_drawdowns),
                    'avg_duration': np.mean(high_durations),
                    'max_drawdown': max(high_drawdowns)
                }
            
            # Analyze low condition events
            if low_condition_events:
                low_drawdowns = [abs(e.max_drawdown) for e in low_condition_events]
                low_durations = [e.drawdown_duration for e in low_condition_events]
                
                analysis['low_condition'] = {
                    'count': len(low_condition_events),
                    'avg_drawdown': np.mean(low_drawdowns),
                    'avg_duration': np.mean(low_durations),
                    'max_drawdown': max(low_drawdowns)
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing drawdowns vs condition: {e}")
            return {}


class UnderwaterAnalyzer:
    """Analyze underwater equity periods"""
    
    def __init__(self, config: DrawdownConfig):
        self.config = config
        
        logger.info("Underwater analyzer initialized")
    
    def calculate_underwater_metrics(self, returns: Union[pd.Series, np.ndarray],
                                   dates: Optional[pd.DatetimeIndex] = None) -> UnderwaterMetrics:
        """Calculate comprehensive underwater equity metrics"""
        
        try:
            if isinstance(returns, pd.Series):
                returns_array = returns.values
                dates_array = returns.index
            else:
                returns_array = returns
                dates_array = dates or pd.date_range(start='2020-01-01', periods=len(returns_array))
            
            if len(returns_array) == 0:
                return UnderwaterMetrics()
            
            # Calculate cumulative returns and running maximum
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            
            # Calculate drawdown (underwater depth)
            drawdown_series = (cumulative_returns - running_max) / running_max
            
            # Identify underwater periods
            underwater_mask = drawdown_series < 0
            underwater_periods = self._identify_underwater_periods(underwater_mask, dates_array, drawdown_series)
            
            # Calculate metrics
            metrics = UnderwaterMetrics()
            
            # Current status
            metrics.is_underwater = underwater_mask[-1] if len(underwater_mask) > 0 else False
            
            if metrics.is_underwater:
                # Find current underwater period
                current_period_start = len(underwater_mask) - 1
                while current_period_start > 0 and underwater_mask[current_period_start - 1]:
                    current_period_start -= 1
                
                metrics.current_underwater_days = len(underwater_mask) - current_period_start
                metrics.current_underwater_depth = abs(drawdown_series[-1])
            
            # Historical metrics
            if underwater_periods:
                metrics.underwater_periods = underwater_periods
                
                underwater_days = [period[1] - period[0] for period in underwater_periods]
                underwater_depths = [abs(period[2]) for period in underwater_periods]
                
                metrics.total_underwater_days = sum([p[1] - p[0] for p in underwater_periods])
                metrics.max_underwater_period = max([p[1] - p[0] for p in underwater_periods])
                metrics.avg_underwater_depth = np.mean(underwater_depths)
                metrics.max_underwater_depth = max(underwater_depths)
                
                # Recovery time analysis
                recovery_times = []
                for i, (start_idx, end_idx, depth) in enumerate(underwater_periods):
                    if end_idx < len(dates_array) - 1:  # Not the last period
                        recovery_times.append(end_idx - start_idx)
                
                if recovery_times:
                    metrics.avg_recovery_time = np.mean(recovery_times)
                    metrics.median_recovery_time = np.median(recovery_times)
                    metrics.fastest_recovery = min(recovery_times)
                    metrics.slowest_recovery = max(recovery_times)
                
                # Time underwater percentage
                total_periods = len(dates_array)
                metrics.underwater_percentage = (metrics.total_underwater_days / total_periods) * 100
                
                # Recovery efficiency
                recovery_returns = []
                for start_idx, end_idx, depth in underwater_periods:
                    if end_idx < len(returns_array):
                        period_returns = returns_array[start_idx:end_idx+1]
                        recovery_returns.extend(period_returns[period_returns > 0])
                
                if recovery_returns:
                    metrics.recovery_efficiency = np.mean(recovery_returns)
            
            logger.debug(f"Calculated underwater metrics: {metrics.underwater_percentage:.1f}% time underwater, "
                        f"max period: {metrics.max_underwater_period} days")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating underwater metrics: {e}")
            return UnderwaterMetrics()
    
    def _identify_underwater_periods(self, underwater_mask: np.ndarray,
                                   dates: pd.DatetimeIndex,
                                   drawdown_series: np.ndarray) -> List[Tuple[int, int, float]]:
        """Identify continuous underwater periods"""
        
        periods = []
        start_idx = None
        
        for i, is_underwater in enumerate(underwater_mask):
            if is_underwater and start_idx is None:
                # Start of underwater period
                start_idx = i
            elif not is_underwater and start_idx is not None:
                # End of underwater period
                end_idx = i - 1
                max_depth = np.min(drawdown_series[start_idx:i])
                periods.append((start_idx, end_idx, max_depth))
                start_idx = None
        
        # Handle case where series ends while underwater
        if start_idx is not None:
            end_idx = len(underwater_mask) - 1
            max_depth = np.min(drawdown_series[start_idx:])
            periods.append((start_idx, end_idx, max_depth))
        
        return periods
    
    def generate_underwater_curve(self, returns: Union[pd.Series, np.ndarray],
                                dates: Optional[pd.DatetimeIndex] = None) -> pd.Series:
        """Generate underwater equity curve"""
        
        try:
            if isinstance(returns, pd.Series):
                returns_array = returns.values
                dates_array = returns.index
            else:
                returns_array = returns
                dates_array = dates or pd.date_range(start='2020-01-01', periods=len(returns_array))
            
            # Calculate cumulative returns and running maximum
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            
            # Calculate underwater curve (drawdown series)
            underwater_curve = (cumulative_returns - running_max) / running_max
            
            return pd.Series(underwater_curve, index=dates_array)
            
        except Exception as e:
            logger.error(f"Error generating underwater curve: {e}")
            return pd.Series(dtype=float)


class DrawdownTracker:
    """
    Comprehensive Drawdown Tracker
    
    Tracks and analyzes drawdowns, underwater periods,
    and recovery patterns with advanced statistical analysis.
    """
    
    def __init__(self, config: Optional[DrawdownConfig] = None):
        """Initialize drawdown tracker"""
        
        self.config = config or DrawdownConfig()
        
        # Core analyzers
        self._drawdown_analyzer = DrawdownAnalyzer(self.config)
        self._underwater_analyzer = UnderwaterAnalyzer(self.config)
        
        # Data storage
        self._drawdown_events: Dict[str, List[DrawdownEvent]] = defaultdict(list)
        self._underwater_metrics: Dict[str, UnderwaterMetrics] = {}
        self._current_drawdowns: Dict[str, float] = {}
        
        # Real-time tracking
        self._real_time_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._last_peaks: Dict[str, float] = {}
        
        # Performance tracking
        self._analysis_stats = {
            'total_analyses': 0,
            'total_events_tracked': 0,
            'last_analysis_time': None
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        logger.info("Drawdown tracker initialized")
    
    def analyze_drawdowns(self, returns: Union[pd.Series, np.ndarray, List[float]],
                         identifier: str = "default",
                         dates: Optional[pd.DatetimeIndex] = None) -> Tuple[List[DrawdownEvent], UnderwaterMetrics]:
        """Perform comprehensive drawdown analysis"""
        
        try:
            with self._lock:
                self._analysis_stats['total_analyses'] += 1
                
                # Convert input to appropriate format
                if isinstance(returns, list):
                    returns = np.array(returns)
                
                # Identify drawdown events
                events = self._drawdown_analyzer.identify_drawdown_events(returns, dates)
                
                # Calculate underwater metrics
                underwater_metrics = self._underwater_analyzer.calculate_underwater_metrics(returns, dates)
                
                # Store results
                self._drawdown_events[identifier] = events
                self._underwater_metrics[identifier] = underwater_metrics
                
                # Update current drawdown
                if len(events) > 0 and events[-1].phase == RecoveryPhase.IN_DRAWDOWN:
                    self._current_drawdowns[identifier] = abs(events[-1].current_drawdown)
                else:
                    self._current_drawdowns[identifier] = 0.0
                
                self._analysis_stats['total_events_tracked'] += len(events)
                self._analysis_stats['last_analysis_time'] = datetime.now()
                
                logger.info(f"Analyzed drawdowns for {identifier}: {len(events)} events, "
                           f"{underwater_metrics.underwater_percentage:.1f}% time underwater")
                
                return events, underwater_metrics
                
        except Exception as e:
            logger.error(f"Error analyzing drawdowns: {e}")
            return [], UnderwaterMetrics()
    
    def update_real_time_drawdown(self, new_return: float, 
                                identifier: str = "real_time") -> float:
        """Update real-time drawdown tracking"""
        
        try:
            with self._lock:
                # Add new return to real-time data
                self._real_time_data[identifier].append(new_return)
                
                # Calculate current cumulative value
                recent_returns = list(self._real_time_data[identifier])
                current_value = np.prod(1 + np.array(recent_returns))
                
                # Update peak
                if identifier not in self._last_peaks:
                    self._last_peaks[identifier] = current_value
                else:
                    self._last_peaks[identifier] = max(self._last_peaks[identifier], current_value)
                
                # Calculate current drawdown
                current_drawdown = (current_value - self._last_peaks[identifier]) / self._last_peaks[identifier]
                self._current_drawdowns[identifier] = abs(current_drawdown)
                
                return self._current_drawdowns[identifier]
                
        except Exception as e:
            logger.error(f"Error updating real-time drawdown: {e}")
            return 0.0
    
    def get_drawdown_events(self, identifier: str) -> List[DrawdownEvent]:
        """Get drawdown events for specific identifier"""
        
        with self._lock:
            return self._drawdown_events.get(identifier, [])
    
    def get_underwater_metrics(self, identifier: str) -> Optional[UnderwaterMetrics]:
        """Get underwater metrics for specific identifier"""
        
        with self._lock:
            return self._underwater_metrics.get(identifier)
    
    def get_current_drawdown(self, identifier: str) -> float:
        """Get current drawdown for specific identifier"""
        
        with self._lock:
            return self._current_drawdowns.get(identifier, 0.0)
    
    def calculate_drawdown_statistics(self, identifier: str) -> Dict[str, Any]:
        """Calculate comprehensive drawdown statistics"""
        
        try:
            events = self.get_drawdown_events(identifier)
            
            if not events:
                return {}
            
            # Basic statistics from analyzer
            stats = self._drawdown_analyzer.calculate_drawdown_statistics(events)
            
            # Add additional statistics
            underwater_metrics = self.get_underwater_metrics(identifier)
            if underwater_metrics:
                stats.update({
                    'underwater_percentage': underwater_metrics.underwater_percentage,
                    'max_underwater_period': underwater_metrics.max_underwater_period,
                    'current_underwater_days': underwater_metrics.current_underwater_days,
                    'recovery_efficiency': underwater_metrics.recovery_efficiency
                })
            
            # Current status
            stats.update({
                'current_drawdown': self.get_current_drawdown(identifier),
                'total_events_analyzed': len(events),
                'events_in_progress': len([e for e in events if e.phase == RecoveryPhase.IN_DRAWDOWN])
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating drawdown statistics: {e}")
            return {}
    
    def analyze_conditional_drawdowns(self, identifier: str,
                                    market_data: Optional[Dict[str, pd.Series]] = None) -> Dict[str, Any]:
        """Perform conditional drawdown analysis"""
        
        try:
            events = self.get_drawdown_events(identifier)
            
            if not events:
                return {}
            
            return self._drawdown_analyzer.analyze_conditional_drawdowns(events, market_data)
            
        except Exception as e:
            logger.error(f"Error in conditional drawdown analysis: {e}")
            return {}
    
    def generate_underwater_curve(self, returns: Union[pd.Series, np.ndarray],
                                dates: Optional[pd.DatetimeIndex] = None) -> pd.Series:
        """Generate underwater equity curve"""
        
        return self._underwater_analyzer.generate_underwater_curve(returns, dates)
    
    def get_worst_drawdowns(self, identifier: str, top_n: int = 10) -> List[DrawdownEvent]:
        """Get worst drawdown events"""
        
        try:
            events = self.get_drawdown_events(identifier)
            
            if not events:
                return []
            
            # Sort by maximum drawdown (worst first)
            sorted_events = sorted(events, key=lambda x: x.max_drawdown)
            
            return sorted_events[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting worst drawdowns: {e}")
            return []
    
    def get_longest_drawdowns(self, identifier: str, top_n: int = 10) -> List[DrawdownEvent]:
        """Get longest drawdown events"""
        
        try:
            events = self.get_drawdown_events(identifier)
            
            if not events:
                return []
            
            # Sort by total duration (longest first)
            sorted_events = sorted(events, key=lambda x: x.total_duration, reverse=True)
            
            return sorted_events[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting longest drawdowns: {e}")
            return []
    
    def export_drawdown_analysis(self, identifier: str) -> Dict[str, pd.DataFrame]:
        """Export drawdown analysis to DataFrames"""
        
        try:
            events = self.get_drawdown_events(identifier)
            
            if not events:
                return {}
            
            # Events DataFrame
            events_data = []
            for event in events:
                row = {
                    'event_id': event.event_id,
                    'start_date': event.start_date,
                    'end_date': event.end_date,
                    'recovery_date': event.recovery_date,
                    'max_drawdown': event.max_drawdown,
                    'peak_value': event.peak_value,
                    'trough_value': event.trough_value,
                    'drawdown_duration': event.drawdown_duration,
                    'recovery_duration': event.recovery_duration,
                    'total_duration': event.total_duration,
                    'phase': event.phase.value,
                    'severity_rank': event.severity_rank
                }
                events_data.append(row)
            
            events_df = pd.DataFrame(events_data)
            
            # Summary statistics
            stats = self.calculate_drawdown_statistics(identifier)
            stats_df = pd.DataFrame([stats])
            
            # Underwater metrics
            underwater_metrics = self.get_underwater_metrics(identifier)
            if underwater_metrics:
                underwater_data = {
                    'total_underwater_days': underwater_metrics.total_underwater_days,
                    'max_underwater_period': underwater_metrics.max_underwater_period,
                    'avg_underwater_depth': underwater_metrics.avg_underwater_depth,
                    'max_underwater_depth': underwater_metrics.max_underwater_depth,
                    'underwater_percentage': underwater_metrics.underwater_percentage,
                    'recovery_efficiency': underwater_metrics.recovery_efficiency
                }
                underwater_df = pd.DataFrame([underwater_data])
            else:
                underwater_df = pd.DataFrame()
            
            export_data = {
                'events': events_df,
                'statistics': stats_df,
                'underwater_metrics': underwater_df
            }
            
            logger.info(f"Exported drawdown analysis for {identifier}")
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting drawdown analysis: {e}")
            return {}
    
    def get_tracker_summary(self) -> Dict[str, Any]:
        """Get tracker summary"""
        
        with self._lock:
            summary = {
                'tracked_series': list(self._drawdown_events.keys()),
                'total_series': len(self._drawdown_events),
                'analysis_stats': self._analysis_stats.copy(),
                'config': {
                    'drawdown_type': self.config.drawdown_type.value,
                    'min_threshold': self.config.min_drawdown_threshold,
                    'significance_threshold': self.config.significance_threshold,
                    'severe_threshold': self.config.severe_threshold
                }
            }
            
            # Add summary for each tracked series
            for identifier in self._drawdown_events.keys():
                events = self._drawdown_events[identifier]
                underwater_metrics = self._underwater_metrics.get(identifier)
                
                series_summary = {
                    'total_events': len(events),
                    'current_drawdown': self._current_drawdowns.get(identifier, 0.0),
                    'worst_drawdown': min([e.max_drawdown for e in events]) if events else 0.0,
                    'longest_duration': max([e.total_duration for e in events]) if events else 0,
                    'underwater_percentage': underwater_metrics.underwater_percentage if underwater_metrics else 0.0,
                    'events_in_progress': len([e for e in events if e.phase == RecoveryPhase.IN_DRAWDOWN])
                }
                
                summary[f'series_{identifier}'] = series_summary
            
            return summary
    
    def clear_analysis_data(self, identifier: Optional[str] = None) -> None:
        """Clear analysis data"""
        
        with self._lock:
            if identifier:
                self._drawdown_events.pop(identifier, None)
                self._underwater_metrics.pop(identifier, None)
                self._current_drawdowns.pop(identifier, None)
                self._real_time_data.pop(identifier, None)
                self._last_peaks.pop(identifier, None)
                logger.info(f"Cleared analysis data for {identifier}")
            else:
                self._drawdown_events.clear()
                self._underwater_metrics.clear()
                self._current_drawdowns.clear()
                self._real_time_data.clear()
                self._last_peaks.clear()
                logger.info("Cleared all analysis data")