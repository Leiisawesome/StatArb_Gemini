"""
Intraday feature engineering for deep dive analysis.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger("core_engine.picker.features")

class IntradayFeatureEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lookback_days = config['features']['lookback_days']

    def compute_features(self, minute_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compute intraday features for each symbol using optimized numpy operations.
        
        Args:
            minute_data: Dict mapping symbol -> DataFrame(timestamp, open, high, low, close, volume)
            
        Returns:
            DataFrame indexed by symbol with feature columns
        """
        features = []
        
        for symbol, df in minute_data.items():
            if df.empty or len(df) < 2:
                continue
                
            try:
                # Extract values to numpy for speed
                close = df['close'].values
                high = df['high'].values
                low = df['low'].values
                volume = df['volume'].values
                
                # 1. Realized Volatility (Log returns std dev annualized)
                # minute vol -> annualized (assuming 252 days * 390 minutes)
                log_ret = np.log(close[1:] / close[:-1])
                realized_vol = np.std(log_ret) * np.sqrt(252 * 390)
                
                # 2. Spread Proxy (High - Low) / Close (in bps)
                avg_spread_bps = np.mean((high - low) / close) * 10000
                
                # 3. Liquidity Stability (Coefficient of variation of volume)
                vol_mean = np.mean(volume)
                vol_cv = np.std(volume) / vol_mean if vol_mean > 0 else 999
                
                # 4. Momentum (Cumulative return over period)
                total_ret = (close[-1] / close[0]) - 1
                
                # 5. Gap Risk (Max absolute 1min log return)
                max_jump = np.max(np.abs(log_ret))
                
                # 6. Skewness (Asymmetry of returns)
                if len(log_ret) > 2:
                    diff = log_ret - np.mean(log_ret)
                    std = np.std(log_ret)
                    skew = np.mean(diff**3) / (std**3) if std > 0 else 0
                else:
                    skew = 0

                features.append({
                    'symbol': symbol,
                    'realized_vol': realized_vol,
                    'avg_spread_bps': avg_spread_bps,
                    'liquidity_stability': vol_cv,
                    'momentum': total_ret,
                    'gap_risk': max_jump,
                    'skewness': skew,
                    'count': len(df)
                })
            except Exception as e:
                logger.warning(f"Error computing features for {symbol}: {e}")
                continue
                
        if not features:
            return pd.DataFrame()
            
        return pd.DataFrame(features).set_index('symbol')

    def compute_micro_stability(self, second_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, float]]:
        """
        Compute micro-stability metrics from 1-second bars.
        
        Metrics:
        - jitter: Std dev of 1s log returns (annualized)
        - voids: Percentage of seconds with zero volume
        - micro_score: Combined stability score (0-1, higher is better)
        """
        results = {}
        
        for symbol, df in second_data.items():
            if df.empty or len(df) < 10:
                results[symbol] = {'jitter': 9.99, 'voids': 1.0, 'micro_score': 0.0}
                continue
                
            try:
                close = df['close'].values
                volume = df['volume'].values
                
                # 1. Jitter (1s volatility)
                log_ret = np.log(close[1:] / close[:-1])
                # Annualize: 252 days * 6.5 hours * 3600 seconds
                jitter = np.std(log_ret) * np.sqrt(252 * 6.5 * 3600)
                
                # 2. Liquidity Voids (Zero volume bars)
                voids = np.mean(volume == 0)
                
                # 3. Micro Score
                # Penalize high jitter and high voids
                # Thresholds: jitter > 0.5 (50%) is high for 1s, voids > 0.2 is high
                jitter_penalty = np.clip(jitter / 0.5, 0, 1)
                void_penalty = np.clip(voids / 0.2, 0, 1)
                micro_score = 1.0 - (0.7 * jitter_penalty + 0.3 * void_penalty)
                
                results[symbol] = {
                    'jitter': float(jitter),
                    'voids': float(voids),
                    'micro_score': float(np.clip(micro_score, 0, 1))
                }
            except Exception as e:
                logger.warning(f"Error computing micro-stability for {symbol}: {e}")
                results[symbol] = {'jitter': 9.99, 'voids': 1.0, 'micro_score': 0.0}
                
        return results

