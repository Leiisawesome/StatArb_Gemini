#!/usr/bin/env python3
"""
Statistical Analysis Engine
Phase 3: Advanced Analytics & Optimization - Batch 2
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class StatisticalEngine:
    """Advanced statistical analysis engine"""
    
    def __init__(self):
        self.analysis_results = {}
        logger.info("Initialized StatisticalEngine")
    
    def analyze_correlations(self, data: pd.DataFrame, symbols: List[str] = None) -> Dict:
        """Analyze correlations between assets"""
        
        if symbols is None:
            symbols = [col for col in data.columns if col.endswith('_close')]
        
        # Calculate returns
        returns_data = {}
        for symbol in symbols:
            if symbol in data.columns:
                returns_data[symbol] = data[symbol].pct_change().dropna()
        
        if not returns_data:
            logger.warning("No valid symbols found for correlation analysis")
            return {}
        
        returns_df = pd.DataFrame(returns_data)
        
        # Calculate correlation matrices
        pearson_corr = returns_df.corr(method='pearson')
        spearman_corr = returns_df.corr(method='spearman')
        
        # Find high correlations
        high_correlations = []
        for i in range(len(pearson_corr.columns)):
            for j in range(i+1, len(pearson_corr.columns)):
                pearson_val = pearson_corr.iloc[i, j]
                spearman_val = spearman_corr.iloc[i, j]
                
                if abs(pearson_val) > 0.7 or abs(spearman_val) > 0.7:
                    high_correlations.append({
                        'symbol1': pearson_corr.columns[i],
                        'symbol2': pearson_corr.columns[j],
                        'pearson': pearson_val,
                        'spearman': spearman_val
                    })
        
        results = {
            'pearson_correlation': pearson_corr.to_dict(),
            'spearman_correlation': spearman_corr.to_dict(),
            'high_correlations': high_correlations,
            'correlation_summary': {
                'total_pairs': len(pearson_corr.columns) * (len(pearson_corr.columns) - 1) // 2,
                'high_correlation_pairs': len(high_correlations),
                'avg_pearson': pearson_corr.values[np.triu_indices_from(pearson_corr.values, k=1)].mean(),
                'avg_spearman': spearman_corr.values[np.triu_indices_from(spearman_corr.values, k=1)].mean()
            }
        }
        
        logger.info(f"Correlation analysis completed: {len(high_correlations)} high correlations found")
        return results
    
    def test_stationarity(self, data: pd.Series, symbol: str = None) -> Dict:
        """Test for stationarity using variance ratio test"""
        
        # Remove NaN values
        clean_data = data.dropna()
        
        if len(clean_data) < 10:
            logger.warning(f"Insufficient data for stationarity test: {len(clean_data)} points")
            return {}
        
        try:
            # Simple variance ratio test
            returns = clean_data.pct_change().dropna()
            
            # Calculate variance ratios
            var_1 = returns.var()
            var_5 = returns.rolling(5).sum().var()
            var_10 = returns.rolling(10).sum().var()
            
            # Variance ratio should be close to 1 for stationary series
            vr_5 = var_5 / (5 * var_1) if var_1 > 0 else 1
            vr_10 = var_10 / (10 * var_1) if var_1 > 0 else 1
            
            # Simple stationarity test
            is_stationary = abs(vr_5 - 1) < 0.2 and abs(vr_10 - 1) < 0.2
            
            results = {
                'variance_ratio_5': vr_5,
                'variance_ratio_10': vr_10,
                'is_stationary': is_stationary,
                'test_type': 'Variance Ratio Test',
                'data_length': len(clean_data)
            }
            
            logger.info(f"Stationarity test for {symbol}: {'Stationary' if results['is_stationary'] else 'Non-stationary'}")
            return results
            
        except Exception as e:
            logger.error(f"Error in stationarity test: {e}")
            return {}
    
    def test_cointegration(self, data1: pd.Series, data2: pd.Series, 
                          symbol1: str = None, symbol2: str = None) -> Dict:
        """Test for cointegration between two time series"""
        
        # Remove NaN values and align data
        clean_data1 = data1.dropna()
        clean_data2 = data2.dropna()
        
        # Align indices
        common_index = clean_data1.index.intersection(clean_data2.index)
        if len(common_index) < 30:
            logger.warning(f"Insufficient common data for cointegration test: {len(common_index)} points")
            return {}
        
        aligned_data1 = clean_data1.loc[common_index]
        aligned_data2 = clean_data2.loc[common_index]
        
        try:
            # Simple cointegration test using correlation of differences
            diff1 = aligned_data1.diff().dropna()
            diff2 = aligned_data2.diff().dropna()
            
            # Align differences
            common_diff_index = diff1.index.intersection(diff2.index)
            if len(common_diff_index) < 10:
                return {}
            
            diff1_aligned = diff1.loc[common_diff_index]
            diff2_aligned = diff2.loc[common_diff_index]
            
            # Calculate correlation of differences
            correlation = diff1_aligned.corr(diff2_aligned)
            
            # Simple cointegration test
            is_cointegrated = abs(correlation) > 0.7
            
            results = {
                'correlation': correlation,
                'is_cointegrated': is_cointegrated,
                'test_type': 'Correlation Test',
                'data_length': len(common_index)
            }
            
            logger.info(f"Cointegration test {symbol1}-{symbol2}: {'Cointegrated' if results['is_cointegrated'] else 'Not cointegrated'}")
            return results
            
        except Exception as e:
            logger.error(f"Error in cointegration test: {e}")
            return {}
    
    def calculate_rolling_statistics(self, data: pd.Series, window: int = 20) -> pd.DataFrame:
        """Calculate rolling statistics for a time series"""
        
        if len(data) < window:
            logger.warning(f"Insufficient data for rolling statistics: {len(data)} < {window}")
            return pd.DataFrame()
        
        rolling_stats = pd.DataFrame({
            'mean': data.rolling(window=window).mean(),
            'std': data.rolling(window=window).std(),
            'min': data.rolling(window=window).min(),
            'max': data.rolling(window=window).max(),
            'skewness': data.rolling(window=window).skew(),
            'kurtosis': data.rolling(window=window).kurt(),
            'quantile_25': data.rolling(window=window).quantile(0.25),
            'quantile_75': data.rolling(window=window).quantile(0.75)
        })
        
        logger.info(f"Rolling statistics calculated with window {window}")
        return rolling_stats
    
    def detect_outliers(self, data: pd.Series, method: str = 'zscore', threshold: float = 3.0) -> Dict:
        """Detect outliers using various methods"""
        
        clean_data = data.dropna()
        
        if len(clean_data) < 10:
            logger.warning(f"Insufficient data for outlier detection: {len(clean_data)} points")
            return {}
        
        outliers = {}
        
        if method == 'zscore':
            # Z-score method
            z_scores = np.abs((clean_data - clean_data.mean()) / clean_data.std())
            outlier_indices = np.where(z_scores > threshold)[0]
            outliers['zscore'] = {
                'indices': outlier_indices.tolist(),
                'values': clean_data.iloc[outlier_indices].tolist(),
                'count': len(outlier_indices)
            }
        
        elif method == 'iqr':
            # IQR method
            Q1 = clean_data.quantile(0.25)
            Q3 = clean_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outlier_mask = (clean_data < lower_bound) | (clean_data > upper_bound)
            outlier_indices = np.where(outlier_mask)[0]
            outliers['iqr'] = {
                'indices': outlier_indices.tolist(),
                'values': clean_data.iloc[outlier_indices].tolist(),
                'count': len(outlier_indices)
            }
        
        elif method == 'both':
            # Both methods
            outliers = self.detect_outliers(data, 'zscore', threshold)
            iqr_outliers = self.detect_outliers(data, 'iqr')
            outliers.update(iqr_outliers)
        
        logger.info(f"Outlier detection completed: {sum(len(v['indices']) for v in outliers.values())} outliers found")
        return outliers
    
    def get_analysis_summary(self) -> Dict:
        """Get statistical analysis summary"""
        return {
            'total_analyses': len(self.analysis_results),
            'analysis_types': list(self.analysis_results.keys())
        }
