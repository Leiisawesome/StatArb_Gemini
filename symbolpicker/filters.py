"""
Coarse filters for daily market data.
"""
import pandas as pd
import logging
from typing import List, Dict, Any

logger = logging.getLogger("core_engine.symbolpicker.filters")

class CoarseFilter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_price = config['filters']['min_price']
        self.min_adv = config['filters']['min_adv_30d']
        self.exclude_tickers = set(config['filters'].get('exclude_tickers', []))

    def filter_universe(self, daily_snapshot: pd.DataFrame) -> List[str]:
        """
        Apply coarse filters to the daily market snapshot.
        
        Args:
            daily_snapshot: DataFrame with columns ['close', 'volume', 'vwap'] 
                          and index 'symbol'.
        
        Returns:
            List of symbol strings that pass the filter.
        """
        if daily_snapshot.empty:
            logger.warning("Daily snapshot is empty. Returning empty list.")
            return []

        # 1. Price Filter
        price_mask = daily_snapshot['close'] >= self.min_price
        
        # 2. Dollar Volume Filter (approximate using today's volume * close)
        # Note: Ideally we want 30d ADV, but for the "Broad Scan" we often just have 
        # the daily snapshot. If we have rolling data, use that. 
        # For now, we use today's Dollar Volume as a proxy or rely on the caller 
        # to provide ADV if available. 
        # Assuming snapshot has 'volume' and 'close'.
        dollar_vol = daily_snapshot['volume'] * daily_snapshot['close']
        liq_mask = dollar_vol >= self.min_adv

        # 3. Ticker Filter (Blacklist & Special Types)
        # Exclude warrants, rights, etc if they leak into the feed (often 5+ chars)
        def is_valid_ticker(symbol: str) -> bool:
            if symbol in self.exclude_tickers:
                return False
            if len(symbol) > 4: # Most common stocks are 1-4 chars. 5 chars often test/warrants
                return False
            return True
        
        # Combine Masks
        valid_rows = daily_snapshot[price_mask & liq_mask]
        
        # Apply Ticker Logic
        candidates = [
            sym for sym in valid_rows.index 
            if is_valid_ticker(str(sym))
        ]
        
        logger.info(f"Coarse Filter: Reduced {len(daily_snapshot)} -> {len(candidates)} candidates.")
        return candidates

