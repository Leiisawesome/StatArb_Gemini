"""
Ranking and selection logic with hysteresis.
"""
import pandas as pd
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger("core_engine.symbolpicker.ranker")

class Ranker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target_count = config['selection']['target_count']
        self.hysteresis = config['selection']['hysteresis']
        self.weights = config['selection']['weights']

    def select_universe(self, 
                       candidates_df: pd.DataFrame, 
                       previous_universe: Set[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Rank candidates and select the final universe.
        
        Args:
            candidates_df: DataFrame with columns ['dollar_vol', 'realized_vol', 'avg_spread_bps', 'liquidity_stability']
            previous_universe: Set of symbols that were in the universe yesterday.
            
        Returns:
            Dict mapping symbol -> {rank, score, metrics...}
        """
        if candidates_df.empty:
            return {}
            
        previous_universe = previous_universe or set()
        
        # 1. Normalize Metrics (0-1 scale)
        # Higher is better for Score
        
        # Log Dollar Vol (Higher is better)
        import numpy as np
        candidates_df['log_dollar_vol'] = np.log1p(candidates_df['dollar_vol'])
        norm_liq = (candidates_df['log_dollar_vol'] - candidates_df['log_dollar_vol'].min()) / \
                   (candidates_df['log_dollar_vol'].max() - candidates_df['log_dollar_vol'].min())
                   
        # Stability (Lower Vol is better -> Invert)
        norm_stab = 1 - (candidates_df['realized_vol'] - candidates_df['realized_vol'].min()) / \
                       (candidates_df['realized_vol'].max() - candidates_df['realized_vol'].min())
                       
        # Efficiency (Lower Spread is better -> Invert)
        norm_eff = 1 - (candidates_df['avg_spread_bps'] - candidates_df['avg_spread_bps'].min()) / \
                      (candidates_df['avg_spread_bps'].max() - candidates_df['avg_spread_bps'].min())
                      
        # 2. Composite Score
        candidates_df['score'] = (
            self.weights['liquidity'] * norm_liq +
            self.weights['stability'] * norm_stab +
            self.weights['efficiency'] * norm_eff
        )
        
        # 3. Rank
        candidates_df['rank'] = candidates_df['score'].rank(ascending=False)
        candidates_df = candidates_df.sort_values('rank')
        
        # 4. Hysteresis Selection
        selected = []
        
        # Iterate through ranked list
        count = 0
        for symbol, row in candidates_df.iterrows():
            rank = row['rank']
            
            is_incumbent = symbol in previous_universe
            
            # Logic:
            # - If Incumbent: Keep if Rank <= Keep Threshold (25)
            # - If New: Enter if Rank <= Enter Threshold (15)
            # - Hard Stop: Don't exceed target_count + buffer (just target_count for now to be strict)
            
            if len(selected) >= self.target_count:
                break
                
            if is_incumbent:
                if rank <= self.hysteresis['keep_rank_threshold']:
                    selected.append(symbol)
            else:
                if rank <= self.hysteresis['enter_rank_threshold']:
                    selected.append(symbol)
                    
        # Fallback: If we selected too few (strict rules), fill with top remaining ranks
        if len(selected) < self.target_count:
            remaining = [s for s in candidates_df.index if s not in selected]
            needed = self.target_count - len(selected)
            selected.extend(remaining[:needed])
            
        # Format Output
        final_universe = {}
        for sym in selected:
            row = candidates_df.loc[sym]
            final_universe[sym] = {
                'rank': int(row['rank']),
                'score': float(row['score']),
                'metrics': {
                    'realized_vol': float(row['realized_vol']),
                    'avg_spread_bps': float(row['avg_spread_bps']),
                    'dollar_vol': float(row['dollar_vol'])
                }
            }
            
        return final_universe

