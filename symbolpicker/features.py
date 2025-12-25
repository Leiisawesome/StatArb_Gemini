"""
Intraday feature engineering for deep dive analysis.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any

logger = logging.getLogger("core_engine.symbolpicker.features")

class IntradayFeatureEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.lookback_days = config['features']['lookback_days']

    def compute_features(self, minute_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compute intraday features for each symbol.
        
        Args:
            minute_data: Dict mapping symbol -> DataFrame(timestamp, open, high, low, close, volume)
            
        Returns:
            DataFrame indexed by symbol with feature columns:
            ['realized_vol', 'avg_spread_bps', 'liquidity_stability']
        """
        features = []
        
        for symbol, df in minute_data.items():
            if df.empty:
                continue
                
            try:
                # 1. Realized Volatility (Log returns std dev annualized)
                # minute vol -> annualized (assuming 252 days * 390 minutes)
                df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
                realized_vol = df['log_ret'].std() * np.sqrt(252 * 390)
                
                # 2. Spread Proxy (High - Low) / Close (in bps)
                # A rough estimate of effective spread/cost
                avg_spread_bps = ((df['high'] - df['low']) / df['close']).mean() * 10000
                
                # 3. Liquidity Stability
                # Coefficient of variation of volume (lower is more stable)
                vol_cv = df['volume'].std() / df['volume'].mean() if df['volume'].mean() > 0 else 999
                
                features.append({
                    'symbol': symbol,
                    'realized_vol': realized_vol,
                    'avg_spread_bps': avg_spread_bps,
                    'liquidity_stability': vol_cv,
                    'count': len(df)
                })
            except Exception as e:
                logger.warning(f"Error computing features for {symbol}: {e}")
                continue
                
        if not features:
            return pd.DataFrame()
            
        return pd.DataFrame(features).set_index('symbol')

