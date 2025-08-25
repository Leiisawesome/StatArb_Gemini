"""
Data Validation and Monitoring System
====================================

Comprehensive data validation and monitoring to prevent timestamp conversion issues
and ensure data quality across all market data operations.

Author: Pro Quant Infrastructure Team
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

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

class DataValidationMonitor:
    """
    Comprehensive data validation and monitoring system
    
    Features:
    - Timestamp format detection and validation
    - Data quality checks (missing values, outliers, etc.)
    - Real-time monitoring and alerting
    - Historical validation tracking
    - Performance impact monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_history = []
        self.alert_thresholds = {
            'missing_data_pct': 5.0,  # Alert if >5% missing data
            'price_outlier_factor': 10.0,  # Alert if price moves >10x
            'timestamp_gap_minutes': 60,  # Alert if >60min gaps
            'volume_zero_pct': 20.0  # Alert if >20% zero volume
        }
    
    def validate_market_data(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """
        Comprehensive market data validation
        
        Args:
            data: Market data DataFrame
            symbol: Symbol being validated
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            # 1. Basic structure validation
            results.extend(self._validate_data_structure(data, symbol))
            
            # 2. Timestamp validation
            results.extend(self._validate_timestamps(data, symbol))
            
            # 3. Price data validation
            results.extend(self._validate_price_data(data, symbol))
            
            # 4. Volume validation
            results.extend(self._validate_volume_data(data, symbol))
            
            # 5. Data completeness validation
            results.extend(self._validate_data_completeness(data, symbol))
            
            # 6. Outlier detection
            results.extend(self._detect_outliers(data, symbol))
            
            # Store validation history
            self.validation_history.append({
                'timestamp': datetime.now(),
                'symbol': symbol,
                'results': results,
                'data_points': len(data)
            })
            
            # Log summary
            error_count = sum(1 for r in results if r.severity == ValidationSeverity.ERROR)
            warning_count = sum(1 for r in results if r.severity == ValidationSeverity.WARNING)
            
            if error_count > 0:
                self.logger.error(f"❌ {symbol}: {error_count} validation errors, {warning_count} warnings")
            elif warning_count > 0:
                self.logger.warning(f"⚠️  {symbol}: {warning_count} validation warnings")
            else:
                self.logger.info(f"✅ {symbol}: All validations passed")
                
        except Exception as e:
            results.append(ValidationResult(
                check_name="validation_system_error",
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Validation system error: {str(e)}"
            ))
            
        return results
    
    def validate_timestamp_format(self, timestamps: List[Any]) -> TimestampValidationResult:
        """
        Detect and validate timestamp format
        
        Args:
            timestamps: List of timestamp values
            
        Returns:
            Timestamp validation result
        """
        if not timestamps:
            return TimestampValidationResult(
                is_valid=False,
                format_detected="empty",
                conversion_factor=None,
                sample_timestamps=[],
                date_range=None,
                issues=["No timestamps provided"]
            )
        
        sample_timestamps = timestamps[:5]  # Sample first 5
        issues = []
        
        # Detect format based on magnitude
        first_ts = timestamps[0]
        
        if isinstance(first_ts, (int, float)):
            # Numeric timestamp - detect scale
            if first_ts > 1e18:  # Nanoseconds (19+ digits)
                format_detected = "nanoseconds"
                conversion_factor = 1_000_000_000
            elif first_ts > 1e15:  # Microseconds (16+ digits)
                format_detected = "microseconds"
                conversion_factor = 1_000_000
            elif first_ts > 1e12:  # Milliseconds (13+ digits)
                format_detected = "milliseconds"
                conversion_factor = 1_000
            elif first_ts > 1e9:   # Seconds (10+ digits)
                format_detected = "seconds"
                conversion_factor = 1
            else:
                format_detected = "unknown_numeric"
                conversion_factor = None
                issues.append(f"Unusual timestamp magnitude: {first_ts}")
        else:
            # Non-numeric timestamp
            format_detected = "string_or_datetime"
            conversion_factor = None
        
        # Try to convert to datetime for validation
        date_range = None
        try:
            if conversion_factor:
                # Convert numeric timestamps
                dt_samples = [datetime.fromtimestamp(ts / conversion_factor) for ts in sample_timestamps]
                all_dts = [datetime.fromtimestamp(ts / conversion_factor) for ts in timestamps]
                date_range = (min(all_dts), max(all_dts))
                
                # Check if dates are reasonable (not in far future/past)
                now = datetime.now()
                for dt in dt_samples:
                    if dt.year < 2000 or dt.year > now.year + 1:
                        issues.append(f"Suspicious date: {dt}")
                        
            elif isinstance(first_ts, str):
                # Try parsing string timestamps
                dt_samples = [pd.to_datetime(ts) for ts in sample_timestamps]
                all_dts = [pd.to_datetime(ts) for ts in timestamps]
                date_range = (min(all_dts), max(all_dts))
                
        except Exception as e:
            issues.append(f"Failed to convert timestamps: {str(e)}")
        
        is_valid = len(issues) == 0 and date_range is not None
        
        return TimestampValidationResult(
            is_valid=is_valid,
            format_detected=format_detected,
            conversion_factor=conversion_factor,
            sample_timestamps=sample_timestamps,
            date_range=date_range,
            issues=issues
        )
    
    def _validate_data_structure(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate basic data structure"""
        results = []
        
        # Check if data is empty
        if data.empty:
            results.append(ValidationResult(
                check_name="data_empty",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"{symbol}: Data is empty"
            ))
            return results
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            results.append(ValidationResult(
                check_name="missing_columns",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"{symbol}: Missing columns: {missing_columns}",
                details={'missing_columns': missing_columns}
            ))
        else:
            results.append(ValidationResult(
                check_name="required_columns",
                severity=ValidationSeverity.INFO,
                passed=True,
                message=f"{symbol}: All required columns present"
            ))
        
        return results
    
    def _validate_timestamps(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate timestamp data"""
        results = []
        
        # Check index type
        if hasattr(data.index, 'dtype'):
            if pd.api.types.is_datetime64_any_dtype(data.index):
                results.append(ValidationResult(
                    check_name="timestamp_index_type",
                    severity=ValidationSeverity.INFO,
                    passed=True,
                    message=f"{symbol}: Index is datetime type"
                ))
            else:
                results.append(ValidationResult(
                    check_name="timestamp_index_type",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"{symbol}: Index is not datetime type: {data.index.dtype}"
                ))
        
        # Check for timestamp gaps
        if len(data) > 1 and pd.api.types.is_datetime64_any_dtype(data.index):
            time_diffs = data.index.to_series().diff().dropna()
            max_gap = time_diffs.max()
            
            if max_gap > timedelta(minutes=self.alert_thresholds['timestamp_gap_minutes']):
                results.append(ValidationResult(
                    check_name="timestamp_gaps",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"{symbol}: Large timestamp gap detected: {max_gap}",
                    details={'max_gap': str(max_gap)}
                ))
        
        return results
    
    def _validate_price_data(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate price data"""
        results = []
        
        price_columns = ['open', 'high', 'low', 'close']
        available_price_cols = [col for col in price_columns if col in data.columns]
        
        if not available_price_cols:
            return results
        
        # Check for negative prices
        for col in available_price_cols:
            negative_count = (data[col] <= 0).sum()
            if negative_count > 0:
                results.append(ValidationResult(
                    check_name=f"negative_prices_{col}",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"{symbol}: {negative_count} negative/zero {col} prices",
                    details={'negative_count': negative_count}
                ))
        
        # Check OHLC logic (High >= Low, etc.)
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            invalid_ohlc = (
                (data['high'] < data['low']) |
                (data['high'] < data['open']) |
                (data['high'] < data['close']) |
                (data['low'] > data['open']) |
                (data['low'] > data['close'])
            ).sum()
            
            if invalid_ohlc > 0:
                results.append(ValidationResult(
                    check_name="ohlc_logic",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"{symbol}: {invalid_ohlc} rows with invalid OHLC logic",
                    details={'invalid_count': invalid_ohlc}
                ))
        
        return results
    
    def _validate_volume_data(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate volume data"""
        results = []
        
        if 'volume' not in data.columns:
            return results
        
        # Check for negative volume
        negative_volume = (data['volume'] < 0).sum()
        if negative_volume > 0:
            results.append(ValidationResult(
                check_name="negative_volume",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"{symbol}: {negative_volume} negative volume entries"
            ))
        
        # Check for excessive zero volume
        zero_volume_pct = (data['volume'] == 0).mean() * 100
        if zero_volume_pct > self.alert_thresholds['volume_zero_pct']:
            results.append(ValidationResult(
                check_name="zero_volume",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"{symbol}: {zero_volume_pct:.1f}% zero volume (threshold: {self.alert_thresholds['volume_zero_pct']}%)"
            ))
        
        return results
    
    def _validate_data_completeness(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate data completeness"""
        results = []
        
        # Check for missing values
        missing_pct = data.isnull().mean() * 100
        for col, pct in missing_pct.items():
            if pct > self.alert_thresholds['missing_data_pct']:
                results.append(ValidationResult(
                    check_name=f"missing_data_{col}",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"{symbol}: {pct:.1f}% missing data in {col} (threshold: {self.alert_thresholds['missing_data_pct']}%)"
                ))
        
        return results
    
    def _detect_outliers(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Detect price and volume outliers"""
        results = []
        
        price_columns = ['open', 'high', 'low', 'close']
        available_price_cols = [col for col in price_columns if col in data.columns]
        
        for col in available_price_cols:
            if len(data) > 10:  # Need sufficient data for outlier detection
                # Use IQR method for outlier detection
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = ((data[col] < lower_bound) | (data[col] > upper_bound)).sum()
                outlier_pct = (outliers / len(data)) * 100
                
                if outlier_pct > 5.0:  # Alert if >5% outliers
                    results.append(ValidationResult(
                        check_name=f"outliers_{col}",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"{symbol}: {outliers} outliers in {col} ({outlier_pct:.1f}%)",
                        details={
                            'outlier_count': outliers,
                            'outlier_percentage': outlier_pct,
                            'bounds': (lower_bound, upper_bound)
                        }
                    ))
        
        return results
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of recent validations"""
        if not self.validation_history:
            return {'status': 'no_validations'}
        
        recent_validations = self.validation_history[-10:]  # Last 10 validations
        
        total_errors = sum(
            sum(1 for r in v['results'] if r.severity == ValidationSeverity.ERROR)
            for v in recent_validations
        )
        
        total_warnings = sum(
            sum(1 for r in v['results'] if r.severity == ValidationSeverity.WARNING)
            for v in recent_validations
        )
        
        symbols_validated = list(set(v['symbol'] for v in recent_validations))
        
        return {
            'status': 'healthy' if total_errors == 0 else 'issues_detected',
            'recent_validations': len(recent_validations),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'symbols_validated': symbols_validated,
            'last_validation': recent_validations[-1]['timestamp'].isoformat()
        }
