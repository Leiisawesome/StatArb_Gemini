"""
Ranking and selection logic with hysteresis.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Set
from sklearn.cluster import KMeans

logger = logging.getLogger("core_engine.picker.ranker")

class Ranker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_count = config['selection']['target_count']
        self.hysteresis = config['selection']['hysteresis']
        self.weights = config['selection']['weights']
        self.cap_thresholds = config['selection'].get('cap_thresholds', {'small_max': 2.0, 'mid_max': 10.0})
        self.regime_policies = config['selection'].get('regime_policies', {})

    def select_universe(self, 
                       candidates_df: pd.DataFrame, 
                       previous_universe: Set[str] = None,
                       regime_label: str = "UNKNOWN",
                       correlation_matrix: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Rank candidates and select the final universe using regime-adaptive bucket policies.
        
        Args:
            candidates_df: DataFrame with columns ['dollar_vol', 'realized_vol', 'avg_spread_bps', 
                          'liquidity_stability', 'market_cap', 'ticker_type', 'sector']
            previous_universe: Set of symbols that were in the universe yesterday.
            regime_label: The canonical MarketRegime label.
            correlation_matrix: Optional pre-computed correlation matrix for candidates.
            
        Returns:
            Dict containing 'symbols' (dict sym->data) and 'diagnostics'
        """
        if candidates_df.empty:
            return {'symbols': {}, 'diagnostics': {}}
            
        previous_universe = previous_universe or set()
        
        # 1. Determine Regime Policy
        policy = self.regime_policies.get(regime_label.lower(), self.regime_policies.get('default', {}))
        weights = policy.get('weights', self.weights)
        buckets = policy.get('buckets', { 'etf': 5, 'large': 5, 'mid': 5, 'small': 5 })
        sector_cap = policy.get('sector_cap', 4)
        corr_threshold = policy.get('correlation_threshold', 0.7)
        corr_penalty = policy.get('correlation_penalty', 0.2)
        
        logger.info(f"Applying selection policy for regime: {regime_label}")
        
        # 2. Normalize Metrics (0-1 scale)
        candidates_df['log_dollar_vol'] = np.log1p(candidates_df['dollar_vol'])
        norm_liq = self._normalize(candidates_df['log_dollar_vol'])
        norm_stab = 1 - self._normalize(candidates_df['realized_vol'])
        norm_eff = 1 - self._normalize(candidates_df['avg_spread_bps'])
        
        momentum_series = candidates_df.get('momentum')
        if momentum_series is None:
            momentum_series = pd.Series(0, index=candidates_df.index)
        norm_mom = self._normalize(momentum_series)

        mr_series = candidates_df.get('mean_reversion')
        if mr_series is None:
            mr_series = pd.Series(0, index=candidates_df.index)
        norm_mr = self._normalize(mr_series)
                      
        # 3. Composite Score
        candidates_df['score'] = (
            weights.get('liquidity', 0.4) * norm_liq +
            weights.get('stability', 0.3) * norm_stab +
            weights.get('efficiency', 0.3) * norm_eff +
            weights.get('momentum', 0.0) * norm_mom +
            weights.get('mean_reversion', 0.0) * norm_mr
        )
        
        # 4. Assign Buckets (Vectorized)
        candidates_df['bucket'] = 'small'
        mcap_bn = candidates_df['market_cap'].fillna(0) / 1_000_000_000
        candidates_df.loc[mcap_bn >= self.cap_thresholds['small_max'], 'bucket'] = 'mid'
        candidates_df.loc[mcap_bn >= self.cap_thresholds['mid_max'], 'bucket'] = 'large'
        candidates_df.loc[candidates_df['ticker_type'] == 'ETF', 'bucket'] = 'etf'
        
        # 5. Rank
        candidates_df['rank'] = candidates_df['score'].rank(ascending=False)
        candidates_df.sort_values('rank', inplace=True)
        
        # 6. Selection with Constraints & Correlation Penalty
        selected = []
        bucket_counts = { 'etf': 0, 'large': 0, 'mid': 0, 'small': 0 }
        sector_counts = {}
        
        def get_corr_penalty(symbol, current_selected):
            if correlation_matrix is None or not current_selected:
                return 0
            if symbol not in correlation_matrix.index:
                return 0
            
            # Check max correlation with any selected symbol
            corrs = correlation_matrix.loc[symbol, current_selected]
            if corrs.max() > corr_threshold:
                return corr_penalty
            return 0

        # Pass 1: Hysteresis
        for symbol, row in candidates_df.iterrows():
            if symbol in previous_universe and row['rank'] <= self.hysteresis['keep_rank_threshold']:
                bucket = row['bucket']
                sector = row['sector']
                
                # Apply correlation penalty to rank check if needed
                penalty = get_corr_penalty(symbol, selected)
                if penalty > 0:
                    # If highly correlated, we might still keep it if it's very high rank
                    if row['rank'] > self.hysteresis['keep_rank_threshold'] / 2:
                        continue

                if bucket_counts[bucket] < buckets.get(bucket, 5) and sector_counts.get(sector, 0) < sector_cap:
                    selected.append(symbol)
                    bucket_counts[bucket] += 1
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        # Pass 2: Fill
        for symbol, row in candidates_df.iterrows():
            if symbol in selected: continue
            if len(selected) >= self.target_count: break
            if row['rank'] > self.hysteresis['enter_rank_threshold']: continue
            
            bucket, sector = row['bucket'], row['sector']
            
            # Correlation Check
            if get_corr_penalty(symbol, selected) > 0:
                continue

            if bucket_counts[bucket] < buckets.get(bucket, 5) and sector_counts.get(sector, 0) < sector_cap:
                selected.append(symbol)
                bucket_counts[bucket] += 1
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
                    
        # Fallback: If we still need symbols, fill them but try to respect bucket limits if possible
        if len(selected) < self.target_count:
            remaining = candidates_df.drop(selected)
            for symbol, row in remaining.iterrows():
                if len(selected) >= self.target_count: break
                bucket, sector = row['bucket'], row['sector']
                # Relaxed constraints: allow bucket overflow but still prefer under-filled buckets
                if bucket_counts[bucket] < buckets.get(bucket, 5) * 2: 
                    selected.append(symbol)
                    bucket_counts[bucket] += 1
            
            # Hard Fallback: Just take the top remaining
            if len(selected) < self.target_count:
                remaining = candidates_df.drop(selected)
                needed = self.target_count - len(selected)
                selected.extend(remaining.index[:needed].tolist())
            
        # 7. Cluster Distribution
        cluster_info = self._get_clusters(candidates_df.loc[selected])
            
        # 8. Diagnostics
        diagnostics = {
            'bucket_fill': bucket_counts,
            'sector_concentration': {k: v for k, v in sector_counts.items() if v > 1},
            'churn': len(set(selected) - previous_universe) / self.target_count if previous_universe else 0,
            'avg_score': float(candidates_df.loc[selected, 'score'].mean()),
            'clusters': cluster_info
        }

        # Format Output
        final_universe = {}
        for sym in selected:
            row = candidates_df.loc[sym]
            final_universe[sym] = {
                'rank': int(row['rank']),
                'score': float(row['score']),
                'bucket': row['bucket'],
                'sector': row['sector'],
                'metrics': {
                    'realized_vol': float(row['realized_vol']),
                    'avg_spread_bps': float(row['avg_spread_bps']),
                    'dollar_vol': float(row['dollar_vol']),
                    'market_cap': float(row.get('market_cap', 0)),
                    'momentum': float(row.get('momentum', 0))
                }
            }
            
        return {'symbols': final_universe, 'diagnostics': diagnostics}

    def _normalize(self, series: pd.Series) -> pd.Series:
        if series.max() == series.min():
            return pd.Series(0.5, index=series.index)
        return (series - series.min()) / (series.max() - series.min())

    def _get_clusters(self, df: pd.DataFrame) -> Dict[str, int]:
        try:
            if len(df) < 5:
                return {}
            X = df[['score', 'realized_vol']].values
            kmeans = KMeans(n_clusters=min(5, len(df)), random_state=42, n_init='auto')
            clusters = kmeans.fit_predict(X)
            return pd.Series(clusters).value_counts().to_dict()
        except Exception as e:
            logger.warning(f"Clustering failed: {e}")
            return {}

