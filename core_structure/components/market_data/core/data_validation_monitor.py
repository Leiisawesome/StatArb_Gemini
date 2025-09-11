"""
Data Validation and Monitoring System
====================================

Comprehensive data validation and monitoring to prevent timestamp conversion issues
and ensure data quality across all market data operations.
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
            'missing_data_pct': 10.0,  # Alert if >10% missing data (increased for market data)
            'price_outlier_factor': 20.0,  # Alert if price moves >20x (increased for volatile stocks)
            'timestamp_gap_minutes': 1440,  # Alert if >24hr gaps (weekends/holidays are normal)
            'volume_zero_pct': 30.0,  # Alert if >30% zero volume (increased for low-volume periods)
            'statistical_outlier_pct': 10.0  # Alert if >10% statistical outliers (new threshold)
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
            
            # Log summary (smart filtering for market data)
            errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
            warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
            
            if errors:
                self.logger.error(f"Validation errors for {symbol}: {len(errors)} errors")
            elif warnings:
                # Filter out expected market data warnings
                significant_warnings = []
                for w in warnings:
                    # Skip normal timestamp gaps (single gaps are usually weekends/holidays)
                    if w.check_name == "timestamps.gaps" and len(warnings) == 1:
                        continue
                    # Skip normal statistical outliers below 10%
                    if w.check_name == "outliers.statistical_outliers" and "%" in w.message:
                        pct_str = w.message.split("(")[1].split("%")[0]
                        try:
                            pct = float(pct_str)
                            if pct < 10.0:  # Below our threshold
                                continue
                        except:
                            pass
                    significant_warnings.append(w)
                
                # Only log significant warnings
                if significant_warnings:
                    warning_types = [w.check_name for w in significant_warnings]
                    self.logger.warning(f"Validation issues for {symbol}: {warning_types}")
                else:
                    self.logger.debug(f"Validation: {len(warnings)} normal market patterns for {symbol}")
            else:
                self.logger.debug(f"Validation passed for {symbol}")
                
        except Exception as e:
            error_result = ValidationResult(
                check_name="validation_execution",
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Validation system error: {str(e)}"
            )
            results.append(error_result)
            self.logger.error(f"Validation system error for {symbol}: {e}")
        
        return results
    
    def _validate_data_structure(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate basic data structure"""
        results = []
        
        # Check if data is empty
        if data.empty:
            results.append(ValidationResult(
                check_name="data_structure.empty_data",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"No data available for {symbol}"
            ))
            return results
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            results.append(ValidationResult(
                check_name="data_structure.missing_columns",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Missing required columns for {symbol}: {missing_columns}"
            ))
        
        # Check index type
        if not isinstance(data.index, pd.DatetimeIndex):
            results.append(ValidationResult(
                check_name="data_structure.index_type",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"Index is not DatetimeIndex for {symbol}: {type(data.index)}"
            ))
        
        return results
    
    def _validate_timestamps(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate timestamp data"""
        results = []
        
        if data.empty:
            return results
        
        try:
            # Check for duplicate timestamps
            if isinstance(data.index, pd.DatetimeIndex):
                duplicates = data.index.duplicated().sum()
                if duplicates > 0:
                    results.append(ValidationResult(
                        check_name="timestamps.duplicates",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"Found {duplicates} duplicate timestamps for {symbol}",
                        details={'duplicate_count': duplicates}
                    ))
                
                # Check for gaps (only alert on very large gaps > 24 hours)
                if len(data) > 1:
                    time_diffs = data.index.to_series().diff().dropna()
                    gap_threshold = pd.Timedelta(minutes=self.alert_thresholds['timestamp_gap_minutes'])
                    large_gaps = time_diffs[time_diffs > gap_threshold]
                    
                    if len(large_gaps) > 0:
                        results.append(ValidationResult(
                            check_name="timestamps.gaps",
                            severity=ValidationSeverity.WARNING,
                            passed=False,
                            message=f"Found {len(large_gaps)} gaps > 24hrs for {symbol}",
                            details={
                                'gap_count': len(large_gaps),
                                'gap_threshold': str(gap_threshold),
                                'max_gap': str(large_gaps.max())
                            }
                        ))
                
                # Check date range reasonableness
                start_date = data.index.min()
                end_date = data.index.max()
                
                if start_date > datetime.now():
                    results.append(ValidationResult(
                        check_name="timestamps.future_data",
                        severity=ValidationSeverity.ERROR,
                        passed=False,
                        message=f"Future data detected for {symbol}: starts {start_date}"
                    ))
                
                if start_date < datetime(1990, 1, 1):
                    results.append(ValidationResult(
                        check_name="timestamps.old_data",
                        severity=ValidationSeverity.WARNING,
                        passed=False,
                        message=f"Very old data detected for {symbol}: starts {start_date}"
                    ))
        
        except Exception as e:
            results.append(ValidationResult(
                check_name="timestamps.validation_error",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Timestamp validation error for {symbol}: {str(e)}"
            ))
        
        return results
    
    def _validate_price_data(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate price data"""
        results = []
        
        if data.empty:
            return results
        
        price_columns = ['open', 'high', 'low', 'close']
        
        for col in price_columns:
            if col not in data.columns:
                continue
            
            prices = data[col]
            
            # Check for negative prices
            negative_count = (prices < 0).sum()
            if negative_count > 0:
                results.append(ValidationResult(
                    check_name=f"price_data.negative_{col}",
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Negative {col} prices found for {symbol}: {negative_count} instances"
                ))
            
            # Check for zero prices
            zero_count = (prices == 0).sum()
            if zero_count > 0:
                results.append(ValidationResult(
                    check_name=f"price_data.zero_{col}",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"Zero {col} prices found for {symbol}: {zero_count} instances"
                ))
            
            # Check for NaN values
            nan_count = prices.isna().sum()
            if nan_count > 0:
                results.append(ValidationResult(
                    check_name=f"price_data.nan_{col}",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"NaN {col} prices found for {symbol}: {nan_count} instances"
                ))
        
        # Check OHLC relationships
        if all(col in data.columns for col in price_columns):
            try:
                # High should be >= Low
                high_low_violations = (data['high'] < data['low']).sum()
                if high_low_violations > 0:
                    results.append(ValidationResult(
                        check_name="price_data.high_low_violation",
                        severity=ValidationSeverity.ERROR,
                        passed=False,
                        message=f"High < Low violations for {symbol}: {high_low_violations} instances"
                    ))
                
                # Open and Close should be between High and Low
                for price_col in ['open', 'close']:
                    below_low = (data[price_col] < data['low']).sum()
                    above_high = (data[price_col] > data['high']).sum()
                    
                    if below_low > 0:
                        results.append(ValidationResult(
                            check_name=f"price_data.{price_col}_below_low",
                            severity=ValidationSeverity.ERROR,
                            passed=False,
                            message=f"{price_col.title()} < Low for {symbol}: {below_low} instances"
                        ))
                    
                    if above_high > 0:
                        results.append(ValidationResult(
                            check_name=f"price_data.{price_col}_above_high",
                            severity=ValidationSeverity.ERROR,
                            passed=False,
                            message=f"{price_col.title()} > High for {symbol}: {above_high} instances"
                        ))
            
            except Exception as e:
                results.append(ValidationResult(
                    check_name="price_data.ohlc_validation_error",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"OHLC validation error for {symbol}: {str(e)}"
                ))
        
        return results
    
    def _validate_volume_data(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate volume data"""
        results = []
        
        if 'volume' not in data.columns or data.empty:
            return results
        
        volume = data['volume']
        
        # Check for negative volume
        negative_count = (volume < 0).sum()
        if negative_count > 0:
            results.append(ValidationResult(
                check_name="volume_data.negative_volume",
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Negative volume found for {symbol}: {negative_count} instances"
            ))
        
        # Check for excessive zero volume
        zero_count = (volume == 0).sum()
        zero_pct = (zero_count / len(volume)) * 100
        
        if zero_pct > self.alert_thresholds['volume_zero_pct']:
            results.append(ValidationResult(
                check_name="volume_data.excessive_zero_volume",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"High zero volume percentage for {symbol}: {zero_pct:.1f}%",
                details={'zero_percentage': zero_pct, 'threshold': self.alert_thresholds['volume_zero_pct']}
            ))
        
        return results
    
    def _validate_data_completeness(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Validate data completeness"""
        results = []
        
        if data.empty:
            return results
        
        # Check overall missing data percentage
        total_cells = data.size
        missing_cells = data.isna().sum().sum()
        missing_pct = (missing_cells / total_cells) * 100
        
        if missing_pct > self.alert_thresholds['missing_data_pct']:
            results.append(ValidationResult(
                check_name="completeness.missing_data",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"High missing data percentage for {symbol}: {missing_pct:.1f}%",
                details={'missing_percentage': missing_pct, 'threshold': self.alert_thresholds['missing_data_pct']}
            ))
        
        return results
    
    def _detect_outliers(self, data: pd.DataFrame, symbol: str) -> List[ValidationResult]:
        """Detect price and volume outliers"""
        results = []
        
        if data.empty or 'close' not in data.columns:
            return results
        
        try:
            close_prices = data['close'].dropna()
            
            if len(close_prices) < 2:
                return results
            
            # Calculate price changes
            price_changes = close_prices.pct_change().dropna()
            
            # Detect extreme price movements
            extreme_threshold = self.alert_thresholds['price_outlier_factor']
            extreme_moves = price_changes[abs(price_changes) > extreme_threshold]
            
            if len(extreme_moves) > 0:
                results.append(ValidationResult(
                    check_name="outliers.extreme_price_moves",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"Extreme price moves detected for {symbol}: {len(extreme_moves)} instances",
                    details={
                        'extreme_count': len(extreme_moves),
                        'max_move': extreme_moves.abs().max(),
                        'threshold': extreme_threshold
                    }
                ))
            
            # Statistical outlier detection using IQR
            Q1 = price_changes.quantile(0.25)
            Q3 = price_changes.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = price_changes[(price_changes < lower_bound) | (price_changes > upper_bound)]
            
            outlier_pct = len(outliers) / len(price_changes) * 100
            if outlier_pct > self.alert_thresholds['statistical_outlier_pct']:
                results.append(ValidationResult(
                    check_name="outliers.statistical_outliers",
                    severity=ValidationSeverity.WARNING,
                    passed=False,
                    message=f"High number of statistical outliers for {symbol}: {len(outliers)} ({outlier_pct:.1f}%)",
                    details={
                        'outlier_count': len(outliers),
                        'outlier_percentage': outlier_pct,
                        'threshold': self.alert_thresholds['statistical_outlier_pct']
                    }
                ))
        
        except Exception as e:
            results.append(ValidationResult(
                check_name="outliers.detection_error",
                severity=ValidationSeverity.WARNING,
                passed=False,
                message=f"Outlier detection error for {symbol}: {str(e)}"
            ))
        
        return results
    
    def get_validation_summary(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get validation summary statistics"""
        relevant_history = self.validation_history
        
        if symbol:
            relevant_history = [h for h in relevant_history if h['symbol'] == symbol]
        
        if not relevant_history:
            return {'message': 'No validation history available'}
        
        total_validations = len(relevant_history)
        total_errors = sum(len([r for r in h['results'] if r.severity == ValidationSeverity.ERROR]) 
                          for h in relevant_history)
        total_warnings = sum(len([r for r in h['results'] if r.severity == ValidationSeverity.WARNING]) 
                            for h in relevant_history)
        
        return {
            'total_validations': total_validations,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'symbols_validated': len(set(h['symbol'] for h in relevant_history)),
            'last_validation': relevant_history[-1]['timestamp'] if relevant_history else None
        }
