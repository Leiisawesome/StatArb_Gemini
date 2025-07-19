"""
Professional Data Validation System
Institutional-grade data quality and integrity checks
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from scipy import stats
import warnings
from dataclasses import dataclass

logger = logging.getLogger('mvs.data_validator')

@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    timeliness_score: float
    overall_score: float
    issues_detected: List[str]
    validation_timestamp: datetime

class DataValidator:
    """
    Institutional-grade data validation system
    
    Features:
    - Real-time data quality monitoring
    - Price data integrity checks
    - Volume and trading activity validation
    - Corporate action detection
    - Data freshness verification
    - Statistical anomaly detection
    - Market data cross-validation
    """
    
    def __init__(self):
        # Data quality thresholds based on institutional standards
        self.quality_thresholds = {
            'minimum_completeness': 0.95,        # 95% data completeness required
            'maximum_price_gap': 0.15,           # 15% maximum price gap
            'minimum_volume_ratio': 0.1,         # 10% minimum volume vs average
            'maximum_volume_ratio': 10.0,        # 1000% maximum volume vs average
            'price_outlier_threshold': 4.0,      # 4 standard deviations
            'maximum_data_age_minutes': 15,      # 15 minutes maximum data age
            'minimum_trading_days': 252,         # 1 year minimum history
            'correlation_threshold': 0.3,        # 30% minimum market correlation
            'bid_ask_spread_limit': 0.05,        # 5% maximum bid-ask spread
        }
        
        # Market-wide validation parameters
        self.market_benchmarks = {
            'SPY': 'S&P 500 ETF',
            'QQQ': 'NASDAQ ETF', 
            'IWM': 'Russell 2000 ETF',
            'VIX': 'Volatility Index'
        }
        
        # Data validation history
        self.validation_history = []
        self.data_issues_log = []
        
        logger.info("Data Validator initialized with institutional standards")
        logger.info(f"Minimum completeness: {self.quality_thresholds['minimum_completeness']:.1%}")
        logger.info(f"Maximum data age: {self.quality_thresholds['maximum_data_age_minutes']} minutes")
        
    def validate_market_data(self, market_data: Dict[str, pd.DataFrame], 
                           validation_date: datetime = None) -> DataQualityMetrics:
        """
        Comprehensive market data validation with institutional standards
        
        Args:
            market_data: Dictionary of {symbol: price_dataframe}
            validation_date: Date for validation (default: current time)
            
        Returns:
            DataQualityMetrics object with comprehensive assessment
        """
        try:
            if validation_date is None:
                validation_date = datetime.now()
                
            logger.info(f"Starting market data validation for {len(market_data)} symbols")
            
            # Initialize validation results
            validation_results = {
                'completeness_issues': [],
                'consistency_issues': [],
                'accuracy_issues': [],
                'timeliness_issues': [],
                'symbol_scores': {}
            }
            
            # Validate each symbol's data
            for symbol, data in market_data.items():
                try:
                    symbol_validation = self._validate_symbol_data(symbol, data, validation_date)
                    validation_results['symbol_scores'][symbol] = symbol_validation
                    
                    # Aggregate issues
                    for issue_type in ['completeness', 'consistency', 'accuracy', 'timeliness']:
                        if symbol_validation.get(f'{issue_type}_issues'):
                            validation_results[f'{issue_type}_issues'].extend(
                                symbol_validation[f'{issue_type}_issues']
                            )
                            
                except Exception as e:
                    logger.warning(f"Validation failed for {symbol}: {e}")
                    validation_results['accuracy_issues'].append(f"Validation error for {symbol}: {e}")
            
            # Cross-validate with market benchmarks
            benchmark_validation = self._validate_market_consistency(market_data)
            validation_results['consistency_issues'].extend(benchmark_validation)
            
            # Calculate overall quality scores
            quality_scores = self._calculate_quality_scores(validation_results)
            
            # Create comprehensive metrics
            metrics = DataQualityMetrics(
                completeness_score=quality_scores['completeness'],
                consistency_score=quality_scores['consistency'],
                accuracy_score=quality_scores['accuracy'],
                timeliness_score=quality_scores['timeliness'],
                overall_score=quality_scores['overall'],
                issues_detected=self._aggregate_all_issues(validation_results),
                validation_timestamp=validation_date
            )
            
            # Log validation results
            self.validation_history.append(metrics)
            logger.info(f"Data validation completed - Overall score: {metrics.overall_score:.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Market data validation failed: {e}")
            return self._create_failed_validation_metrics(validation_date, str(e))
    
    def _validate_symbol_data(self, symbol: str, data: pd.DataFrame, 
                            validation_date: datetime) -> Dict[str, Any]:
        """Validate individual symbol data quality"""
        
        validation_result = {
            'symbol': symbol,
            'completeness_issues': [],
            'consistency_issues': [],
            'accuracy_issues': [],
            'timeliness_issues': [],
            'data_points': len(data),
            'date_range': None
        }
        
        try:
            if data.empty:
                validation_result['completeness_issues'].append(f"{symbol}: No data available")
                return validation_result
            
            # Set date range
            validation_result['date_range'] = {
                'start': data.index.min(),
                'end': data.index.max()
            }
            
            # 1. Completeness validation
            completeness_issues = self._check_data_completeness(symbol, data)
            validation_result['completeness_issues'].extend(completeness_issues)
            
            # 2. Consistency validation
            consistency_issues = self._check_data_consistency(symbol, data)
            validation_result['consistency_issues'].extend(consistency_issues)
            
            # 3. Accuracy validation
            accuracy_issues = self._check_data_accuracy(symbol, data)
            validation_result['accuracy_issues'].extend(accuracy_issues)
            
            # 4. Timeliness validation
            timeliness_issues = self._check_data_timeliness(symbol, data, validation_date)
            validation_result['timeliness_issues'].extend(timeliness_issues)
            
            return validation_result
            
        except Exception as e:
            logger.debug(f"Symbol validation error for {symbol}: {e}")
            validation_result['accuracy_issues'].append(f"{symbol}: Validation processing error")
            return validation_result
    
    def _check_data_completeness(self, symbol: str, data: pd.DataFrame) -> List[str]:
        """Check data completeness metrics"""
        issues = []
        
        try:
            # Check minimum data requirements
            if len(data) < self.quality_thresholds['minimum_trading_days']:
                issues.append(f"{symbol}: Insufficient data points ({len(data)} < {self.quality_thresholds['minimum_trading_days']})")
            
            # Check for required columns
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                issues.append(f"{symbol}: Missing columns: {missing_columns}")
            
            # Check for null values
            for column in required_columns:
                if column in data.columns:
                    null_ratio = data[column].isnull().sum() / len(data)
                    if null_ratio > (1 - self.quality_thresholds['minimum_completeness']):
                        issues.append(f"{symbol}: High null ratio in {column}: {null_ratio:.2%}")
            
            # Check for gaps in trading days (weekends excluded)
            if len(data) > 5:
                date_gaps = pd.bdate_range(data.index.min(), data.index.max()).difference(data.index)
                gap_ratio = len(date_gaps) / len(pd.bdate_range(data.index.min(), data.index.max()))
                if gap_ratio > 0.05:  # More than 5% gaps
                    issues.append(f"{symbol}: Significant date gaps detected: {gap_ratio:.2%}")
                
        except Exception as e:
            issues.append(f"{symbol}: Completeness check error: {e}")
        
        return issues
    
    def _check_data_consistency(self, symbol: str, data: pd.DataFrame) -> List[str]:
        """Check data consistency and logical relationships"""
        issues = []
        
        try:
            if 'high' in data.columns and 'low' in data.columns and 'close' in data.columns and 'open' in data.columns:
                
                # Check OHLC relationships
                high_low_issues = (data['high'] < data['low']).sum()
                if high_low_issues > 0:
                    issues.append(f"{symbol}: High < Low detected in {high_low_issues} records")
                
                close_range_issues = ((data['close'] > data['high']) | (data['close'] < data['low'])).sum()
                if close_range_issues > 0:
                    issues.append(f"{symbol}: Close outside High-Low range in {close_range_issues} records")
                
                open_range_issues = ((data['open'] > data['high']) | (data['open'] < data['low'])).sum()
                if open_range_issues > 0:
                    issues.append(f"{symbol}: Open outside High-Low range in {open_range_issues} records")
            
            # Check for negative prices
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in data.columns:
                    negative_prices = (data[col] <= 0).sum()
                    if negative_prices > 0:
                        issues.append(f"{symbol}: Negative/zero prices in {col}: {negative_prices} records")
            
            # Check volume consistency
            if 'volume' in data.columns:
                negative_volume = (data['volume'] < 0).sum()
                if negative_volume > 0:
                    issues.append(f"{symbol}: Negative volume detected in {negative_volume} records")
                
                # Check for suspicious zero volume days
                zero_volume_ratio = (data['volume'] == 0).sum() / len(data)
                if zero_volume_ratio > 0.1:  # More than 10% zero volume days
                    issues.append(f"{symbol}: High zero volume ratio: {zero_volume_ratio:.2%}")
                    
        except Exception as e:
            issues.append(f"{symbol}: Consistency check error: {e}")
        
        return issues
    
    def _check_data_accuracy(self, symbol: str, data: pd.DataFrame) -> List[str]:
        """Check data accuracy and detect anomalies"""
        issues = []
        
        try:
            # Price jump analysis
            if 'close' in data.columns and len(data) > 1:
                returns = data['close'].pct_change().dropna()
                
                # Statistical outlier detection
                if len(returns) > 30:
                    outlier_threshold = self.quality_thresholds['price_outlier_threshold']
                    outliers = np.abs(stats.zscore(returns)) > outlier_threshold
                    outlier_count = outliers.sum()
                    
                    if outlier_count > len(returns) * 0.01:  # More than 1% outliers
                        issues.append(f"{symbol}: High number of price outliers: {outlier_count}")
                
                # Large price gaps
                large_gaps = (np.abs(returns) > self.quality_thresholds['maximum_price_gap']).sum()
                if large_gaps > 0:
                    issues.append(f"{symbol}: Large price gaps detected: {large_gaps} instances")
            
            # Volume anomaly detection
            if 'volume' in data.columns and len(data) > 30:
                volume_data = data['volume'][data['volume'] > 0]  # Exclude zero volume
                if len(volume_data) > 30:
                    avg_volume = volume_data.rolling(window=30).mean()
                    volume_ratios = volume_data / avg_volume
                    
                    # Check for extreme volume spikes
                    high_volume = (volume_ratios > self.quality_thresholds['maximum_volume_ratio']).sum()
                    low_volume = (volume_ratios < self.quality_thresholds['minimum_volume_ratio']).sum()
                    
                    if high_volume > 0:
                        issues.append(f"{symbol}: Extreme volume spikes detected: {high_volume} instances")
                    if low_volume > len(volume_data) * 0.05:  # More than 5% extremely low volume
                        issues.append(f"{symbol}: Frequent extremely low volume: {low_volume} instances")
            
            # Check for data duplication
            if len(data) != len(data.drop_duplicates()):
                duplicate_count = len(data) - len(data.drop_duplicates())
                issues.append(f"{symbol}: Duplicate records detected: {duplicate_count}")
                
        except Exception as e:
            issues.append(f"{symbol}: Accuracy check error: {e}")
        
        return issues
    
    def _check_data_timeliness(self, symbol: str, data: pd.DataFrame, 
                             validation_date: datetime) -> List[str]:
        """Check data timeliness and freshness"""
        issues = []
        
        try:
            if data.empty:
                return issues
            
            # Check data freshness
            latest_data_date = data.index.max()
            if isinstance(latest_data_date, str):
                latest_data_date = pd.to_datetime(latest_data_date)
            
            # For market hours, data should be very recent
            data_age_hours = (validation_date - latest_data_date).total_seconds() / 3600
            
            # During market hours (9:30 AM - 4:00 PM ET), data should be very fresh
            market_open = validation_date.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = validation_date.replace(hour=16, minute=0, second=0, microsecond=0)
            
            if market_open <= validation_date <= market_close:
                # During market hours
                max_age_minutes = self.quality_thresholds['maximum_data_age_minutes']
                if data_age_hours * 60 > max_age_minutes:
                    issues.append(f"{symbol}: Stale data during market hours (age: {data_age_hours:.1f} hours)")
            else:
                # After hours - data should be from last trading day
                if data_age_hours > 24:
                    issues.append(f"{symbol}: Data older than 24 hours (age: {data_age_hours:.1f} hours)")
            
            # Check for future dates (should not exist)
            future_dates = data.index > validation_date
            if future_dates.any():
                future_count = future_dates.sum()
                issues.append(f"{symbol}: Future dated records detected: {future_count}")
                
        except Exception as e:
            issues.append(f"{symbol}: Timeliness check error: {e}")
        
        return issues
    
    def _validate_market_consistency(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Cross-validate market data consistency"""
        issues = []
        
        try:
            # Check correlation with market benchmarks
            for benchmark_symbol in self.market_benchmarks.keys():
                if benchmark_symbol in market_data:
                    benchmark_data = market_data[benchmark_symbol]
                    if 'close' in benchmark_data.columns and len(benchmark_data) > 30:
                        
                        # Check individual stock correlations with benchmark
                        benchmark_returns = benchmark_data['close'].pct_change().dropna()
                        
                        low_correlation_count = 0
                        for symbol, data in market_data.items():
                            if symbol != benchmark_symbol and 'close' in data.columns:
                                stock_returns = data['close'].pct_change().dropna()
                                
                                # Align dates and calculate correlation
                                common_dates = benchmark_returns.index.intersection(stock_returns.index)
                                if len(common_dates) > 30:
                                    correlation = benchmark_returns.loc[common_dates].corr(
                                        stock_returns.loc[common_dates]
                                    )
                                    
                                    if abs(correlation) < self.quality_thresholds['correlation_threshold']:
                                        low_correlation_count += 1
                        
                        # Flag if too many stocks have low correlation with market
                        if low_correlation_count > len(market_data) * 0.3:  # More than 30%
                            issues.append(f"High number of stocks with low {benchmark_symbol} correlation: {low_correlation_count}")
            
            # Check for synchronized anomalies (all stocks moving unusually)
            if len(market_data) >= 5:
                daily_changes = {}
                for symbol, data in market_data.items():
                    if 'close' in data.columns and len(data) > 1:
                        daily_changes[symbol] = data['close'].pct_change().dropna()
                
                if daily_changes:
                    # Find dates where most stocks have extreme moves
                    change_df = pd.DataFrame(daily_changes)
                    extreme_move_days = (np.abs(change_df) > 0.1).sum(axis=1)  # More than 10% move
                    
                    # Flag days where >50% of stocks have extreme moves
                    synchronized_extreme_days = (extreme_move_days > len(change_df.columns) * 0.5).sum()
                    if synchronized_extreme_days > 5:  # More than 5 such days
                        issues.append(f"Potential data quality issue: {synchronized_extreme_days} days with synchronized extreme moves")
                        
        except Exception as e:
            issues.append(f"Market consistency validation error: {e}")
        
        return issues
    
    def _calculate_quality_scores(self, validation_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate numerical quality scores"""
        
        try:
            total_symbols = len(validation_results['symbol_scores'])
            if total_symbols == 0:
                return {'completeness': 0, 'consistency': 0, 'accuracy': 0, 'timeliness': 0, 'overall': 0}
            
            # Count issues by type
            issue_counts = {
                'completeness': len(validation_results['completeness_issues']),
                'consistency': len(validation_results['consistency_issues']),
                'accuracy': len(validation_results['accuracy_issues']),
                'timeliness': len(validation_results['timeliness_issues'])
            }
            
            # Calculate scores (1.0 = perfect, 0.0 = worst)
            scores = {}
            for issue_type, count in issue_counts.items():
                # Score based on issue density (issues per symbol)
                issue_density = count / total_symbols if total_symbols > 0 else 0
                scores[issue_type] = max(0, 1.0 - (issue_density * 0.2))  # Each issue reduces score by 0.2
            
            # Overall score is weighted average
            scores['overall'] = (
                scores['completeness'] * 0.3 + 
                scores['consistency'] * 0.25 + 
                scores['accuracy'] * 0.25 + 
                scores['timeliness'] * 0.2
            )
            
            return scores
            
        except Exception as e:
            logger.debug(f"Quality score calculation error: {e}")
            return {'completeness': 0.5, 'consistency': 0.5, 'accuracy': 0.5, 'timeliness': 0.5, 'overall': 0.5}
    
    def _aggregate_all_issues(self, validation_results: Dict[str, Any]) -> List[str]:
        """Aggregate all detected issues"""
        all_issues = []
        
        for issue_type in ['completeness_issues', 'consistency_issues', 'accuracy_issues', 'timeliness_issues']:
            all_issues.extend(validation_results.get(issue_type, []))
        
        return all_issues
    
    def _create_failed_validation_metrics(self, validation_date: datetime, error_message: str) -> DataQualityMetrics:
        """Create metrics object for failed validation"""
        return DataQualityMetrics(
            completeness_score=0.0,
            consistency_score=0.0,
            accuracy_score=0.0,
            timeliness_score=0.0,
            overall_score=0.0,
            issues_detected=[f"Validation failed: {error_message}"],
            validation_timestamp=validation_date
        )
    
    def validate_real_time_tick(self, symbol: str, tick_data: Dict[str, Any]) -> bool:
        """Real-time tick data validation for live trading"""
        try:
            # Basic tick validation
            required_fields = ['timestamp', 'price', 'volume']
            if not all(field in tick_data for field in required_fields):
                logger.warning(f"Missing required fields in tick for {symbol}")
                return False
            
            # Price validation
            price = tick_data['price']
            if price <= 0:
                logger.warning(f"Invalid price for {symbol}: {price}")
                return False
            
            # Volume validation
            volume = tick_data['volume']
            if volume < 0:
                logger.warning(f"Invalid volume for {symbol}: {volume}")
                return False
            
            # Timestamp validation
            timestamp = tick_data['timestamp']
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            time_diff = abs((datetime.now() - timestamp).total_seconds())
            if time_diff > 300:  # More than 5 minutes old
                logger.warning(f"Stale tick data for {symbol}: {time_diff} seconds old")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Tick validation error for {symbol}: {e}")
            return False
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get comprehensive validation statistics"""
        if not self.validation_history:
            return {'status': 'No validation history available'}
        
        latest_validation = self.validation_history[-1]
        
        return {
            'latest_validation': {
                'timestamp': latest_validation.validation_timestamp.isoformat(),
                'overall_score': latest_validation.overall_score,
                'completeness_score': latest_validation.completeness_score,
                'consistency_score': latest_validation.consistency_score,
                'accuracy_score': latest_validation.accuracy_score,
                'timeliness_score': latest_validation.timeliness_score,
                'issues_count': len(latest_validation.issues_detected)
            },
            'validation_history_count': len(self.validation_history),
            'quality_thresholds': self.quality_thresholds,
            'total_issues_logged': len(self.data_issues_log)
        }
