"""
Pairs Selection for Statistical Arbitrage
==========================================

Professional pairs selection framework for identifying cointegrated pairs.

This module provides:
- Cointegration testing (Engle-Granger)
- Quality scoring and ranking
- Half-life calculation
- ADF stationarity testing
- Correlation analysis

Author: StatArb_Gemini Phase 3.3
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from sklearn.linear_model import LinearRegression
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


@dataclass
class PairQualityMetrics:
    """Quality metrics for a cointegrated pair"""
    
    # Pair identification
    asset1: str
    asset2: str
    
    # Cointegration metrics
    cointegration_pvalue: float
    cointegration_statistic: float
    is_cointegrated: bool
    
    # Statistical properties
    correlation: float
    hedge_ratio: float
    spread_mean: float
    spread_std: float
    
    # Mean reversion properties
    half_life: float  # Days
    mean_reversion_speed: float
    adf_statistic: float
    adf_pvalue: float
    
    # Quality scores
    quality_score: float  # Overall quality (0-100)
    stationarity_score: float
    correlation_score: float
    mean_reversion_score: float
    
    # Trading metrics
    zscore_range: Tuple[float, float]  # (min, max) z-scores observed
    spread_volatility: float
    
    # Metadata
    lookback_days: int
    test_timestamp: datetime


class PairsSelector:
    """
    Professional pairs selection for statistical arbitrage
    
    This class identifies cointegrated pairs using rigorous statistical tests
    and ranks them by trading quality.
    """
    
    def __init__(
        self,
        min_correlation: float = 0.70,
        min_cointegration_pvalue: float = 0.05,
        min_half_life: float = 1.0,  # days
        max_half_life: float = 60.0,  # days
        lookback_days: int = 252,  # 1 year
        use_daily_data: bool = True
    ):
        """
        Initialize pairs selector
        
        Args:
            min_correlation: Minimum correlation threshold
            min_cointegration_pvalue: Maximum p-value for cointegration
            min_half_life: Minimum mean reversion half-life (days)
            max_half_life: Maximum mean reversion half-life (days)
            lookback_days: Historical lookback period
            use_daily_data: Use daily candles (recommended for cointegration)
        """
        self.min_correlation = min_correlation
        self.min_cointegration_pvalue = min_cointegration_pvalue
        self.min_half_life = min_half_life
        self.max_half_life = max_half_life
        self.lookback_days = lookback_days
        self.use_daily_data = use_daily_data
        
        logger.info(f"🔍 PairsSelector initialized:")
        logger.info(f"   Min correlation: {min_correlation:.2f}")
        logger.info(f"   Max cointegration p-value: {min_cointegration_pvalue:.3f}")
        logger.info(f"   Half-life range: {min_half_life}-{max_half_life} days")
        logger.info(f"   Lookback: {lookback_days} days")
    
    def select_pairs(
        self,
        price_data: Dict[str, pd.DataFrame],
        max_pairs: int = 10
    ) -> List[PairQualityMetrics]:
        """
        Select best cointegrated pairs from price data
        
        Args:
            price_data: Dictionary of {symbol: DataFrame} with OHLCV data
            max_pairs: Maximum number of pairs to return
        
        Returns:
            List of PairQualityMetrics, sorted by quality score (best first)
        """
        
        logger.info(f"🔍 Testing {len(price_data)} symbols for cointegration...")
        
        # Resample to daily data if using minute data
        if self.use_daily_data:
            price_data = self._resample_to_daily(price_data)
        
        # Test all possible pairs
        all_pairs = []
        symbols = list(price_data.keys())
        
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                try:
                    metrics = self._test_pair(symbol1, symbol2, price_data)
                    if metrics and metrics.is_cointegrated:
                        all_pairs.append(metrics)
                        logger.info(f"   ✅ {symbol1}-{symbol2}: Quality={metrics.quality_score:.1f}, "
                                  f"p-value={metrics.cointegration_pvalue:.4f}, "
                                  f"corr={metrics.correlation:.3f}")
                except Exception as e:
                    logger.debug(f"   ⚠️  {symbol1}-{symbol2}: Test failed - {e}")
                    continue
        
        # Sort by quality score
        all_pairs.sort(key=lambda x: x.quality_score, reverse=True)
        
        # Return top N pairs
        selected_pairs = all_pairs[:max_pairs]
        
        logger.info(f"📊 Selected {len(selected_pairs)} cointegrated pairs out of "
                   f"{len(symbols)*(len(symbols)-1)//2} tested")
        
        return selected_pairs
    
    def _resample_to_daily(
        self,
        price_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """Resample minute data to daily candles"""
        
        logger.info("   📅 Resampling to daily data for cointegration testing...")
        
        daily_data = {}
        for symbol, df in price_data.items():
            try:
                # Ensure timestamp is in index
                if 'timestamp' in df.columns and df.index.name != 'timestamp':
                    df = df.set_index('timestamp')
                
                # Resample to daily
                daily = df.resample('1D').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
                
                # Keep only last N days
                if len(daily) > self.lookback_days:
                    daily = daily.tail(self.lookback_days)
                
                daily_data[symbol] = daily
                logger.debug(f"      {symbol}: {len(df)} minutes → {len(daily)} days")
                
            except Exception as e:
                logger.warning(f"      ⚠️  Failed to resample {symbol}: {e}")
                continue
        
        return daily_data
    
    def _test_pair(
        self,
        symbol1: str,
        symbol2: str,
        price_data: Dict[str, pd.DataFrame]
    ) -> Optional[PairQualityMetrics]:
        """
        Test a pair for cointegration and calculate quality metrics
        
        Returns:
            PairQualityMetrics if tests pass, None otherwise
        """
        
        # Get price series
        if symbol1 not in price_data or symbol2 not in price_data:
            return None
        
        df1 = price_data[symbol1]
        df2 = price_data[symbol2]
        
        # Align data
        aligned = pd.concat([df1['close'], df2['close']], axis=1, join='inner')
        aligned.columns = [symbol1, symbol2]
        
        if len(aligned) < 50:  # Minimum data requirement
            return None
        
        prices1 = aligned[symbol1].values
        prices2 = aligned[symbol2].values
        
        # 1. Test correlation
        correlation = np.corrcoef(prices1, prices2)[0, 1]
        if abs(correlation) < self.min_correlation:
            return None
        
        # 2. Test cointegration (Engle-Granger)
        try:
            score, pvalue, crit_values = coint(prices1, prices2)
        except Exception as e:
            logger.debug(f"Cointegration test failed for {symbol1}-{symbol2}: {e}")
            return None
        
        if pvalue > self.min_cointegration_pvalue:
            return None
        
        # 3. Calculate hedge ratio (OLS regression)
        X = prices1.reshape(-1, 1)
        y = prices2
        reg = LinearRegression().fit(X, y)
        hedge_ratio = reg.coef_[0]
        
        # 4. Calculate spread
        spread = prices2 - hedge_ratio * prices1
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        
        # 5. Test spread stationarity (ADF test)
        try:
            adf_result = adfuller(spread, maxlag=20)
            adf_statistic = adf_result[0]
            adf_pvalue = adf_result[1]
        except Exception:
            adf_statistic = 0.0
            adf_pvalue = 1.0
        
        # 6. Calculate half-life of mean reversion
        half_life = self._calculate_half_life(spread)
        
        if half_life < self.min_half_life or half_life > self.max_half_life:
            return None  # Mean reversion too fast or too slow
        
        # 7. Calculate mean reversion speed
        mean_reversion_speed = np.log(2) / half_life if half_life > 0 else 0
        
        # 8. Calculate z-scores
        z_scores = (spread - spread_mean) / spread_std
        zscore_range = (float(np.min(z_scores)), float(np.max(z_scores)))
        
        # 9. Calculate quality scores
        stationarity_score = self._score_stationarity(adf_pvalue)
        correlation_score = self._score_correlation(correlation)
        mean_reversion_score = self._score_mean_reversion(half_life)
        
        # Overall quality score (weighted average)
        quality_score = (
            stationarity_score * 0.40 +
            correlation_score * 0.30 +
            mean_reversion_score * 0.30
        )
        
        # Create metrics object
        metrics = PairQualityMetrics(
            asset1=symbol1,
            asset2=symbol2,
            cointegration_pvalue=float(pvalue),
            cointegration_statistic=float(score),
            is_cointegrated=True,
            correlation=float(correlation),
            hedge_ratio=float(hedge_ratio),
            spread_mean=float(spread_mean),
            spread_std=float(spread_std),
            half_life=float(half_life),
            mean_reversion_speed=float(mean_reversion_speed),
            adf_statistic=float(adf_statistic),
            adf_pvalue=float(adf_pvalue),
            quality_score=float(quality_score),
            stationarity_score=float(stationarity_score),
            correlation_score=float(correlation_score),
            mean_reversion_score=float(mean_reversion_score),
            zscore_range=zscore_range,
            spread_volatility=float(spread_std),
            lookback_days=len(aligned),
            test_timestamp=datetime.now()
        )
        
        return metrics
    
    def _calculate_half_life(self, spread: np.ndarray) -> float:
        """
        Calculate half-life of mean reversion using AR(1) model
        
        Half-life = -log(2) / log(lambda)
        where lambda is the AR(1) coefficient
        """
        try:
            # Lag the spread
            spread_lag = spread[:-1]
            spread_ret = spread[1:]
            
            # OLS regression: spread_ret = alpha + beta * spread_lag
            X = np.vstack([np.ones(len(spread_lag)), spread_lag]).T
            beta = np.linalg.lstsq(X, spread_ret, rcond=None)[0][1]
            
            # Half-life calculation
            if beta >= 1 or beta <= 0:
                return 999.0  # No mean reversion
            
            half_life = -np.log(2) / np.log(beta)
            
            return float(half_life)
            
        except Exception:
            return 999.0
    
    def _score_stationarity(self, adf_pvalue: float) -> float:
        """Score spread stationarity (0-100)"""
        # Lower p-value = more stationary = higher score
        if adf_pvalue <= 0.01:
            return 100.0
        elif adf_pvalue <= 0.05:
            return 80.0
        elif adf_pvalue <= 0.10:
            return 60.0
        else:
            return 40.0 * (1.0 - min(adf_pvalue, 1.0))
    
    def _score_correlation(self, correlation: float) -> float:
        """Score correlation strength (0-100)"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.95:
            return 100.0
        elif abs_corr >= 0.85:
            return 90.0
        elif abs_corr >= 0.75:
            return 80.0
        elif abs_corr >= 0.70:
            return 70.0
        else:
            return max(0, abs_corr * 100)
    
    def _score_mean_reversion(self, half_life: float) -> float:
        """Score mean reversion speed (0-100)"""
        # Optimal half-life: 5-20 days
        if 5 <= half_life <= 20:
            return 100.0
        elif 3 <= half_life < 5 or 20 < half_life <= 30:
            return 80.0
        elif 1 <= half_life < 3 or 30 < half_life <= 45:
            return 60.0
        elif half_life < 1:
            return 30.0  # Too fast
        elif half_life <= 60:
            return 40.0  # Getting slow
        else:
            return 20.0  # Too slow
    
    def save_pairs_to_file(
        self,
        pairs: List[PairQualityMetrics],
        filename: str
    ) -> None:
        """Save selected pairs to JSON file"""
        
        import json
        from pathlib import Path
        
        # Convert to serializable format
        pairs_dict = [asdict(pair) for pair in pairs]
        
        # Save to file
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                'selection_timestamp': datetime.now().isoformat(),
                'num_pairs': len(pairs),
                'selection_criteria': {
                    'min_correlation': self.min_correlation,
                    'min_cointegration_pvalue': self.min_cointegration_pvalue,
                    'half_life_range': [self.min_half_life, self.max_half_life],
                    'lookback_days': self.lookback_days
                },
                'pairs': pairs_dict
            }, f, indent=2, default=str)
        
        logger.info(f"💾 Saved {len(pairs)} pairs to {filename}")
    
    @staticmethod
    def load_pairs_from_file(filename: str) -> List[PairQualityMetrics]:
        """Load pairs from JSON file"""
        
        import json
        from pathlib import Path
        
        with open(filename, 'r') as f:
            data = json.load(f)
        
        # Convert back to PairQualityMetrics objects
        pairs = []
        for pair_dict in data['pairs']:
            # Convert test_timestamp string back to datetime
            if isinstance(pair_dict['test_timestamp'], str):
                pair_dict['test_timestamp'] = datetime.fromisoformat(pair_dict['test_timestamp'])
            
            pairs.append(PairQualityMetrics(**pair_dict))
        
        logger.info(f"📂 Loaded {len(pairs)} pairs from {filename}")
        return pairs


def generate_pairs_report(pairs: List[PairQualityMetrics]) -> str:
    """Generate human-readable report of selected pairs"""
    
    report = []
    report.append("=" * 80)
    report.append("COINTEGRATED PAIRS SELECTION REPORT")
    report.append("=" * 80)
    report.append(f"Total Pairs Found: {len(pairs)}")
    report.append(f"Selection Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    for i, pair in enumerate(pairs, 1):
        report.append(f"\n{'='*80}")
        report.append(f"Pair #{i}: {pair.asset1} / {pair.asset2}")
        report.append(f"{'='*80}")
        report.append(f"Quality Score:        {pair.quality_score:.1f}/100")
        report.append(f"")
        report.append(f"Cointegration:")
        report.append(f"  P-value:            {pair.cointegration_pvalue:.4f}")
        report.append(f"  Statistic:          {pair.cointegration_statistic:.4f}")
        report.append(f"  Correlation:        {pair.correlation:.3f}")
        report.append(f"")
        report.append(f"Mean Reversion:")
        report.append(f"  Half-life:          {pair.half_life:.2f} days")
        report.append(f"  Reversion Speed:    {pair.mean_reversion_speed:.4f}")
        report.append(f"  ADF P-value:        {pair.adf_pvalue:.4f}")
        report.append(f"")
        report.append(f"Trading Metrics:")
        report.append(f"  Hedge Ratio:        {pair.hedge_ratio:.4f}")
        report.append(f"  Spread Mean:        {pair.spread_mean:.4f}")
        report.append(f"  Spread Std:         {pair.spread_std:.4f}")
        report.append(f"  Z-score Range:      [{pair.zscore_range[0]:.2f}, {pair.zscore_range[1]:.2f}]")
        report.append(f"")
        report.append(f"Component Scores:")
        report.append(f"  Stationarity:       {pair.stationarity_score:.1f}/100")
        report.append(f"  Correlation:        {pair.correlation_score:.1f}/100")
        report.append(f"  Mean Reversion:     {pair.mean_reversion_score:.1f}/100")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


# Convenience function for quick pair testing
def quick_test_pair(
    symbol1: str,
    symbol2: str,
    price_data: Dict[str, pd.DataFrame],
    lookback_days: int = 252
) -> Optional[PairQualityMetrics]:
    """
    Quick test of a single pair
    
    Args:
        symbol1: First symbol
        symbol2: Second symbol
        price_data: Price data dictionary
        lookback_days: Historical lookback
    
    Returns:
        PairQualityMetrics if cointegrated, None otherwise
    """
    selector = PairsSelector(lookback_days=lookback_days)
    return selector._test_pair(symbol1, symbol2, price_data)
