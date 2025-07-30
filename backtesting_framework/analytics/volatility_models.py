#!/usr/bin/env python3
"""
Volatility Models
Phase 3: Advanced Analytics & Optimization - Batch 2
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class VolatilityModels:
    """Advanced volatility modeling and forecasting"""
    
    def __init__(self):
        self.volatility_models = {}
        self.forecast_history = []
        
        logger.info("Initialized VolatilityModels")
    
    def calculate_realized_volatility(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """Calculate realized volatility"""
        
        if len(returns) < window:
            logger.warning(f"Insufficient data for realized volatility: {len(returns)} < {window}")
            return pd.Series()
        
        # Realized volatility as square root of sum of squared returns
        realized_vol = np.sqrt((returns**2).rolling(window=window).sum())
        
        logger.info(f"Realized volatility calculated with window {window}")
        return realized_vol
    
    def calculate_parkinson_volatility(self, high: pd.Series, low: pd.Series, 
                                     window: int = 20) -> pd.Series:
        """Calculate Parkinson volatility estimator"""
        
        if len(high) < window or len(low) < window:
            logger.warning(f"Insufficient data for Parkinson volatility")
            return pd.Series()
        
        # Parkinson volatility formula
        log_hl = np.log(high / low)
        parkinson_vol = np.sqrt((log_hl**2 / (4 * np.log(2))).rolling(window=window).mean())
        
        logger.info(f"Parkinson volatility calculated with window {window}")
        return parkinson_vol
    
    def calculate_garman_klass_volatility(self, open_price: pd.Series, high: pd.Series,
                                        low: pd.Series, close: pd.Series, 
                                        window: int = 20) -> pd.Series:
        """Calculate Garman-Klass volatility estimator"""
        
        if len(open_price) < window:
            logger.warning(f"Insufficient data for Garman-Klass volatility")
            return pd.Series()
        
        # Garman-Klass formula
        log_hl = np.log(high / low)
        log_co = np.log(close / open_price)
        
        gk_vol = np.sqrt((0.5 * log_hl**2 - (2*np.log(2) - 1) * log_co**2).rolling(window=window).mean())
        
        logger.info(f"Garman-Klass volatility calculated with window {window}")
        return gk_vol
    
    def detect_volatility_clustering(self, returns: pd.Series, window: int = 20) -> Dict:
        """Detect volatility clustering patterns"""
        
        if len(returns) < window * 2:
            logger.warning(f"Insufficient data for volatility clustering detection")
            return {}
        
        # Calculate rolling volatility
        rolling_vol = returns.rolling(window=window).std()
        
        # Calculate autocorrelation of volatility
        vol_autocorr = rolling_vol.autocorr(lag=1)
        
        # Detect high volatility periods
        vol_threshold = rolling_vol.quantile(0.8)
        high_vol_periods = (rolling_vol > vol_threshold).sum()
        
        # Calculate volatility persistence
        vol_persistence = self._calculate_volatility_persistence(rolling_vol)
        
        results = {
            'volatility_autocorrelation': vol_autocorr,
            'high_volatility_periods': high_vol_periods,
            'volatility_persistence': vol_persistence,
            'volatility_threshold': vol_threshold,
            'clustering_detected': vol_autocorr > 0.3  # Threshold for clustering
        }
        
        logger.info(f"Volatility clustering analysis completed: autocorr={vol_autocorr:.3f}")
        return results
    
    def forecast_volatility(self, returns: pd.Series, method: str = 'ewm', 
                          forecast_horizon: int = 5) -> Dict:
        """Forecast volatility using various methods"""
        
        if len(returns) < 30:
            logger.warning(f"Insufficient data for volatility forecasting: {len(returns)} points")
            return {}
        
        forecasts = {}
        
        if method == 'ewm':
            # Exponentially weighted moving average
            ewm_vol = returns.ewm(span=20).std()
            forecast = ewm_vol.iloc[-1]  # Use last value as forecast
            forecasts['ewm'] = forecast
        
        elif method == 'garch_simple':
            # Simple GARCH(1,1) approximation
            vol_forecast = self._simple_garch_forecast(returns, forecast_horizon)
            forecasts['garch_simple'] = vol_forecast
        
        elif method == 'rolling':
            # Rolling window forecast
            rolling_vol = returns.rolling(window=20).std()
            forecast = rolling_vol.iloc[-1]
            forecasts['rolling'] = forecast
        
        elif method == 'all':
            # All methods
            forecasts.update(self.forecast_volatility(returns, 'ewm', forecast_horizon))
            forecasts.update(self.forecast_volatility(returns, 'garch_simple', forecast_horizon))
            forecasts.update(self.forecast_volatility(returns, 'rolling', forecast_horizon))
        
        # Store forecast history
        forecast_record = {
            'timestamp': datetime.now(),
            'method': method,
            'forecast_horizon': forecast_horizon,
            'forecasts': forecasts
        }
        self.forecast_history.append(forecast_record)
        
        logger.info(f"Volatility forecasting completed: {len(forecasts)} methods")
        return forecasts
    
    def _calculate_volatility_persistence(self, volatility: pd.Series) -> float:
        """Calculate volatility persistence measure"""
        
        if len(volatility) < 10:
            return 0.0
        
        # Calculate how long high volatility periods last
        high_vol_threshold = volatility.quantile(0.7)
        high_vol_mask = volatility > high_vol_threshold
        
        persistence = 0
        current_duration = 0
        
        for is_high_vol in high_vol_mask:
            if is_high_vol:
                current_duration += 1
            else:
                if current_duration > 0:
                    persistence = max(persistence, current_duration)
                    current_duration = 0
        
        if current_duration > 0:
            persistence = max(persistence, current_duration)
        
        return persistence
    
    def _simple_garch_forecast(self, returns: pd.Series, horizon: int) -> List[float]:
        """Simple GARCH(1,1) volatility forecast"""
        
        # Calculate rolling variance
        rolling_var = returns.rolling(window=20).var()
        
        # Simple GARCH parameters (omega, alpha, beta)
        omega = 0.0001
        alpha = 0.1
        beta = 0.8
        
        # Initial variance
        current_var = rolling_var.iloc[-1] if not rolling_var.empty else 0.01
        
        # Forecast variance
        forecast_var = []
        for i in range(horizon):
            current_var = omega + alpha * returns.iloc[-1]**2 + beta * current_var
            forecast_var.append(np.sqrt(current_var))
        
        return forecast_var
    
    def get_volatility_summary(self) -> Dict:
        """Get volatility modeling summary"""
        return {
            'total_models': len(self.volatility_models),
            'forecast_history_count': len(self.forecast_history),
            'available_methods': ['ewm', 'garch_simple', 'rolling']
        }
