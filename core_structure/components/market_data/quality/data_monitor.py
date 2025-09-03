"""
Unified Data Quality Monitor - Market Data Quality Management
===========================================================

Consolidated data quality monitoring system combining:
- Real-time data quality monitoring and alerting
- Data validation and timestamp conversion monitoring  
- Quality metrics tracking and reporting
- Unified quality management interface

This module replaces:
- data_quality_monitor.py (813 lines)
- data_validation_monitor.py (438 lines)

Author: StatArb_Gemini Architecture Consolidation
Version: 4.0 (Phase 4B)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Core infrastructure imports
try:
    from core_structure.infrastructure.types.monitoring_types import AlertLevel
    from core_structure.infrastructure.messaging.message_bus import MessageBus
    from core_structure.infrastructure.monitoring.metrics_collector import MetricsCollector
except ImportError:
    # Fallback enum if infrastructure not available
    class AlertLevel(Enum):
        INFO = "info"
        WARNING = "warning"
        ERROR = "error"
        CRITICAL = "critical"
    MessageBus = None
    MetricsCollector = None

class DataQualityLevel(Enum):
    """Data quality level classification"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"

class DataIssueType(Enum):
    """Types of data quality issues"""
    MISSING_DATA = "missing_data"
    STALE_DATA = "stale_data"
    OUTLIER = "outlier"
    DUPLICATE = "duplicate"
    INVALID_FORMAT = "invalid_format"
    TIMESTAMP_ISSUE = "timestamp_issue"
    VOLUME_ANOMALY = "volume_anomaly"
    PRICE_ANOMALY = "price_anomaly"
    CONNECTIVITY = "connectivity"

class MonitoringStatus(Enum):
    """Monitoring status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class QualityAlert:
    """Data quality alert"""
    alert_id: str
    level: AlertLevel
    message: str
    symbol: str
    timestamp: datetime
    issue_type: DataIssueType
    details: Optional[Dict[str, Any]] = None
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None

@dataclass
class ValidationResult:
    """Result of a data validation check"""
    check_name: str
    severity: ValidationSeverity
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None

@dataclass
class TimestampValidationResult:
    """Result of timestamp validation"""
    is_valid: bool
    format_detected: str
    conversion_factor: Optional[int]
    sample_timestamps: List[Any]
    date_range: Optional[Tuple[datetime, datetime]]
    issues: List[str]

@dataclass
class DataQualityMetrics:
    """Data quality metrics container"""
    timestamp: datetime
    symbol: str
    completeness_ratio: float
    timeliness_score: float
    accuracy_score: float
    consistency_score: float
    overall_quality_level: DataQualityLevel
    issue_count: int
    last_update: datetime
    data_points_analyzed: int

@dataclass
class QualityThresholds:
    """Quality threshold configuration"""
    completeness_threshold: float = 0.95
    timeliness_threshold: float = 0.90
    accuracy_threshold: float = 0.98
    consistency_threshold: float = 0.95
    max_staleness_minutes: int = 5
    max_price_change_percent: float = 10.0
    min_volume_threshold: int = 100
    max_gap_minutes: int = 2

@dataclass
class MonitoringConfig:
    """Data quality monitoring configuration"""
    check_interval_seconds: int = 30
    alert_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    enabled_checks: Set[str] = field(default_factory=lambda: {
        'completeness', 'timeliness', 'accuracy', 'consistency', 
        'outliers', 'timestamps', 'connectivity'
    })
    alert_channels: List[str] = field(default_factory=lambda: ['console', 'metrics'])
    buffer_size: int = 1000
    historical_retention_hours: int = 24

class TimestampValidator:
    """Timestamp validation and conversion utilities"""
    
    def __init__(self):
        self.known_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%d'
        ]
        self.timestamp_cache = {}
        
    def validate_timestamps(self, data: pd.DataFrame, 
                          timestamp_col: str = 'timestamp') -> TimestampValidationResult:
        """Validate timestamp column in dataframe"""
        try:
            if timestamp_col not in data.columns:
                return TimestampValidationResult(
                    is_valid=False,
                    format_detected="not_found",
                    conversion_factor=None,
                    sample_timestamps=[],
                    date_range=None,
                    issues=[f"Timestamp column '{timestamp_col}' not found"]
                )
                
            timestamps = data[timestamp_col]
            sample_values = timestamps.head(10).tolist()
            issues = []
            
            # Check for null values
            null_count = timestamps.isnull().sum()
            if null_count > 0:
                issues.append(f"Found {null_count} null timestamps")
                
            # Detect timestamp format
            format_detected = self._detect_timestamp_format(timestamps)
            
            # Check for conversion issues
            conversion_factor = None
            if self._is_numeric_timestamp(timestamps.iloc[0]):
                conversion_factor = self._detect_conversion_factor(timestamps)
                
            # Validate date range
            try:
                if format_detected != "unknown":
                    converted_timestamps = pd.to_datetime(timestamps, errors='coerce')
                    valid_timestamps = converted_timestamps.dropna()
                    
                    if len(valid_timestamps) == 0:
                        issues.append("No valid timestamps after conversion")
                        date_range = None
                    else:
                        date_range = (valid_timestamps.min(), valid_timestamps.max())
                        
                        # Check for reasonable date range
                        if date_range[0].year < 2000 or date_range[1].year > 2030:
                            issues.append(f"Suspicious date range: {date_range}")
                            
                else:
                    date_range = None
                    issues.append("Could not detect timestamp format")
                    
            except Exception as e:
                issues.append(f"Error validating date range: {str(e)}")
                date_range = None
                
            is_valid = len(issues) == 0
            
            return TimestampValidationResult(
                is_valid=is_valid,
                format_detected=format_detected,
                conversion_factor=conversion_factor,
                sample_timestamps=sample_values,
                date_range=date_range,
                issues=issues
            )
            
        except Exception as e:
            return TimestampValidationResult(
                is_valid=False,
                format_detected="error",
                conversion_factor=None,
                sample_timestamps=[],
                date_range=None,
                issues=[f"Validation error: {str(e)}"]
            )
            
    def _detect_timestamp_format(self, timestamps: pd.Series) -> str:
        """Detect timestamp format from sample data"""
        sample = timestamps.dropna().iloc[0] if len(timestamps.dropna()) > 0 else None
        
        if sample is None:
            return "unknown"
            
        # Check if already datetime
        if isinstance(sample, (pd.Timestamp, datetime)):
            return "datetime"
            
        # Check if numeric (unix timestamp)
        if self._is_numeric_timestamp(sample):
            return "unix_timestamp"
            
        # Check string formats
        if isinstance(sample, str):
            for fmt in self.known_formats:
                try:
                    datetime.strptime(sample, fmt)
                    return fmt
                except ValueError:
                    continue
                    
        return "unknown"
        
    def _is_numeric_timestamp(self, value) -> bool:
        """Check if value is a numeric timestamp"""
        try:
            num_value = float(value)
            # Check if it's in a reasonable range for unix timestamps
            return 1e9 < num_value < 2e10  # Roughly 2001-2033
        except (ValueError, TypeError):
            return False
            
    def _detect_conversion_factor(self, timestamps: pd.Series) -> Optional[int]:
        """Detect conversion factor for numeric timestamps"""
        try:
            sample = float(timestamps.iloc[0])
            
            # Check different scales
            if 1e9 < sample < 2e10:  # Seconds
                return 1
            elif 1e12 < sample < 2e13:  # Milliseconds
                return 1000
            elif 1e15 < sample < 2e16:  # Microseconds
                return 1000000
            elif 1e18 < sample < 2e19:  # Nanoseconds
                return 1000000000
                
        except (ValueError, TypeError, IndexError):
            pass
            
        return None

class DataQualityAnalyzer:
    """Core data quality analysis engine"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.timestamp_validator = TimestampValidator()
        
    def analyze_data_quality(self, data: pd.DataFrame, symbol: str) -> DataQualityMetrics:
        """Comprehensive data quality analysis"""
        timestamp = datetime.now()
        
        try:
            # Basic data checks
            completeness_ratio = self._calculate_completeness(data)
            timeliness_score = self._calculate_timeliness(data)
            accuracy_score = self._calculate_accuracy(data)
            consistency_score = self._calculate_consistency(data)
            
            # Count issues
            issues = self._detect_issues(data, symbol)
            issue_count = len(issues)
            
            # Overall quality level
            overall_quality = self._determine_quality_level(
                completeness_ratio, timeliness_score, accuracy_score, consistency_score
            )
            
            return DataQualityMetrics(
                timestamp=timestamp,
                symbol=symbol,
                completeness_ratio=completeness_ratio,
                timeliness_score=timeliness_score,
                accuracy_score=accuracy_score,
                consistency_score=consistency_score,
                overall_quality_level=overall_quality,
                issue_count=issue_count,
                last_update=timestamp,
                data_points_analyzed=len(data)
            )
            
        except Exception as e:
            logger.error(f"Error analyzing data quality for {symbol}: {e}")
            return DataQualityMetrics(
                timestamp=timestamp,
                symbol=symbol,
                completeness_ratio=0.0,
                timeliness_score=0.0,
                accuracy_score=0.0,
                consistency_score=0.0,
                overall_quality_level=DataQualityLevel.UNACCEPTABLE,
                issue_count=1,
                last_update=timestamp,
                data_points_analyzed=0
            )
            
    def _calculate_completeness(self, data: pd.DataFrame) -> float:
        """Calculate data completeness ratio"""
        if data.empty:
            return 0.0
            
        total_cells = data.size
        missing_cells = data.isnull().sum().sum()
        return max(0.0, (total_cells - missing_cells) / total_cells)
        
    def _calculate_timeliness(self, data: pd.DataFrame) -> float:
        """Calculate data timeliness score"""
        if data.empty or 'timestamp' not in data.columns:
            return 0.0
            
        try:
            timestamps = pd.to_datetime(data['timestamp'], errors='coerce')
            latest_time = timestamps.max()
            current_time = datetime.now()
            
            if pd.isna(latest_time):
                return 0.0
                
            # Convert to same timezone if needed
            if latest_time.tz is not None:
                current_time = current_time.replace(tzinfo=latest_time.tz)
            elif current_time.tz is not None:
                latest_time = latest_time.replace(tzinfo=current_time.tz)
                
            staleness_minutes = (current_time - latest_time).total_seconds() / 60
            max_staleness = self.config.alert_thresholds.max_staleness_minutes
            
            return max(0.0, 1.0 - (staleness_minutes / max_staleness))
            
        except Exception:
            return 0.0
            
    def _calculate_accuracy(self, data: pd.DataFrame) -> float:
        """Calculate data accuracy score"""
        if data.empty:
            return 0.0
            
        try:
            score = 1.0
            
            # Check for obvious data errors
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                # Check for infinite values
                inf_count = np.isinf(data[col]).sum()
                if inf_count > 0:
                    score *= (len(data) - inf_count) / len(data)
                    
                # Check for extreme outliers (beyond 5 standard deviations)
                if col in ['open', 'high', 'low', 'close']:
                    values = data[col].dropna()
                    if len(values) > 0:
                        mean_val = values.mean()
                        std_val = values.std()
                        if std_val > 0:
                            outliers = np.abs(values - mean_val) > 5 * std_val
                            outlier_count = outliers.sum()
                            score *= (len(values) - outlier_count) / len(values)
                            
            return max(0.0, score)
            
        except Exception:
            return 0.0
            
    def _calculate_consistency(self, data: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        if data.empty:
            return 0.0
            
        try:
            score = 1.0
            
            # Check OHLC consistency
            if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
                # High should be >= max(open, close)
                invalid_high = (data['high'] < data[['open', 'close']].max(axis=1)).sum()
                # Low should be <= min(open, close)
                invalid_low = (data['low'] > data[['open', 'close']].min(axis=1)).sum()
                
                total_records = len(data)
                if total_records > 0:
                    consistency_ratio = (total_records - invalid_high - invalid_low) / total_records
                    score *= consistency_ratio
                    
            # Check timestamp ordering
            if 'timestamp' in data.columns:
                timestamps = pd.to_datetime(data['timestamp'], errors='coerce')
                valid_timestamps = timestamps.dropna()
                if len(valid_timestamps) > 1:
                    ordered_ratio = (valid_timestamps == valid_timestamps.sort_values()).sum() / len(valid_timestamps)
                    score *= ordered_ratio
                    
            return max(0.0, score)
            
        except Exception:
            return 0.0
            
    def _determine_quality_level(self, completeness: float, timeliness: float, 
                               accuracy: float, consistency: float) -> DataQualityLevel:
        """Determine overall quality level"""
        avg_score = (completeness + timeliness + accuracy + consistency) / 4
        
        if avg_score >= 0.95:
            return DataQualityLevel.EXCELLENT
        elif avg_score >= 0.85:
            return DataQualityLevel.GOOD
        elif avg_score >= 0.70:
            return DataQualityLevel.ACCEPTABLE
        elif avg_score >= 0.50:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.UNACCEPTABLE
            
    def _detect_issues(self, data: pd.DataFrame, symbol: str) -> List[DataIssueType]:
        """Detect specific data quality issues"""
        issues = []
        
        if data.empty:
            issues.append(DataIssueType.MISSING_DATA)
            return issues
            
        # Missing data check
        if data.isnull().sum().sum() > 0:
            issues.append(DataIssueType.MISSING_DATA)
            
        # Stale data check
        if 'timestamp' in data.columns:
            try:
                latest_time = pd.to_datetime(data['timestamp']).max()
                if pd.notna(latest_time):
                    staleness = (datetime.now() - latest_time.to_pydatetime()).total_seconds() / 60
                    if staleness > self.config.alert_thresholds.max_staleness_minutes:
                        issues.append(DataIssueType.STALE_DATA)
            except Exception:
                issues.append(DataIssueType.TIMESTAMP_ISSUE)
                
        # Outlier detection
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            values = data[col].dropna()
            if len(values) > 2:
                q1, q3 = values.quantile([0.25, 0.75])
                iqr = q3 - q1
                outliers = (values < (q1 - 3 * iqr)) | (values > (q3 + 3 * iqr))
                if outliers.any():
                    issues.append(DataIssueType.OUTLIER)
                    break
                    
        # Duplicate check
        if data.duplicated().any():
            issues.append(DataIssueType.DUPLICATE)
            
        return issues

class UnifiedDataQualityMonitor:
    """
    Unified Data Quality Monitor
    
    Consolidates:
    - Real-time data quality monitoring
    - Data validation and timestamp monitoring
    - Quality metrics tracking and alerting
    - Quality management interface
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.analyzer = DataQualityAnalyzer(self.config)
        self.timestamp_validator = TimestampValidator()
        
        # State management
        self.status = MonitoringStatus.STOPPED
        self._monitoring_task = None
        self._alerts = deque(maxlen=self.config.buffer_size)
        self._metrics_history = defaultdict(lambda: deque(maxlen=100))
        self._subscribers = []
        
        # External integrations
        self.message_bus = MessageBus() if MessageBus else None
        self.metrics_collector = MetricsCollector() if MetricsCollector else None
        
        logger.info("UnifiedDataQualityMonitor initialized")
        
    def start_monitoring(self):
        """Start quality monitoring"""
        if self.status == MonitoringStatus.ACTIVE:
            logger.warning("Monitoring already active")
            return
            
        self.status = MonitoringStatus.ACTIVE
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Data quality monitoring started")
        
    async def stop_monitoring(self):
        """Stop quality monitoring"""
        self.status = MonitoringStatus.STOPPED
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Data quality monitoring stopped")
        
    def analyze_data(self, data: pd.DataFrame, symbol: str) -> DataQualityMetrics:
        """Analyze data quality for a dataset"""
        metrics = self.analyzer.analyze_data_quality(data, symbol)
        
        # Store metrics
        self._metrics_history[symbol].append(metrics)
        
        # Check for alerts
        self._check_quality_alerts(metrics)
        
        # Publish metrics if available
        if self.metrics_collector:
            self.metrics_collector.record_metric(
                f"data_quality.{symbol}.completeness",
                metrics.completeness_ratio
            )
            
        return metrics
        
    def validate_timestamps(self, data: pd.DataFrame, 
                          timestamp_col: str = 'timestamp') -> TimestampValidationResult:
        """Validate timestamps in dataset"""
        return self.timestamp_validator.validate_timestamps(data, timestamp_col)
        
    def validate_data(self, data: pd.DataFrame, symbol: str = "unknown") -> List[ValidationResult]:
        """Comprehensive data validation"""
        results = []
        
        # Basic structure validation
        if data.empty:
            results.append(ValidationResult(
                check_name="data_presence",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message="Dataset is empty"
            ))
            return results
            
        # Timestamp validation
        if 'timestamp' in data.columns:
            ts_result = self.validate_timestamps(data)
            results.append(ValidationResult(
                check_name="timestamp_validation",
                severity=ValidationSeverity.ERROR if not ts_result.is_valid else ValidationSeverity.INFO,
                passed=ts_result.is_valid,
                message=f"Timestamp validation: {ts_result.format_detected}",
                details=ts_result.__dict__
            ))
            
        # Required columns check
        required_cols = ['open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            results.append(ValidationResult(
                check_name="required_columns",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"Missing required columns: {missing_cols}"
            ))
            
        # Data quality analysis
        try:
            metrics = self.analyzer.analyze_data_quality(data, symbol)
            results.append(ValidationResult(
                check_name="quality_analysis",
                severity=ValidationSeverity.INFO,
                passed=metrics.overall_quality_level != DataQualityLevel.UNACCEPTABLE,
                message=f"Quality level: {metrics.overall_quality_level.value}",
                details=metrics.__dict__
            ))
        except Exception as e:
            results.append(ValidationResult(
                check_name="quality_analysis",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Quality analysis failed: {str(e)}"
            ))
            
        return results
        
    def add_alert_subscriber(self, callback: Callable[[QualityAlert], None]):
        """Add alert subscriber"""
        self._subscribers.append(callback)
        
    def get_quality_metrics(self, symbol: str) -> List[DataQualityMetrics]:
        """Get quality metrics history for symbol"""
        return list(self._metrics_history[symbol])
        
    def get_recent_alerts(self, limit: int = 100) -> List[QualityAlert]:
        """Get recent quality alerts"""
        return list(self._alerts)[-limit:]
        
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring status and summary"""
        return {
            'status': self.status.value,
            'active_symbols': len(self._metrics_history),
            'total_alerts': len(self._alerts),
            'config': {
                'check_interval': self.config.check_interval_seconds,
                'enabled_checks': list(self.config.enabled_checks)
            }
        }
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.status == MonitoringStatus.ACTIVE:
            try:
                # Periodic quality checks would go here
                # For now, just maintain the loop structure
                await asyncio.sleep(self.config.check_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
                
    def _check_quality_alerts(self, metrics: DataQualityMetrics):
        """Check metrics against thresholds and generate alerts"""
        thresholds = self.config.alert_thresholds
        
        # Completeness alert
        if metrics.completeness_ratio < thresholds.completeness_threshold:
            self._create_alert(
                level=AlertLevel.WARNING,
                message=f"Low data completeness: {metrics.completeness_ratio:.2f}",
                symbol=metrics.symbol,
                issue_type=DataIssueType.MISSING_DATA
            )
            
        # Timeliness alert
        if metrics.timeliness_score < thresholds.timeliness_threshold:
            self._create_alert(
                level=AlertLevel.WARNING,
                message=f"Stale data detected: score {metrics.timeliness_score:.2f}",
                symbol=metrics.symbol,
                issue_type=DataIssueType.STALE_DATA
            )
            
        # Overall quality alert
        if metrics.overall_quality_level == DataQualityLevel.UNACCEPTABLE:
            self._create_alert(
                level=AlertLevel.ERROR,
                message=f"Unacceptable data quality for {metrics.symbol}",
                symbol=metrics.symbol,
                issue_type=DataIssueType.INVALID_FORMAT
            )
            
    def _create_alert(self, level: AlertLevel, message: str, symbol: str, 
                     issue_type: DataIssueType):
        """Create and distribute quality alert"""
        alert = QualityAlert(
            alert_id=f"{symbol}_{int(datetime.now().timestamp())}",
            level=level,
            message=message,
            symbol=symbol,
            timestamp=datetime.now(),
            issue_type=issue_type
        )
        
        # Store alert
        self._alerts.append(alert)
        
        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error notifying alert subscriber: {e}")
                
        # Publish to message bus if available
        if self.message_bus:
            self.message_bus.publish(f"quality_alert.{symbol}", alert.__dict__)
            
        logger.warning(f"Quality alert: {alert.message}")

# Backward compatibility aliases
DataQualityMonitor = UnifiedDataQualityMonitor
DataValidationMonitor = UnifiedDataQualityMonitor

# Export classes
__all__ = [
    'UnifiedDataQualityMonitor',
    'TimestampValidator', 
    'DataQualityAnalyzer',
    'QualityAlert',
    'ValidationResult',
    'TimestampValidationResult',
    'DataQualityMetrics',
    'QualityThresholds',
    'MonitoringConfig',
    'DataQualityLevel',
    'DataIssueType',
    'MonitoringStatus',
    'ValidationSeverity',
    # Backward compatibility
    'DataQualityMonitor',
    'DataValidationMonitor'
]
