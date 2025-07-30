#!/usr/bin/env python3
"""
Memory Optimizer
Phase 3: Advanced Analytics & Optimization - Batch 5
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import psutil
import gc
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    """Memory optimization for the trading system"""
    
    def __init__(self):
        self.memory_optimization_results = {}
        self.memory_usage_history = []
        
        logger.info("Initialized MemoryOptimizer")
    
    def analyze_memory_usage(self, data: pd.DataFrame) -> Dict:
        """Analyze memory usage of data structures"""
        
        try:
            logger.info("Analyzing memory usage...")
            
            # Get current memory usage
            process = psutil.Process()
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Analyze DataFrame memory usage
            data_memory = data.memory_usage(deep=True).sum() / 1024 / 1024  # MB
            
            # Analyze column-wise memory usage
            column_memory = data.memory_usage(deep=True) / 1024 / 1024  # MB
            
            # Memory usage analysis
            memory_analysis = {
                'total_memory_mb': current_memory,
                'data_memory_mb': data_memory,
                'data_memory_pct': (data_memory / current_memory) * 100 if current_memory > 0 else 0,
                'column_memory': column_memory.to_dict(),
                'memory_efficiency': self._calculate_memory_efficiency(data),
                'optimization_potential': self._calculate_optimization_potential(data),
                'analysis_date': datetime.now().isoformat()
            }
            
            logger.info(f"Memory analysis: {data_memory:.2f}MB data, {current_memory:.2f}MB total")
            return memory_analysis
            
        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            return {}
    
    def _calculate_memory_efficiency(self, data: pd.DataFrame) -> float:
        """Calculate memory efficiency score"""
        
        try:
            # Calculate memory efficiency based on data types
            total_memory = data.memory_usage(deep=True).sum()
            
            # Ideal memory usage (using optimal data types)
            ideal_memory = 0
            for col in data.columns:
                col_data = data[col]
                if pd.api.types.is_numeric_dtype(col_data):
                    # Estimate optimal numeric type
                    col_min = col_data.min()
                    col_max = col_data.max()
                    
                    if pd.isna(col_min) or pd.isna(col_max):
                        ideal_memory += len(col_data) * 8  # float64
                    elif col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
                        ideal_memory += len(col_data) * 1  # int8
                    elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
                        ideal_memory += len(col_data) * 2  # int16
                    elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                        ideal_memory += len(col_data) * 4  # int32
                    else:
                        ideal_memory += len(col_data) * 8  # int64/float64
                else:
                    # String/categorical data
                    ideal_memory += len(col_data) * 8  # estimate
            
            efficiency = (ideal_memory / total_memory) * 100 if total_memory > 0 else 100
            return min(efficiency, 100)  # Cap at 100%
            
        except Exception:
            return 50.0  # Default efficiency
    
    def _calculate_optimization_potential(self, data: pd.DataFrame) -> Dict:
        """Calculate memory optimization potential"""
        
        try:
            optimization_potential = {
                'numeric_optimization': 0,
                'categorical_optimization': 0,
                'datetime_optimization': 0,
                'overall_potential': 0
            }
            
            total_columns = len(data.columns)
            optimizable_columns = 0
            
            for col in data.columns:
                col_data = data[col]
                
                if pd.api.types.is_numeric_dtype(col_data):
                    # Check if numeric column can be optimized
                    col_min = col_data.min()
                    col_max = col_data.max()
                    
                    if not (pd.isna(col_min) or pd.isna(col_max)):
                        current_size = col_data.dtype.itemsize
                        optimal_size = 8  # Default to float64
                        
                        if col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
                            optimal_size = 1
                        elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
                            optimal_size = 2
                        elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                            optimal_size = 4
                        
                        if optimal_size < current_size:
                            optimizable_columns += 1
                            optimization_potential['numeric_optimization'] += 1
                
                elif pd.api.types.is_categorical_dtype(col_data):
                    # Check categorical optimization potential
                    unique_ratio = col_data.nunique() / len(col_data)
                    if unique_ratio < 0.5:  # Less than 50% unique values
                        optimizable_columns += 1
                        optimization_potential['categorical_optimization'] += 1
                
                elif pd.api.types.is_datetime64_any_dtype(col_data):
                    # Check datetime optimization potential
                    optimizable_columns += 1
                    optimization_potential['datetime_optimization'] += 1
            
            optimization_potential['overall_potential'] = (optimizable_columns / total_columns) * 100 if total_columns > 0 else 0
            
            return optimization_potential
            
        except Exception:
            return {'numeric_optimization': 0, 'categorical_optimization': 0, 'datetime_optimization': 0, 'overall_potential': 0}
    
    def optimize_memory_usage(self, data: pd.DataFrame) -> Dict:
        """Optimize memory usage of data structures"""
        
        try:
            logger.info("Optimizing memory usage...")
            
            # Measure original memory usage
            original_memory = data.memory_usage(deep=True).sum() / 1024 / 1024  # MB
            original_memory_analysis = self.analyze_memory_usage(data)
            
            # Create optimized copy
            optimized_data = data.copy()
            
            # Optimize numeric columns
            numeric_optimizations = 0
            for col in optimized_data.select_dtypes(include=[np.number]).columns:
                col_data = optimized_data[col]
                original_dtype = col_data.dtype
                
                # Find optimal data type
                col_min = col_data.min()
                col_max = col_data.max()
                
                if not (pd.isna(col_min) or pd.isna(col_max)):
                    if col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
                        optimized_data[col] = col_data.astype(np.int8)
                        numeric_optimizations += 1
                    elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
                        optimized_data[col] = col_data.astype(np.int16)
                        numeric_optimizations += 1
                    elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                        optimized_data[col] = col_data.astype(np.int32)
                        numeric_optimizations += 1
            
            # Optimize float columns
            float_optimizations = 0
            for col in optimized_data.select_dtypes(include=[np.floating]).columns:
                optimized_data[col] = optimized_data[col].astype(np.float32)
                float_optimizations += 1
            
            # Optimize categorical columns
            categorical_optimizations = 0
            for col in optimized_data.select_dtypes(include=['object']).columns:
                unique_ratio = optimized_data[col].nunique() / len(optimized_data[col])
                if unique_ratio < 0.5:  # Less than 50% unique values
                    optimized_data[col] = optimized_data[col].astype('category')
                    categorical_optimizations += 1
            
            # Measure optimized memory usage
            optimized_memory = optimized_data.memory_usage(deep=True).sum() / 1024 / 1024  # MB
            memory_savings = (original_memory - optimized_memory) / original_memory * 100
            
            # Force garbage collection
            gc.collect()
            
            # Store memory usage history
            self.memory_usage_history.append({
                'timestamp': datetime.now(),
                'original_memory': original_memory,
                'optimized_memory': optimized_memory,
                'memory_savings': memory_savings
            })
            
            optimization_results = {
                'original_memory_mb': original_memory,
                'optimized_memory_mb': optimized_memory,
                'memory_savings_mb': original_memory - optimized_memory,
                'memory_savings_pct': memory_savings,
                'optimizations_applied': {
                    'numeric_optimizations': numeric_optimizations,
                    'float_optimizations': float_optimizations,
                    'categorical_optimizations': categorical_optimizations,
                    'total_optimizations': numeric_optimizations + float_optimizations + categorical_optimizations
                },
                'optimization_date': datetime.now().isoformat()
            }
            
            # Store results
            optimization_id = f"memory_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.memory_optimization_results[optimization_id] = optimization_results
            
            logger.info(f"Memory optimization: {memory_savings:.1f}% savings ({original_memory:.2f}MB -> {optimized_memory:.2f}MB)")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {}
    
    def monitor_memory_usage(self, interval_seconds: int = 60) -> Dict:
        """Monitor memory usage over time"""
        
        try:
            logger.info(f"Starting memory monitoring (interval: {interval_seconds}s)")
            
            # Get current memory usage
            process = psutil.Process()
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            monitoring_results = {
                'current_memory_mb': current_memory,
                'system_memory_total_mb': system_memory.total / 1024 / 1024,
                'system_memory_available_mb': system_memory.available / 1024 / 1024,
                'system_memory_used_pct': system_memory.percent,
                'memory_usage_pct': (current_memory / (system_memory.total / 1024 / 1024)) * 100,
                'monitoring_date': datetime.now().isoformat()
            }
            
            logger.info(f"Memory monitoring: {current_memory:.2f}MB used, {system_memory.percent:.1f}% system usage")
            return monitoring_results
            
        except Exception as e:
            logger.error(f"Memory monitoring failed: {e}")
            return {}
    
    def get_memory_summary(self) -> Dict:
        """Get memory optimization summary"""
        return {
            'total_optimizations': len(self.memory_optimization_results),
            'memory_history_count': len(self.memory_usage_history),
            'available_optimizations': list(self.memory_optimization_results.keys()),
            'average_memory_savings': np.mean([h['memory_savings'] for h in self.memory_usage_history]) if self.memory_usage_history else 0
        }
