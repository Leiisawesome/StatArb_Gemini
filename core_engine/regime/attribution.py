"""
Regime-based Performance Attribution.
Extracted from RegimeManager for modularity and specialization.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from ..type_definitions.regime import MarketRegime as RegimeType

logger = logging.getLogger(__name__)

# Import canonical metric functions
try:
    from ..analytics.core_metrics import calculate_max_drawdown
except ImportError:
    def calculate_max_drawdown(returns: pd.Series) -> float:
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        return ((cumulative - running_max) / running_max).min()

class RegimePerformanceAttributor:
    """
    Handles performance attribution by market regime.
    """

    def __init__(self, config: Any = None):
        self.config = config
        self.regime_performance_history: Dict[RegimeType, List[float]] = {}
        logger.info("Regime performance attribution initialized")

    def calculate_regime_attribution(self, portfolio_returns: pd.Series,
                                   regime_history: pd.Series,
                                   benchmark_returns: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        Calculate performance attribution by regime.
        """
        try:
            # Alignment
            common_index = portfolio_returns.index.intersection(regime_history.index)
            if common_index.empty:
                return {}
                
            p_aligned = portfolio_returns.loc[common_index]
            r_aligned = regime_history.loc[common_index]
            b_aligned = benchmark_returns.loc[common_index] if benchmark_returns is not None else pd.Series(0, index=common_index)

            regime_performance = {}
            regime_periods = {}

            # Vectorized grouping for performance
            combined_df = pd.DataFrame({
                'returns': p_aligned,
                'regime': r_aligned,
                'benchmark': b_aligned
            })

            grouped = combined_df.groupby('regime')
            
            for regime_val, group in grouped:
                # Map value back to Enum if necessary
                regime_type = regime_val if isinstance(regime_val, RegimeType) else next((r for r in RegimeType if r.value == regime_val), None)
                if not regime_type or regime_type == RegimeType.UNKNOWN:
                    continue

                rets = group['returns']
                bench = group['benchmark']
                
                stats = {
                    'total_return': (1 + rets).prod() - 1,
                    'annualized_return': rets.mean() * 252,
                    'volatility': rets.std() * np.sqrt(252),
                    'sharpe_ratio': (rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0),
                    'max_drawdown': calculate_max_drawdown(rets),
                    'periods': len(rets),
                    'win_rate': (rets > 0).mean()
                }

                if benchmark_returns is not None:
                    excess = rets - bench
                    stats.update({
                        'alpha': excess.mean() * 252,
                        'beta': np.cov(rets, bench)[0, 1] / np.var(bench) if np.var(bench) > 0 else 1.0
                    })

                regime_performance[regime_type.value] = stats
                regime_periods[regime_type.value] = len(rets)

            # Overall contributions
            total_periods = len(p_aligned)
            regime_contributions = {
                k: {
                    'weight': v['periods'] / total_periods,
                    'return': v['total_return'],
                    'contribution': v['total_return'] * (v['periods'] / total_periods)
                } for k, v in regime_performance.items()
            }

            return {
                'regime_performance': regime_performance,
                'regime_contributions': regime_contributions,
                'total_attribution': sum(c['contribution'] for c in regime_contributions.values()),
                'best_regime': max(regime_performance.keys(), key=lambda k: regime_performance[k]['total_return']) if regime_performance else None
            }

        except Exception as e:
            logger.error(f"Error in regime attribution: {e}", exc_info=True)
            return {}

    def update_history(self, regime: RegimeType, performance: float):
        if regime not in self.regime_performance_history:
            self.regime_performance_history[regime] = []
        self.regime_performance_history[regime].append(performance)
        
        # Maintain rolling window (1 year)
        if len(self.regime_performance_history[regime]) > 252:
            self.regime_performance_history[regime] = self.regime_performance_history[regime][-252:]
