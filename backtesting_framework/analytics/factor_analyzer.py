#!/usr/bin/env python3
"""
Factor Analysis
Phase 3: Advanced Analytics & Optimization - Batch 2
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class FactorAnalyzer:
    """Factor analysis and decomposition"""
    
    def __init__(self):
        self.factor_models = {}
        self.factor_history = []
        
        logger.info("Initialized FactorAnalyzer")
    
    def perform_pca_analysis(self, data: pd.DataFrame, n_components: int = None) -> Dict:
        """Perform Principal Component Analysis"""
        
        if len(data) < 10:
            logger.warning(f"Insufficient data for PCA: {len(data)} points")
            return {}
        
        # Remove NaN values
        clean_data = data.dropna()
        
        if len(clean_data) < 10:
            logger.warning(f"Insufficient clean data for PCA: {len(clean_data)} points")
            return {}
        
        # Standardize data
        data_mean = clean_data.mean()
        data_std = clean_data.std()
        data_scaled = (clean_data - data_mean) / data_std
        
        # Calculate covariance matrix
        cov_matrix = data_scaled.cov()
        
        # Calculate eigenvalues and eigenvectors
        eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
        
        # Sort eigenvalues and eigenvectors in descending order
        idx = eigenvals.argsort()[::-1]
        eigenvals = eigenvals[idx]
        eigenvecs = eigenvecs[:, idx]
        
        # Determine number of components if not specified
        if n_components is None:
            n_components = min(len(clean_data.columns), len(clean_data) - 1)
        
        # Calculate explained variance
        total_variance = eigenvals.sum()
        explained_variance = eigenvals[:n_components] / total_variance
        cumulative_variance = np.cumsum(explained_variance)
        
        # Create factor loadings DataFrame
        factor_loadings = pd.DataFrame(
            eigenvecs[:, :n_components],
            columns=[f'PC{i+1}' for i in range(n_components)],
            index=clean_data.columns
        )
        
        # Find important factors (explaining > 5% variance)
        important_factors = [i for i, var in enumerate(explained_variance) if var > 0.05]
        
        results = {
            'explained_variance': explained_variance.tolist(),
            'cumulative_variance': cumulative_variance.tolist(),
            'factor_loadings': factor_loadings.to_dict(),
            'important_factors': important_factors,
            'n_components': n_components,
            'total_variance_explained': cumulative_variance[-1],
            'components_to_explain_80_percent': np.argmax(cumulative_variance >= 0.8) + 1
        }
        
        # Store factor model
        self.factor_models['pca'] = {
            'results': results,
            'eigenvalues': eigenvals,
            'eigenvectors': eigenvecs
        }
        
        logger.info(f"PCA analysis completed: {n_components} components, {results['total_variance_explained']:.2%} variance explained")
        return results
    
    def calculate_factor_returns(self, data: pd.DataFrame, factor_loadings: pd.DataFrame) -> pd.DataFrame:
        """Calculate factor returns from asset returns"""
        
        # Calculate asset returns
        asset_returns = data.pct_change().dropna()
        
        # Align data
        common_assets = asset_returns.columns.intersection(factor_loadings.index)
        if len(common_assets) < 2:
            logger.warning(f"Insufficient common assets: {len(common_assets)}")
            return pd.DataFrame()
        
        aligned_returns = asset_returns[common_assets]
        aligned_loadings = factor_loadings.loc[common_assets]
        
        # Calculate factor returns using least squares
        factor_returns = pd.DataFrame(index=aligned_returns.index)
        
        for i in range(len(aligned_loadings.columns)):
            factor_name = aligned_loadings.columns[i]
            loadings = aligned_loadings[factor_name]
            
            # Use weighted least squares to estimate factor returns
            factor_return = []
            for t in range(len(aligned_returns)):
                returns_t = aligned_returns.iloc[t]
                valid_mask = ~(returns_t.isna() | loadings.isna())
                
                if valid_mask.sum() > 1:
                    X = loadings[valid_mask].values.reshape(-1, 1)
                    y = returns_t[valid_mask].values
                    
                    try:
                        # Simple linear regression
                        factor_ret = np.linalg.lstsq(X, y, rcond=None)[0][0]
                        factor_return.append(factor_ret)
                    except:
                        factor_return.append(np.nan)
                else:
                    factor_return.append(np.nan)
            
            factor_returns[factor_name] = factor_return
        
        logger.info(f"Factor returns calculated: {len(factor_returns.columns)} factors")
        return factor_returns
    
    def analyze_factor_exposures(self, portfolio_weights: pd.Series, 
                               factor_loadings: pd.DataFrame) -> Dict:
        """Analyze portfolio factor exposures"""
        
        # Align portfolio weights with factor loadings
        common_assets = portfolio_weights.index.intersection(factor_loadings.index)
        if len(common_assets) < 1:
            logger.warning("No common assets between portfolio and factor loadings")
            return {}
        
        aligned_weights = portfolio_weights[common_assets]
        aligned_loadings = factor_loadings.loc[common_assets]
        
        # Calculate factor exposures
        factor_exposures = {}
        for factor in aligned_loadings.columns:
            exposure = (aligned_weights * aligned_loadings[factor]).sum()
            factor_exposures[factor] = exposure
        
        # Calculate factor contribution to risk
        factor_risk_contribution = {}
        total_exposure = sum(abs(exposure) for exposure in factor_exposures.values())
        
        if total_exposure > 0:
            for factor, exposure in factor_exposures.items():
                factor_risk_contribution[factor] = abs(exposure) / total_exposure
        
        results = {
            'factor_exposures': factor_exposures,
            'factor_risk_contribution': factor_risk_contribution,
            'total_factor_exposure': total_exposure,
            'concentration_analysis': {
                'max_exposure': max(factor_exposures.values()) if factor_exposures else 0,
                'min_exposure': min(factor_exposures.values()) if factor_exposures else 0,
                'exposure_std': np.std(list(factor_exposures.values())) if factor_exposures else 0
            }
        }
        
        logger.info(f"Factor exposure analysis completed: {len(factor_exposures)} factors")
        return results
    
    def get_factor_summary(self) -> Dict:
        """Get factor analysis summary"""
        return {
            'total_factor_models': len(self.factor_models),
            'factor_history_count': len(self.factor_history),
            'available_models': list(self.factor_models.keys())
        }
