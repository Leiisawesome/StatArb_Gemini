#!/usr/bin/env python3
"""
Data Corruption Testing Module - Phase 2 Extension

This module implements data corruption and validation testing for the StatArb_Gemini
core_engine, focusing on data integrity, validation, and recovery mechanisms.

Components:
- DataCorruptionTester: Data integrity and corruption testing
- DataValidationTester: Data validation and sanitization testing
- RecoveryMechanismTester: Data recovery and backup testing

Author: StatArb_Gemini Performance Testing Team
Version: 2.0.0 (Phase 2 - Data Corruption Testing)
"""

import asyncio
import logging
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import copy

from .stress_testing import StressTestConfiguration, StressTestResult, StressTestType

logger = logging.getLogger(__name__)

# ============================================================================
# DATA CORRUPTION ENUMS AND DATA CLASSES
# ============================================================================

class CorruptionType(Enum):
    """Types of data corruption to simulate"""
    NAN_VALUES = "nan_values"
    INFINITE_VALUES = "infinite_values"
    NULL_VALUES = "null_values"
    WRONG_DATA_TYPES = "wrong_data_types"
    OUT_OF_RANGE_VALUES = "out_of_range_values"
    DUPLICATE_RECORDS = "duplicate_records"
    MISSING_FIELDS = "missing_fields"
    MALFORMED_JSON = "malformed_json"
    ENCODING_ERRORS = "encoding_errors"
    TIMESTAMP_CORRUPTION = "timestamp_corruption"

class DataIntegrityLevel(Enum):
    """Data integrity validation levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"

@dataclass
class CorruptionPattern:
    """Pattern for data corruption injection"""
    corruption_type: CorruptionType
    injection_rate: float  # 0.0 to 1.0
    target_fields: List[str]
    severity: float = 1.0  # 0.1 (mild) to 10.0 (severe)

@dataclass
class DataValidationRule:
    """Data validation rule definition"""
    field_name: str
    data_type: type
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    required: bool = True
    regex_pattern: Optional[str] = None

# ============================================================================
# DATA CORRUPTION TESTER
# ============================================================================

class DataCorruptionTester:
    """Test system resilience to data corruption and validation failures"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DataCorruptionTester")
        self.corruption_patterns = []
        self.validation_rules = []
        self.integrity_checkers = {}
        self.recovery_mechanisms = {}
        self._setup_enhanced_validation()
    
    def _setup_enhanced_validation(self):
        """Setup enhanced data validation mechanisms"""
        
        # Setup default validation rules for financial data
        self.validation_rules = [
            DataValidationRule('price', float, min_value=0.01, max_value=10000.0),
            DataValidationRule('volume', int, min_value=0, max_value=1000000000),
            DataValidationRule('timestamp', datetime, required=True),
            DataValidationRule('symbol', str, required=True),
            DataValidationRule('returns', float, min_value=-1.0, max_value=1.0)
        ]
        
        # Basic integrity checkers
        self.integrity_checkers = {
            'basic_validator': self._basic_data_validation,
        }
        
        # Basic recovery mechanisms
        self.recovery_mechanisms = {
            'simple_recovery': self._simple_data_recovery,
        }
    
    def _basic_data_validation(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """Basic data validation"""
        try:
            if data.empty:
                return False, "Data is empty"
            
            # Check for critical columns
            required_cols = ['price', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                return False, f"Missing columns: {missing_cols}"
            
            return True, "Basic validation passed"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _simple_data_recovery(self, data: pd.DataFrame, corruption_mask: pd.Series) -> pd.DataFrame:
        """Simple data recovery using forward fill"""
        try:
            recovered_data = data.copy()
            for column in recovered_data.columns:
                if pd.api.types.is_numeric_dtype(recovered_data[column]):
                    recovered_data[column] = recovered_data[column].fillna(method='ffill').fillna(0)
            return recovered_data
        except Exception:
            return data
        
    async def run_data_corruption_test(self, config: StressTestConfiguration,
                                     target_system: Any) -> StressTestResult:
        """Run comprehensive data corruption testing"""
        
        self.logger.info(f"🗂️ Starting data corruption test: {config.corruption_rate*100:.1f}% corruption rate")
        start_time = datetime.now()
        
        result = StressTestResult(
            test_type=StressTestType.DATA_CORRUPTION,
            configuration=config,
            start_time=start_time,
            end_time=start_time,
            duration_seconds=0.0
        )
        
        try:
            # Step 1: Generate clean baseline data
            clean_data = self._generate_clean_test_data()
            baseline_metrics = await self._test_clean_data_processing(target_system, clean_data)
            result.baseline_performance = baseline_metrics
            
            # Step 2: Generate corrupted data
            corrupted_data = self._inject_data_corruption(clean_data, config)
            
            # Step 3: Test system behavior with corrupted data
            corruption_metrics = await self._test_corrupted_data_processing(target_system, corrupted_data, config)
            result.stress_performance = corruption_metrics
            
            # Step 4: Test data validation and recovery
            validation_metrics = await self._test_data_validation_recovery(target_system, corrupted_data, clean_data)
            result.stress_performance.update(validation_metrics)
            
            # Step 5: Calculate data integrity score
            result.system_stability_score = self._calculate_data_integrity_score(result)
            result.success = True
            
        except Exception as e:
            result.failure_reason = str(e)
            self.logger.error(f"Data corruption test failed: {e}")
        
        finally:
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _generate_clean_test_data(self) -> Dict[str, pd.DataFrame]:
        """Generate clean test data for baseline testing"""
        
        # Generate market data
        timestamps = pd.date_range(start=datetime.now() - timedelta(days=1), periods=1000, freq='1min')
        
        market_data = pd.DataFrame({
            'timestamp': timestamps,
            'symbol': ['AAPL'] * 1000,
            'price': 150.0 + np.random.normal(0, 2, 1000),
            'volume': np.random.randint(100000, 1000000, 1000),
            'bid': 150.0 + np.random.normal(-0.1, 1, 1000),
            'ask': 150.0 + np.random.normal(0.1, 1, 1000),
            'high': 150.0 + np.random.normal(1, 2, 1000),
            'low': 150.0 + np.random.normal(-1, 2, 1000)
        })
        
        # Generate portfolio data
        portfolio_data = pd.DataFrame({
            'symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'],
            'position': [100, 50, 25, 75, 200],
            'avg_cost': [145.0, 280.0, 2500.0, 800.0, 450.0],
            'market_value': [15000.0, 14000.0, 62500.0, 60000.0, 90000.0],
            'unrealized_pnl': [500.0, -1000.0, 2500.0, -5000.0, 10000.0]
        })
        
        # Generate trade data
        trade_data = pd.DataFrame({
            'trade_id': [f"T{i:06d}" for i in range(100)],
            'timestamp': pd.date_range(start=datetime.now() - timedelta(hours=1), periods=100, freq='30s'),
            'symbol': np.random.choice(['AAPL', 'MSFT', 'GOOGL'], 100),
            'side': np.random.choice(['BUY', 'SELL'], 100),
            'quantity': np.random.randint(10, 1000, 100),
            'price': 150.0 + np.random.normal(0, 5, 100),
            'commission': np.random.uniform(1.0, 10.0, 100)
        })
        
        return {
            'market_data': market_data,
            'portfolio_data': portfolio_data,
            'trade_data': trade_data
        }
    
    def _inject_data_corruption(self, clean_data: Dict[str, pd.DataFrame], 
                              config: StressTestConfiguration) -> Dict[str, pd.DataFrame]:
        """Inject various types of data corruption"""
        
        self.logger.info(f"💉 Injecting data corruption: {len(config.corruption_types)} types")
        
        corrupted_data = {}
        
        for data_name, df in clean_data.items():
            corrupted_df = df.copy()
            
            for corruption_type in config.corruption_types:
                corrupted_df = self._apply_corruption_type(corrupted_df, corruption_type, config.corruption_rate)
            
            corrupted_data[data_name] = corrupted_df
        
        return corrupted_data
    
    def _apply_corruption_type(self, df: pd.DataFrame, corruption_type: str, 
                             corruption_rate: float) -> pd.DataFrame:
        """Apply specific type of corruption to dataframe"""
        
        corrupted_df = df.copy()
        num_rows = len(df)
        num_corruptions = int(num_rows * corruption_rate)
        
        if num_corruptions == 0:
            return corrupted_df
        
        # Select random rows for corruption
        corruption_indices = np.random.choice(num_rows, num_corruptions, replace=False)
        
        if corruption_type == 'nan':
            # Inject NaN values
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                for idx in corruption_indices:
                    col = np.random.choice(numeric_columns)
                    corrupted_df.loc[idx, col] = np.nan
        
        elif corruption_type == 'inf':
            # Inject infinite values
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                for idx in corruption_indices:
                    col = np.random.choice(numeric_columns)
                    corrupted_df.loc[idx, col] = np.inf if random.random() > 0.5 else -np.inf
        
        elif corruption_type == 'null':
            # Inject null/None values
            for idx in corruption_indices:
                col = np.random.choice(df.columns)
                corrupted_df.loc[idx, col] = None
        
        elif corruption_type == 'wrong_type':
            # Inject wrong data types
            for idx in corruption_indices:
                col = np.random.choice(df.columns)
                if df[col].dtype in ['int64', 'float64']:
                    corrupted_df.loc[idx, col] = "INVALID_NUMBER"
                elif df[col].dtype == 'object':
                    corrupted_df.loc[idx, col] = 99999
        
        elif corruption_type == 'out_of_range':
            # Inject out-of-range values
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 0:
                for idx in corruption_indices:
                    col = np.random.choice(numeric_columns)
                    if 'price' in col.lower():
                        corrupted_df.loc[idx, col] = -1000.0  # Negative price
                    elif 'volume' in col.lower():
                        corrupted_df.loc[idx, col] = -50000  # Negative volume
                    else:
                        corrupted_df.loc[idx, col] = 1e15  # Extremely large value
        
        elif corruption_type == 'duplicate':
            # Create duplicate records
            if len(corruption_indices) > 0:
                duplicate_rows = corrupted_df.iloc[corruption_indices].copy()
                corrupted_df = pd.concat([corrupted_df, duplicate_rows], ignore_index=True)
        
        elif corruption_type == 'missing_fields':
            # Remove random fields (set to NaN)
            for idx in corruption_indices:
                col = np.random.choice(df.columns)
                corrupted_df.loc[idx, col] = np.nan
        
        elif corruption_type == 'timestamp_corruption':
            # Corrupt timestamp fields
            timestamp_columns = df.select_dtypes(include=['datetime64']).columns
            if len(timestamp_columns) > 0:
                for idx in corruption_indices:
                    col = np.random.choice(timestamp_columns)
                    # Set to invalid timestamp
                    corrupted_df.loc[idx, col] = pd.Timestamp('1900-01-01')
        
        return corrupted_df
    
    async def _test_clean_data_processing(self, target_system: Any, 
                                        clean_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test system performance with clean data"""
        
        self.logger.info("📊 Testing clean data processing performance...")
        
        processing_times = []
        successful_operations = 0
        total_operations = 0
        
        for data_name, df in clean_data.items():
            for _, row in df.head(50).iterrows():  # Test first 50 rows
                total_operations += 1
                
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Simulate data processing
                    await self._simulate_data_processing(target_system, row.to_dict(), data_name)
                    
                    end_time = asyncio.get_event_loop().time()
                    processing_times.append((end_time - start_time) * 1000)  # Convert to ms
                    successful_operations += 1
                    
                except Exception as e:
                    self.logger.debug(f"Clean data processing failed: {e}")
        
        return {
            'clean_avg_processing_time_ms': np.mean(processing_times) if processing_times else 0,
            'clean_success_rate': successful_operations / total_operations if total_operations > 0 else 0,
            'clean_operations_per_sec': 1000 / np.mean(processing_times) if processing_times and np.mean(processing_times) > 0 else 0
        }
    
    async def _test_corrupted_data_processing(self, target_system: Any, 
                                            corrupted_data: Dict[str, pd.DataFrame],
                                            config: StressTestConfiguration) -> Dict[str, Any]:
        """Test system behavior with corrupted data"""
        
        self.logger.info("⚠️ Testing corrupted data processing...")
        
        processing_times = []
        successful_operations = 0
        failed_operations = 0
        error_types = {}
        
        for data_name, df in corrupted_data.items():
            for _, row in df.head(50).iterrows():  # Test first 50 rows
                try:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Simulate data processing with corruption
                    await self._simulate_data_processing(target_system, row.to_dict(), data_name)
                    
                    end_time = asyncio.get_event_loop().time()
                    processing_times.append((end_time - start_time) * 1000)
                    successful_operations += 1
                    
                except ValueError as e:
                    failed_operations += 1
                    error_types['value_error'] = error_types.get('value_error', 0) + 1
                except TypeError as e:
                    failed_operations += 1
                    error_types['type_error'] = error_types.get('type_error', 0) + 1
                except Exception as e:
                    failed_operations += 1
                    error_types['other_error'] = error_types.get('other_error', 0) + 1
        
        total_operations = successful_operations + failed_operations
        
        return {
            'corrupted_avg_processing_time_ms': np.mean(processing_times) if processing_times else float('inf'),
            'corrupted_success_rate': successful_operations / total_operations if total_operations > 0 else 0,
            'corrupted_error_rate': failed_operations / total_operations if total_operations > 0 else 1,
            'error_types': error_types,
            'total_corrupted_operations': total_operations,
            'corruption_detection_rate': failed_operations / total_operations if total_operations > 0 else 0
        }
    
    async def _simulate_data_processing(self, target_system: Any, data_row: Dict[str, Any], 
                                      data_type: str):
        """Simulate data processing operation"""
        
        # Validate data based on type
        if data_type == 'market_data':
            await self._validate_market_data(data_row)
        elif data_type == 'portfolio_data':
            await self._validate_portfolio_data(data_row)
        elif data_type == 'trade_data':
            await self._validate_trade_data(data_row)
        
        # Simulate processing delay
        await asyncio.sleep(0.001)  # 1ms processing time
        
        # Call target system if it has processing methods
        if hasattr(target_system, 'process_data'):
            await target_system.process_data(data_row)
    
    async def _validate_market_data(self, data: Dict[str, Any]):
        """Validate market data"""
        
        # Check required fields
        required_fields = ['timestamp', 'symbol', 'price', 'volume']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Check data types and ranges
        if not isinstance(data['symbol'], str) or len(data['symbol']) == 0:
            raise ValueError("Invalid symbol")
        
        price = data['price']
        if not isinstance(price, (int, float)) or np.isnan(price) or np.isinf(price) or price <= 0:
            raise ValueError(f"Invalid price: {price}")
        
        volume = data['volume']
        if not isinstance(volume, (int, float)) or np.isnan(volume) or np.isinf(volume) or volume < 0:
            raise ValueError(f"Invalid volume: {volume}")
        
        # Check timestamp
        if 'timestamp' in data:
            timestamp = data['timestamp']
            if pd.isna(timestamp) or timestamp < pd.Timestamp('2000-01-01'):
                raise ValueError(f"Invalid timestamp: {timestamp}")
    
    async def _validate_portfolio_data(self, data: Dict[str, Any]):
        """Validate portfolio data"""
        
        required_fields = ['symbol', 'position', 'avg_cost']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate position
        position = data['position']
        if not isinstance(position, (int, float)) or np.isnan(position) or np.isinf(position):
            raise ValueError(f"Invalid position: {position}")
        
        # Validate avg_cost
        avg_cost = data['avg_cost']
        if not isinstance(avg_cost, (int, float)) or np.isnan(avg_cost) or np.isinf(avg_cost) or avg_cost <= 0:
            raise ValueError(f"Invalid avg_cost: {avg_cost}")
    
    async def _validate_trade_data(self, data: Dict[str, Any]):
        """Validate trade data"""
        
        required_fields = ['trade_id', 'symbol', 'side', 'quantity', 'price']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate side
        if data['side'] not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid side: {data['side']}")
        
        # Validate quantity
        quantity = data['quantity']
        if not isinstance(quantity, (int, float)) or np.isnan(quantity) or np.isinf(quantity) or quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")
        
        # Validate price
        price = data['price']
        if not isinstance(price, (int, float)) or np.isnan(price) or np.isinf(price) or price <= 0:
            raise ValueError(f"Invalid price: {price}")
    
    async def _test_data_validation_recovery(self, target_system: Any, 
                                           corrupted_data: Dict[str, pd.DataFrame],
                                           clean_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test data validation and recovery mechanisms"""
        
        self.logger.info("🔄 Testing data validation and recovery...")
        
        recovery_metrics = {
            'validation_attempts': 0,
            'successful_validations': 0,
            'successful_recoveries': 0,
            'recovery_times_ms': [],
            'data_sanitization_success': 0
        }
        
        for data_name in corrupted_data.keys():
            corrupted_df = corrupted_data[data_name]
            clean_df = clean_data[data_name]
            
            # Test data sanitization
            sanitized_df = await self._attempt_data_sanitization(corrupted_df, data_name)
            
            # Compare sanitized data quality
            sanitization_success = self._compare_data_quality(sanitized_df, clean_df)
            if sanitization_success > 0.8:  # 80% data quality threshold
                recovery_metrics['data_sanitization_success'] += 1
            
            # Test recovery from backup
            recovery_start = asyncio.get_event_loop().time()
            
            try:
                # Simulate recovery from clean backup
                recovered_data = await self._simulate_data_recovery(clean_df, data_name)
                
                recovery_end = asyncio.get_event_loop().time()
                recovery_time_ms = (recovery_end - recovery_start) * 1000
                
                recovery_metrics['recovery_times_ms'].append(recovery_time_ms)
                recovery_metrics['successful_recoveries'] += 1
                
            except Exception as e:
                self.logger.debug(f"Data recovery failed for {data_name}: {e}")
        
        # Calculate recovery metrics
        if recovery_metrics['recovery_times_ms']:
            recovery_metrics['avg_recovery_time_ms'] = np.mean(recovery_metrics['recovery_times_ms'])
        
        recovery_metrics['recovery_success_rate'] = (
            recovery_metrics['successful_recoveries'] / len(corrupted_data)
            if len(corrupted_data) > 0 else 0
        )
        
        return recovery_metrics
    
    async def _attempt_data_sanitization(self, corrupted_df: pd.DataFrame, 
                                       data_type: str) -> pd.DataFrame:
        """Attempt to sanitize corrupted data"""
        
        sanitized_df = corrupted_df.copy()
        
        # Remove rows with all NaN values
        sanitized_df = sanitized_df.dropna(how='all')
        
        # Handle numeric columns
        numeric_columns = sanitized_df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            # Replace inf values with NaN
            sanitized_df[col] = sanitized_df[col].replace([np.inf, -np.inf], np.nan)
            
            # Fill NaN with median for numeric columns
            if sanitized_df[col].notna().sum() > 0:
                median_value = sanitized_df[col].median()
                sanitized_df[col] = sanitized_df[col].fillna(median_value)
        
        # Handle object columns
        object_columns = sanitized_df.select_dtypes(include=['object']).columns
        for col in object_columns:
            # Fill NaN with mode for categorical columns
            if sanitized_df[col].notna().sum() > 0:
                mode_value = sanitized_df[col].mode().iloc[0] if len(sanitized_df[col].mode()) > 0 else 'UNKNOWN'
                sanitized_df[col] = sanitized_df[col].fillna(mode_value)
        
        # Remove duplicates
        sanitized_df = sanitized_df.drop_duplicates()
        
        return sanitized_df
    
    def _compare_data_quality(self, sanitized_df: pd.DataFrame, 
                            clean_df: pd.DataFrame) -> float:
        """Compare data quality between sanitized and clean data"""
        
        if len(sanitized_df) == 0:
            return 0.0
        
        # Calculate quality score based on various factors
        quality_score = 0.0
        
        # Row count preservation (up to 30% loss acceptable)
        row_preservation = len(sanitized_df) / len(clean_df) if len(clean_df) > 0 else 0
        quality_score += min(1.0, row_preservation / 0.7) * 0.3  # 30% weight
        
        # Data completeness (non-null values)
        sanitized_completeness = sanitized_df.notna().sum().sum() / (len(sanitized_df) * len(sanitized_df.columns))
        clean_completeness = clean_df.notna().sum().sum() / (len(clean_df) * len(clean_df.columns))
        
        completeness_ratio = sanitized_completeness / clean_completeness if clean_completeness > 0 else 0
        quality_score += min(1.0, completeness_ratio) * 0.4  # 40% weight
        
        # Data type consistency
        type_consistency = 0.0
        common_columns = set(sanitized_df.columns) & set(clean_df.columns)
        
        for col in common_columns:
            if sanitized_df[col].dtype == clean_df[col].dtype:
                type_consistency += 1
        
        if len(common_columns) > 0:
            type_consistency /= len(common_columns)
        
        quality_score += type_consistency * 0.3  # 30% weight
        
        return quality_score
    
    async def _simulate_data_recovery(self, clean_df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Simulate data recovery from backup"""
        
        # Simulate recovery delay
        await asyncio.sleep(0.1)  # 100ms recovery time
        
        # Return clean data as "recovered" data
        return clean_df.copy()
    
    def _calculate_data_integrity_score(self, result: StressTestResult) -> float:
        """Calculate data integrity score (0-100)"""
        
        score = 100.0
        
        # Corruption detection capability
        detection_rate = result.stress_performance.get('corruption_detection_rate', 0)
        score *= detection_rate  # Full score only if all corruption is detected
        
        # Error handling capability
        error_rate = result.stress_performance.get('corrupted_error_rate', 1)
        if error_rate < 0.1:  # Less than 10% errors with corrupted data is concerning
            score -= 20  # Penalty for not detecting corruption
        
        # Recovery capability
        recovery_rate = result.stress_performance.get('recovery_success_rate', 0)
        score = (score + recovery_rate * 100) / 2  # Average with recovery score
        
        # Data sanitization capability
        sanitization_success = result.stress_performance.get('data_sanitization_success', 0)
        total_datasets = 3  # market_data, portfolio_data, trade_data
        sanitization_rate = sanitization_success / total_datasets if total_datasets > 0 else 0
        score += sanitization_rate * 10  # Bonus for successful sanitization
        
        return max(0.0, min(100.0, score))

# ============================================================================
# DATA VALIDATION TESTER
# ============================================================================

class DataValidationTester:
    """Test data validation rules and sanitization mechanisms"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DataValidationTester")
        self.validation_rules = []
        
    def add_validation_rule(self, rule: DataValidationRule):
        """Add a data validation rule"""
        self.validation_rules.append(rule)
    
    async def test_validation_rules(self, test_data: pd.DataFrame) -> Dict[str, Any]:
        """Test all validation rules against test data"""
        
        validation_results = {
            'total_rules': len(self.validation_rules),
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_errors': [],
            'field_validation_rates': {}
        }
        
        for _, row in test_data.iterrows():
            for rule in self.validation_rules:
                try:
                    is_valid = await self._validate_field(row, rule)
                    
                    if is_valid:
                        validation_results['passed_validations'] += 1
                    else:
                        validation_results['failed_validations'] += 1
                        validation_results['validation_errors'].append({
                            'field': rule.field_name,
                            'value': row.get(rule.field_name),
                            'rule_type': type(rule).__name__
                        })
                    
                    # Track per-field validation rates
                    field_name = rule.field_name
                    if field_name not in validation_results['field_validation_rates']:
                        validation_results['field_validation_rates'][field_name] = {'passed': 0, 'total': 0}
                    
                    validation_results['field_validation_rates'][field_name]['total'] += 1
                    if is_valid:
                        validation_results['field_validation_rates'][field_name]['passed'] += 1
                        
                except Exception as e:
                    validation_results['failed_validations'] += 1
                    validation_results['validation_errors'].append({
                        'field': rule.field_name,
                        'error': str(e),
                        'rule_type': type(rule).__name__
                    })
        
        # Calculate overall validation rate
        total_validations = validation_results['passed_validations'] + validation_results['failed_validations']
        validation_results['overall_validation_rate'] = (
            validation_results['passed_validations'] / total_validations
            if total_validations > 0 else 0
        )
        
        return validation_results
    
    async def _validate_field(self, row: pd.Series, rule: DataValidationRule) -> bool:
        """Validate a single field against a rule"""
        
        field_value = row.get(rule.field_name)
        
        # Check if field is required
        if rule.required and (field_value is None or pd.isna(field_value)):
            return False
        
        # Skip validation if field is not required and is missing
        if not rule.required and (field_value is None or pd.isna(field_value)):
            return True
        
        # Check data type
        if not isinstance(field_value, rule.data_type):
            try:
                # Attempt type conversion
                field_value = rule.data_type(field_value)
            except (ValueError, TypeError):
                return False
        
        # Check value range
        if rule.min_value is not None and field_value < rule.min_value:
            return False
        
        if rule.max_value is not None and field_value > rule.max_value:
            return False
        
        # Check allowed values
        if rule.allowed_values is not None and field_value not in rule.allowed_values:
            return False
        
        # Check regex pattern
        if rule.regex_pattern is not None:
            import re
            if not re.match(rule.regex_pattern, str(field_value)):
                return False
        
        return True

# ============================================================================
# RECOVERY MECHANISM TESTER
# ============================================================================

class RecoveryMechanismTester:
    """Test data recovery and backup mechanisms"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.RecoveryMechanismTester")
        
    async def test_backup_recovery(self, target_system: Any, 
                                 test_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test backup and recovery mechanisms"""
        
        recovery_results = {
            'backup_attempts': 0,
            'successful_backups': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0,
            'backup_times_ms': [],
            'recovery_times_ms': [],
            'data_integrity_after_recovery': []
        }
        
        for data_name, df in test_data.items():
            # Test backup
            recovery_results['backup_attempts'] += 1
            
            backup_start = asyncio.get_event_loop().time()
            backup_success = await self._test_backup_creation(target_system, df, data_name)
            backup_end = asyncio.get_event_loop().time()
            
            if backup_success:
                recovery_results['successful_backups'] += 1
                recovery_results['backup_times_ms'].append((backup_end - backup_start) * 1000)
            
            # Test recovery
            recovery_results['recovery_attempts'] += 1
            
            recovery_start = asyncio.get_event_loop().time()
            recovered_data, recovery_success = await self._test_data_recovery(target_system, data_name)
            recovery_end = asyncio.get_event_loop().time()
            
            if recovery_success:
                recovery_results['successful_recoveries'] += 1
                recovery_results['recovery_times_ms'].append((recovery_end - recovery_start) * 1000)
                
                # Check data integrity
                integrity_score = self._check_data_integrity(df, recovered_data)
                recovery_results['data_integrity_after_recovery'].append(integrity_score)
        
        # Calculate averages
        if recovery_results['backup_times_ms']:
            recovery_results['avg_backup_time_ms'] = np.mean(recovery_results['backup_times_ms'])
        
        if recovery_results['recovery_times_ms']:
            recovery_results['avg_recovery_time_ms'] = np.mean(recovery_results['recovery_times_ms'])
        
        if recovery_results['data_integrity_after_recovery']:
            recovery_results['avg_data_integrity_score'] = np.mean(recovery_results['data_integrity_after_recovery'])
        
        # Calculate success rates
        recovery_results['backup_success_rate'] = (
            recovery_results['successful_backups'] / recovery_results['backup_attempts']
            if recovery_results['backup_attempts'] > 0 else 0
        )
        
        recovery_results['recovery_success_rate'] = (
            recovery_results['successful_recoveries'] / recovery_results['recovery_attempts']
            if recovery_results['recovery_attempts'] > 0 else 0
        )
        
        return recovery_results
    
    async def _test_backup_creation(self, target_system: Any, data: pd.DataFrame, 
                                  data_name: str) -> bool:
        """Test backup creation"""
        
        try:
            # Simulate backup creation
            if hasattr(target_system, 'create_backup'):
                await target_system.create_backup(data_name, data)
            else:
                # Simulate backup delay
                await asyncio.sleep(0.05)  # 50ms backup time
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Backup creation failed for {data_name}: {e}")
            return False
    
    async def _test_data_recovery(self, target_system: Any, 
                                data_name: str) -> Tuple[Optional[pd.DataFrame], bool]:
        """Test data recovery"""
        
        try:
            # Simulate data recovery
            if hasattr(target_system, 'recover_data'):
                recovered_data = await target_system.recover_data(data_name)
            else:
                # Simulate recovery delay and return mock data
                await asyncio.sleep(0.1)  # 100ms recovery time
                recovered_data = pd.DataFrame({'mock': [1, 2, 3]})
            
            return recovered_data, True
            
        except Exception as e:
            self.logger.debug(f"Data recovery failed for {data_name}: {e}")
            return None, False
    
    def _check_data_integrity(self, original_data: pd.DataFrame, 
                            recovered_data: Optional[pd.DataFrame]) -> float:
        """Check data integrity after recovery"""
        
        if recovered_data is None:
            return 0.0
        
        # Simple integrity check - compare shapes and basic statistics
        integrity_score = 0.0
        
        # Shape comparison (30% weight)
        if original_data.shape == recovered_data.shape:
            integrity_score += 0.3
        else:
            # Partial credit for similar shapes
            shape_similarity = min(
                len(recovered_data) / len(original_data) if len(original_data) > 0 else 0,
                len(recovered_data.columns) / len(original_data.columns) if len(original_data.columns) > 0 else 0
            )
            integrity_score += 0.3 * shape_similarity
        
        # Column name comparison (20% weight)
        common_columns = set(original_data.columns) & set(recovered_data.columns)
        column_similarity = len(common_columns) / len(original_data.columns) if len(original_data.columns) > 0 else 0
        integrity_score += 0.2 * column_similarity
        
        # Data type comparison (25% weight)
        type_similarity = 0.0
        for col in common_columns:
            if original_data[col].dtype == recovered_data[col].dtype:
                type_similarity += 1
        
        if len(common_columns) > 0:
            type_similarity /= len(common_columns)
        
        integrity_score += 0.25 * type_similarity
        
        # Value comparison (25% weight) - sample comparison for performance
        value_similarity = 0.0
        sample_size = min(100, len(original_data), len(recovered_data))
        
        if sample_size > 0:
            for col in common_columns:
                if col in original_data.columns and col in recovered_data.columns:
                    orig_sample = original_data[col].head(sample_size)
                    rec_sample = recovered_data[col].head(sample_size)
                    
                    # Compare non-null values
                    orig_values = orig_sample.dropna()
                    rec_values = rec_sample.dropna()
                    
                    if len(orig_values) > 0 and len(rec_values) > 0:
                        # Simple equality check for a subset
                        matches = sum(1 for i in range(min(len(orig_values), len(rec_values))) 
                                    if orig_values.iloc[i] == rec_values.iloc[i])
                        value_similarity += matches / min(len(orig_values), len(rec_values))
            
            if len(common_columns) > 0:
                value_similarity /= len(common_columns)
        
        integrity_score += 0.25 * value_similarity
        
        return integrity_score

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def run_data_corruption_test_example():
    """Example usage of data corruption testing"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create mock target system
    class MockDataSystem:
        async def process_data(self, data):
            # Simple validation
            if 'price' in data and (data['price'] <= 0 or np.isnan(data['price']) or np.isinf(data['price'])):
                raise ValueError("Invalid price data")
            await asyncio.sleep(0.001)  # Simulate processing
            return {'processed': True}
    
    target_system = MockDataSystem()
    
    # Create data corruption tester
    corruption_tester = DataCorruptionTester()
    
    # Configure corruption test
    config = StressTestConfiguration(
        test_type=StressTestType.DATA_CORRUPTION,
        duration_seconds=60,
        corruption_rate=0.1,  # 10% corruption rate
        corruption_types=['nan', 'inf', 'null', 'out_of_range'],
        intensity_level=2.0
    )
    
    # Run data corruption test
    result = await corruption_tester.run_data_corruption_test(config, target_system)
    
    # Print results
    print(f"\\nData Corruption Test Results:")
    print(f"Success: {'✅' if result.success else '❌'}")
    print(f"Data Integrity Score: {result.system_stability_score:.1f}/100")
    print(f"Duration: {result.duration_seconds:.1f} seconds")
    
    if result.stress_performance:
        print(f"Corruption Detection Rate: {result.stress_performance.get('corruption_detection_rate', 0):.2%}")
        print(f"Recovery Success Rate: {result.stress_performance.get('recovery_success_rate', 0):.2%}")
        print(f"Error Types: {result.stress_performance.get('error_types', {})}")
    
    return result

# Enhanced validation methods for DataCorruptionTester
def _add_validation_methods_to_class():
    """Add validation methods to DataCorruptionTester class"""
    
    def _validate_data_checksum(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """Validate data integrity using checksums"""
        try:
            # Calculate checksum for critical columns
            critical_cols = ['price', 'volume', 'timestamp']
            available_cols = [col for col in critical_cols if col in data.columns]
            
            if not available_cols:
                return False, "No critical columns found for checksum validation"
            
            # Simple checksum validation
            for col in available_cols:
                if data[col].isnull().any():
                    return False, f"Null values detected in critical column: {col}"
                
                if col in ['price', 'volume'] and (data[col] < 0).any():
                    return False, f"Negative values detected in {col}"
            
            return True, "Checksum validation passed"
            
        except Exception as e:
            return False, f"Checksum validation error: {str(e)}"
    
        return False, f"Checksum validation error: {str(e)}"
    
    def _validate_data_schema(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """Validate data schema against expected structure"""
        try:
            required_columns = ['price', 'volume', 'timestamp']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                return False, f"Missing required columns: {missing_columns}"
            
            # Validate data types
            if 'price' in data.columns and not pd.api.types.is_numeric_dtype(data['price']):
                return False, "Price column must be numeric"
            
            if 'volume' in data.columns and not pd.api.types.is_numeric_dtype(data['volume']):
                return False, "Volume column must be numeric"
            
            return True, "Schema validation passed"
            
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"
    
    # Add all methods to the class
    DataCorruptionTester._validate_data_checksum = _validate_data_checksum
    DataCorruptionTester._validate_data_schema = _validate_data_schema
    
    # Setup integrity checkers after methods are added
    def setup_integrity_checkers(self):
        """Setup integrity checkers after methods are available"""
        self.integrity_checkers = {
            'checksum_validator': self._validate_data_checksum,
            'schema_validator': self._validate_data_schema,
            'range_validator': self._validate_data_ranges,
        }
    
    DataCorruptionTester.setup_integrity_checkers = setup_integrity_checkers

# Apply the validation methods
_add_validation_methods_to_class()

# Add enhanced validation methods to DataCorruptionTester class
def _add_enhanced_validation_methods():
    """Add enhanced validation methods to DataCorruptionTester"""
    
    def _validate_data_ranges(self, data: pd.DataFrame) -> Tuple[bool, str]:
        """Validate data values are within expected ranges"""
        try:
            for rule in self.validation_rules:
                if rule.field_name not in data.columns:
                    if rule.required:
                        return False, f"Required field missing: {rule.field_name}"
                    continue
                
                column_data = data[rule.field_name]
                
                # Check min/max values for numeric fields
                if rule.min_value is not None and pd.api.types.is_numeric_dtype(column_data):
                    if (column_data < rule.min_value).any():
                        return False, f"{rule.field_name} contains values below minimum: {rule.min_value}"
                
                if rule.max_value is not None and pd.api.types.is_numeric_dtype(column_data):
                    if (column_data > rule.max_value).any():
                        return False, f"{rule.field_name} contains values above maximum: {rule.max_value}"
            
            return True, "Range validation passed"
            
        except Exception as e:
            return False, f"Range validation error: {str(e)}"
    
    # Add methods to DataCorruptionTester class
    DataCorruptionTester._validate_data_ranges = _validate_data_ranges

# Apply enhanced validation methods
_add_enhanced_validation_methods()

if __name__ == "__main__":
    asyncio.run(run_data_corruption_test_example())
