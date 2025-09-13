#!/usr/bin/env python3
"""
Historical Ranking Engine
========================

Comprehensive instrument performance analysis and ranking system
for different strategy/regime combinations with statistical validation.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import asdict
from pathlib import Path
import json
from scipy import stats
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

from .data_types import (
    HistoricalPeriod, MarketDataset, RegimeDetectionResult,
    InstrumentScore, InstrumentRankings, RegimeAnalysisOutput,
    RankingsOutputPaths
)

# Import from existing strategy system
from ..market_condition_analytics import MarketCondition, StrategyType

# Configure logging
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore', category=RuntimeWarning)


class HistoricalRankingEngine:
    """
    Advanced engine for ranking instruments across strategy/regime combinations
    """
    
    def __init__(self, min_sample_size: int = 30, 
                 confidence_level: float = 0.95,
                 enable_parallel_processing: bool = True):
        """
        Initialize the ranking engine
        
        Args:
            min_sample_size: Minimum data points required for reliable ranking
            confidence_level: Confidence level for statistical intervals
            enable_parallel_processing: Whether to use parallel processing
        """
        self.min_sample_size = min_sample_size
        self.confidence_level = confidence_level
        self.enable_parallel_processing = enable_parallel_processing
        
        # Performance calculation parameters
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.trading_days_per_year = 252
        
        # Ranking weights
        self.ranking_weights = {
            'expected_return': 0.3,
            'sharpe_ratio': 0.25,
            'max_drawdown': 0.2,  # Negative weight (lower is better)
            'win_rate': 0.15,
            'regime_consistency': 0.1
        }
        
        # Cache for performance calculations
        self._performance_cache: Dict[str, Dict] = {}
        
        logger.info(f"HistoricalRankingEngine initialized with min_sample_size: {min_sample_size}")
    
    def generate_comprehensive_rankings(self, 
                                      regime_analysis: RegimeAnalysisOutput,
                                      datasets: Dict[str, MarketDataset],
                                      strategies: Optional[List[StrategyType]] = None) -> InstrumentRankings:
        """
        Generate comprehensive instrument rankings across all strategy/regime combinations
        
        Args:
            regime_analysis: Complete regime analysis output
            datasets: Dictionary of period datasets
            strategies: Optional list of strategies (uses all if None)
            
        Returns:
            Complete instrument rankings
        """
        if strategies is None:
            strategies = list(StrategyType)
        
        logger.info(f"Generating rankings for {len(strategies)} strategies across {len(regime_analysis.regime_results)} periods")
        
        # Extract all unique symbols across datasets
        all_symbols = set()
        for dataset in datasets.values():
            all_symbols.update(dataset.symbols)
        
        all_symbols = list(all_symbols)
        logger.info(f"Analyzing {len(all_symbols)} unique symbols")
        
        # Group datasets by detected regime
        regime_datasets = self._group_datasets_by_regime(regime_analysis, datasets)
        
        # Generate rankings for each strategy/regime combination
        strategy_rankings = {}
        ranking_metadata = {
            'generation_timestamp': datetime.now().isoformat(),
            'total_symbols_analyzed': len(all_symbols),
            'total_strategies': len(strategies),
            'total_regimes': len(regime_datasets),
            'min_sample_size': self.min_sample_size,
            'confidence_level': self.confidence_level,
            'ranking_weights': self.ranking_weights
        }
        
        for strategy in strategies:
            strategy_name = strategy.value
            strategy_rankings[strategy_name] = {}
            
            for regime_name, regime_data_list in regime_datasets.items():
                logger.info(f"Processing {strategy_name} strategy for {regime_name} regime")
                
                # Calculate instrument scores for this strategy/regime
                instrument_scores = self._calculate_strategy_regime_scores(
                    strategy, regime_name, regime_data_list, all_symbols
                )
                
                # Sort by composite score (descending)
                instrument_scores.sort(key=lambda x: x.composite_score, reverse=True)
                
                strategy_rankings[strategy_name][regime_name] = instrument_scores
                
                logger.info(
                    f"Ranked {len(instrument_scores)} instruments for "
                    f"{strategy_name}/{regime_name} combination"
                )
        
        # Create comprehensive rankings object
        rankings = InstrumentRankings(
            strategy_rankings=strategy_rankings,
            ranking_metadata=ranking_metadata
        )
        
        # Validate rankings
        self._validate_rankings(rankings)
        
        logger.info(f"Comprehensive rankings generation complete")
        return rankings
    
    def analyze_instrument_performance(self, 
                                     symbol: str,
                                     strategy: StrategyType,
                                     regime_datasets: List[Tuple[str, MarketDataset]]) -> Optional[InstrumentScore]:
        """
        Analyze performance of a specific instrument for a strategy across regime periods
        
        Args:
            symbol: Symbol to analyze
            strategy: Trading strategy to evaluate
            regime_datasets: List of (regime_name, dataset) tuples
            
        Returns:
            Instrument performance score or None if insufficient data
        """
        logger.debug(f"Analyzing performance for {symbol} with {strategy.value} strategy")
        
        # Collect all relevant data points for this symbol
        symbol_data_points = []
        regime_consistency_scores = []
        
        for regime_name, dataset in regime_datasets:
            # Extract data for this symbol
            symbol_data = self._extract_symbol_data(dataset, symbol)
            
            if symbol_data is not None and len(symbol_data) >= 10:  # Minimum data requirement
                # Calculate strategy-specific returns
                strategy_returns = self._calculate_strategy_returns(symbol_data, strategy)
                
                if len(strategy_returns) > 0:
                    symbol_data_points.extend(strategy_returns)
                    
                    # Calculate regime consistency for this period
                    regime_consistency = self._calculate_regime_consistency(
                        strategy_returns, strategy, regime_name
                    )
                    regime_consistency_scores.append(regime_consistency)
        
        # Check if we have sufficient data
        if len(symbol_data_points) < self.min_sample_size:
            logger.debug(f"Insufficient data for {symbol}: {len(symbol_data_points)} < {self.min_sample_size}")
            return None
        
        # Calculate performance metrics
        returns_array = np.array(symbol_data_points)
        
        # Expected return (annualized)
        expected_return = np.mean(returns_array) * self.trading_days_per_year
        
        # Volatility (annualized)
        volatility = np.std(returns_array) * np.sqrt(self.trading_days_per_year)
        
        # Sharpe ratio
        sharpe_ratio = (expected_return - self.risk_free_rate) / volatility if volatility > 0 else 0.0
        
        # Maximum drawdown
        max_drawdown = self._calculate_max_drawdown(returns_array)
        
        # Win rate
        win_rate = np.sum(returns_array > 0) / len(returns_array)
        
        # Average regime consistency
        regime_consistency = np.mean(regime_consistency_scores) if regime_consistency_scores else 0.5
        
        # Market correlation (using overall market proxy)
        market_correlation = self._calculate_market_correlation(symbol_data_points, regime_datasets)
        
        # Calculate confidence intervals
        confidence_interval = self._calculate_confidence_interval(returns_array)
        
        # Calculate composite score
        composite_score = self._calculate_composite_score(
            expected_return, sharpe_ratio, max_drawdown, win_rate, regime_consistency
        )
        
        # Create instrument score
        instrument_score = InstrumentScore(
            symbol=symbol,
            strategy=strategy,
            regime=MarketCondition.HIGH_VOLATILITY,  # Will be set by caller
            expected_return=expected_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            regime_consistency=regime_consistency,
            volatility=volatility,
            correlation_to_market=market_correlation,
            composite_score=composite_score,
            sample_size=len(symbol_data_points),
            confidence_interval=confidence_interval
        )
        
        return instrument_score
    
    def export_detailed_rankings(self, rankings: InstrumentRankings,
                               output_dir: Optional[Path] = None) -> RankingsOutputPaths:
        """
        Export detailed rankings to files
        
        Args:
            rankings: Complete instrument rankings
            output_dir: Optional output directory
            
        Returns:
            Paths to exported files
        """
        if output_dir is None:
            output_dir = Path("outputs/historical_analytics/rankings")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        strategy_files = {}
        
        # Export strategy-specific rankings
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            strategy_file = output_dir / f"rankings_{strategy_name}_{timestamp}.csv"
            
            # Prepare data for CSV export
            csv_data = []
            for regime_name, instruments in regime_rankings.items():
                for instrument in instruments:
                    row = {
                        'strategy': strategy_name,
                        'regime': regime_name,
                        'symbol': instrument.symbol,
                        'rank': len(csv_data) + 1,
                        'composite_score': instrument.composite_score,
                        'expected_return': instrument.expected_return,
                        'sharpe_ratio': instrument.sharpe_ratio,
                        'max_drawdown': instrument.max_drawdown,
                        'win_rate': instrument.win_rate,
                        'regime_consistency': instrument.regime_consistency,
                        'volatility': instrument.volatility,
                        'correlation_to_market': instrument.correlation_to_market,
                        'sample_size': instrument.sample_size
                    }
                    csv_data.append(row)
            
            # Export to CSV
            if csv_data:
                df = pd.DataFrame(csv_data)
                df.to_csv(strategy_file, index=False)
                strategy_files[strategy_name] = strategy_file
                logger.info(f"Exported {strategy_name} rankings to: {strategy_file}")
        
        # Export summary file
        summary_file = output_dir / f"rankings_summary_{timestamp}.json"
        summary_data = {
            'generation_timestamp': rankings.generation_timestamp.isoformat(),
            'ranking_metadata': rankings.ranking_metadata,
            'strategy_summary': {}
        }
        
        # Generate strategy summaries
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            strategy_summary = {
                'total_instruments_ranked': sum(len(instruments) for instruments in regime_rankings.values()),
                'regimes_analyzed': list(regime_rankings.keys()),
                'top_performers': {}
            }
            
            # Get top performer in each regime
            for regime_name, instruments in regime_rankings.items():
                if instruments:
                    top_performer = instruments[0]  # Already sorted by composite score
                    strategy_summary['top_performers'][regime_name] = {
                        'symbol': top_performer.symbol,
                        'composite_score': top_performer.composite_score,
                        'expected_return': top_performer.expected_return,
                        'sharpe_ratio': top_performer.sharpe_ratio
                    }
            
            summary_data['strategy_summary'][strategy_name] = strategy_summary
        
        # Export summary
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        logger.info(f"Exported rankings summary to: {summary_file}")
        
        return RankingsOutputPaths(
            strategy_files=strategy_files,
            summary_file=summary_file,
            timestamp=timestamp
        )
    
    def _group_datasets_by_regime(self, 
                                regime_analysis: RegimeAnalysisOutput,
                                datasets: Dict[str, MarketDataset]) -> Dict[str, List[MarketDataset]]:
        """Group datasets by their detected regime"""
        regime_datasets = {}
        
        for result in regime_analysis.regime_results:
            regime_name = result.detected_regime.value
            period_name = result.period.name
            
            if regime_name not in regime_datasets:
                regime_datasets[regime_name] = []
            
            if period_name in datasets:
                regime_datasets[regime_name].append(datasets[period_name])
        
        return regime_datasets
    
    def _calculate_strategy_regime_scores(self,
                                        strategy: StrategyType,
                                        regime_name: str,
                                        regime_datasets: List[MarketDataset],
                                        symbols: List[str]) -> List[InstrumentScore]:
        """Calculate scores for all instruments in a strategy/regime combination"""
        regime_enum = self._regime_name_to_enum(regime_name)
        instrument_scores = []
        
        # Process instruments in parallel if enabled
        if self.enable_parallel_processing and len(symbols) > 10:
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_symbol = {
                    executor.submit(
                        self._calculate_single_instrument_score,
                        symbol, strategy, regime_enum, regime_datasets
                    ): symbol
                    for symbol in symbols
                }
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        score = future.result()
                        if score is not None:
                            instrument_scores.append(score)
                    except Exception as e:
                        logger.warning(f"Error processing {symbol}: {e}")
        else:
            # Sequential processing
            for symbol in symbols:
                try:
                    score = self._calculate_single_instrument_score(
                        symbol, strategy, regime_enum, regime_datasets
                    )
                    if score is not None:
                        instrument_scores.append(score)
                except Exception as e:
                    logger.warning(f"Error processing {symbol}: {e}")
        
        return instrument_scores
    
    def _calculate_single_instrument_score(self,
                                         symbol: str,
                                         strategy: StrategyType,
                                         regime: MarketCondition,
                                         datasets: List[MarketDataset]) -> Optional[InstrumentScore]:
        """Calculate score for a single instrument"""
        # Convert datasets to the format expected by analyze_instrument_performance
        regime_datasets = [(regime.value, dataset) for dataset in datasets]
        
        # Calculate base score
        score = self.analyze_instrument_performance(symbol, strategy, regime_datasets)
        
        if score is not None:
            # Update regime field
            score.regime = regime
        
        return score
    
    def _extract_symbol_data(self, dataset: MarketDataset, symbol: str) -> Optional[pd.DataFrame]:
        """Extract data for a specific symbol from dataset"""
        if dataset.market_data is None or dataset.market_data.empty:
            return None
        
        if 'symbol' not in dataset.market_data.columns:
            return None
        
        symbol_data = dataset.market_data[dataset.market_data['symbol'] == symbol].copy()
        
        if symbol_data.empty:
            return None
        
        # Sort by timestamp
        if 'timestamp' in symbol_data.columns:
            symbol_data = symbol_data.sort_values('timestamp')
        
        return symbol_data
    
    def _calculate_strategy_returns(self, symbol_data: pd.DataFrame, strategy: StrategyType) -> List[float]:
        """Calculate strategy-specific returns for symbol data"""
        if symbol_data.empty or 'close' not in symbol_data.columns:
            return []
        
        try:
            prices = symbol_data['close'].values
            
            if len(prices) < 2:
                return []
            
            # Calculate basic returns
            returns = np.diff(prices) / prices[:-1]
            
            # Apply strategy-specific logic
            if strategy == StrategyType.MEAN_REVERSION:
                # Mean reversion: profit from reversals
                # Simple implementation: reverse signal when price deviates from mean
                mean_price = np.mean(prices)
                deviations = (prices - mean_price) / mean_price
                
                # Generate signals: buy when below mean, sell when above
                signals = np.where(deviations[:-1] < -0.02, 1, 
                         np.where(deviations[:-1] > 0.02, -1, 0))
                
                strategy_returns = returns * signals
                
            elif strategy == StrategyType.MOMENTUM:
                # Momentum: follow trends
                # Simple momentum: use short-term vs long-term average
                if len(prices) >= 20:
                    short_ma = pd.Series(prices).rolling(5).mean()
                    long_ma = pd.Series(prices).rolling(20).mean()
                    
                    signals = np.where(short_ma[:-1] > long_ma[:-1], 1, -1)
                    signals = np.nan_to_num(signals, 0)
                    
                    strategy_returns = returns * signals[:len(returns)]
                else:
                    # Simple momentum for short series
                    momentum = np.sign(returns)
                    strategy_returns = returns * np.roll(momentum, 1)
                    strategy_returns[0] = 0  # No signal for first return
                    
            elif strategy == StrategyType.PAIRS_TRADING:
                # Pairs trading: assume beta-neutral returns
                # Simplified: reduce correlation with market
                market_beta = self._estimate_market_beta(returns)
                strategy_returns = returns * (1 - min(abs(market_beta), 0.5))
                
            else:
                # Default: use raw returns
                strategy_returns = returns
            
            # Remove any infinite or NaN values
            strategy_returns = strategy_returns[np.isfinite(strategy_returns)]
            
            return strategy_returns.tolist()
            
        except Exception as e:
            logger.warning(f"Error calculating strategy returns: {e}")
            return []
    
    def _calculate_regime_consistency(self, returns: List[float], 
                                    strategy: StrategyType, 
                                    regime_name: str) -> float:
        """Calculate how consistently the strategy performs in this regime"""
        if not returns or len(returns) < 5:
            return 0.5  # Default neutral consistency
        
        returns_array = np.array(returns)
        
        # Calculate consistency metrics
        positive_periods = np.sum(returns_array > 0)
        total_periods = len(returns_array)
        
        # Base consistency: win rate
        win_rate_consistency = positive_periods / total_periods
        
        # Volatility consistency: lower volatility = higher consistency
        returns_std = np.std(returns_array)
        volatility_consistency = max(0, 1 - returns_std * 5)  # Scale volatility penalty
        
        # Regime-specific adjustments
        regime_adjustment = 1.0
        if regime_name == 'high_volatility':
            # In high volatility, expect some inconsistency
            regime_adjustment = 0.9
        elif regime_name == 'low_volatility':
            # In low volatility, expect high consistency
            regime_adjustment = 1.1
        
        # Combined consistency score
        consistency = (win_rate_consistency * 0.6 + volatility_consistency * 0.4) * regime_adjustment
        
        return min(1.0, max(0.0, consistency))
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns"""
        if len(returns) == 0:
            return 0.0
        
        try:
            # Calculate cumulative returns
            cumulative = np.cumprod(1 + returns)
            
            # Calculate running maximum
            running_max = np.maximum.accumulate(cumulative)
            
            # Calculate drawdowns
            drawdowns = (cumulative - running_max) / running_max
            
            # Return maximum drawdown (positive value)
            max_drawdown = abs(np.min(drawdowns))
            
            return min(1.0, max_drawdown)  # Cap at 100%
            
        except Exception as e:
            logger.warning(f"Error calculating max drawdown: {e}")
            return 0.5  # Default moderate drawdown
    
    def _calculate_market_correlation(self, symbol_returns: List[float],
                                    regime_datasets: List[Tuple[str, MarketDataset]]) -> float:
        """Calculate correlation with overall market"""
        if len(symbol_returns) < 10:
            return 0.0
        
        try:
            # Create a simple market proxy from all available data
            market_returns = []
            
            for _, dataset in regime_datasets:
                if dataset.market_data is not None and not dataset.market_data.empty:
                    if 'close' in dataset.market_data.columns:
                        # Calculate market returns (equal-weighted)
                        market_prices = dataset.market_data.groupby('timestamp')['close'].mean()
                        if len(market_prices) > 1:
                            market_rets = market_prices.pct_change().dropna()
                            market_returns.extend(market_rets.tolist())
            
            if len(market_returns) < 10:
                return 0.0
            
            # Calculate correlation (use same length as symbol returns)
            min_length = min(len(symbol_returns), len(market_returns))
            if min_length < 5:
                return 0.0
            
            symbol_subset = np.array(symbol_returns[:min_length])
            market_subset = np.array(market_returns[:min_length])
            
            correlation = np.corrcoef(symbol_subset, market_subset)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating market correlation: {e}")
            return 0.0
    
    def _calculate_confidence_interval(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate confidence interval for expected returns"""
        if len(returns) < 3:
            return {'lower': 0.0, 'upper': 0.0}
        
        try:
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            n = len(returns)
            
            # Calculate confidence interval
            alpha = 1 - self.confidence_level
            t_critical = stats.t.ppf(1 - alpha/2, n - 1)
            
            margin_of_error = t_critical * std_return / np.sqrt(n)
            
            # Annualized confidence interval
            lower_bound = (mean_return - margin_of_error) * self.trading_days_per_year
            upper_bound = (mean_return + margin_of_error) * self.trading_days_per_year
            
            return {
                'lower': lower_bound,
                'upper': upper_bound,
                'margin_of_error': margin_of_error * self.trading_days_per_year
            }
            
        except Exception as e:
            logger.warning(f"Error calculating confidence interval: {e}")
            return {'lower': 0.0, 'upper': 0.0}
    
    def _calculate_composite_score(self, expected_return: float, sharpe_ratio: float,
                                 max_drawdown: float, win_rate: float,
                                 regime_consistency: float) -> float:
        """Calculate composite ranking score"""
        try:
            # Normalize metrics to 0-1 scale
            normalized_return = min(1.0, max(0.0, (expected_return + 0.5) / 1.0))  # -50% to +50% range
            normalized_sharpe = min(1.0, max(0.0, (sharpe_ratio + 2.0) / 4.0))     # -2 to +2 range
            normalized_drawdown = 1.0 - min(1.0, max(0.0, max_drawdown))          # Invert (lower is better)
            normalized_win_rate = win_rate  # Already 0-1
            normalized_consistency = regime_consistency  # Already 0-1
            
            # Apply weights
            weighted_score = (
                normalized_return * self.ranking_weights['expected_return'] +
                normalized_sharpe * self.ranking_weights['sharpe_ratio'] +
                normalized_drawdown * self.ranking_weights['max_drawdown'] +
                normalized_win_rate * self.ranking_weights['win_rate'] +
                normalized_consistency * self.ranking_weights['regime_consistency']
            )
            
            return round(weighted_score, 4)
            
        except Exception as e:
            logger.warning(f"Error calculating composite score: {e}")
            return 0.5
    
    def _estimate_market_beta(self, returns: np.ndarray) -> float:
        """Estimate market beta (simplified)"""
        if len(returns) < 5:
            return 1.0
        
        # Simple proxy: volatility relative to expected market volatility
        returns_vol = np.std(returns) * np.sqrt(252)
        market_vol = 0.20  # Assume 20% market volatility
        
        beta = returns_vol / market_vol
        return min(3.0, max(0.1, beta))  # Cap beta between 0.1 and 3.0
    
    def _regime_name_to_enum(self, regime_name: str) -> MarketCondition:
        """Convert regime name string to MarketCondition enum"""
        regime_mapping = {
            'bull_market': MarketCondition.TRENDING_BULL,
            'bear_market': MarketCondition.TRENDING_BEAR,
            'sideways_market': MarketCondition.SIDEWAYS_RANGE,
            'high_volatility': MarketCondition.HIGH_VOLATILITY,
            'low_volatility': MarketCondition.LOW_VOLATILITY,
            'trending_bull': MarketCondition.TRENDING_BULL,
            'trending_bear': MarketCondition.TRENDING_BEAR,
            'sideways_range': MarketCondition.SIDEWAYS_RANGE,
            'crisis_mode': MarketCondition.CRISIS_MODE,
            'recovery_mode': MarketCondition.RECOVERY_MODE,
            'transition': MarketCondition.TRANSITION
        }
        
        return regime_mapping.get(regime_name, MarketCondition.SIDEWAYS_RANGE)
    
    def _validate_rankings(self, rankings: InstrumentRankings) -> None:
        """Validate the generated rankings"""
        total_instruments = 0
        
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            for regime_name, instruments in regime_rankings.items():
                total_instruments += len(instruments)
                
                # Validate that scores are properly ordered
                for i in range(len(instruments) - 1):
                    if instruments[i].composite_score < instruments[i + 1].composite_score:
                        logger.warning(
                            f"Ranking order issue in {strategy_name}/{regime_name}: "
                            f"Position {i} has lower score than position {i+1}"
                        )
        
        logger.info(f"Ranking validation complete: {total_instruments} total instrument scores")


class RankingAnalytics:
    """
    Advanced analytics for ranking results and performance analysis
    """
    
    def __init__(self):
        pass
    
    def analyze_ranking_stability(self, rankings: InstrumentRankings) -> Dict[str, Any]:
        """Analyze stability of rankings across different regimes"""
        stability_analysis = {
            'cross_regime_stability': {},
            'strategy_consistency': {},
            'regime_specific_insights': {}
        }
        
        # Analyze how consistently instruments rank across regimes
        all_symbols = set()
        for strategy_rankings in rankings.strategy_rankings.values():
            for instruments in strategy_rankings.values():
                all_symbols.update(instrument.symbol for instrument in instruments)
        
        # Calculate cross-regime stability for each symbol
        symbol_stability = {}
        for symbol in all_symbols:
            symbol_rankings = []
            
            for strategy_name, regime_rankings in rankings.strategy_rankings.items():
                for regime_name, instruments in regime_rankings.items():
                    # Find this symbol's rank in this strategy/regime
                    for rank, instrument in enumerate(instruments):
                        if instrument.symbol == symbol:
                            symbol_rankings.append({
                                'strategy': strategy_name,
                                'regime': regime_name,
                                'rank': rank + 1,
                                'score': instrument.composite_score
                            })
                            break
            
            if len(symbol_rankings) > 1:
                # Calculate rank variance as stability measure
                ranks = [r['rank'] for r in symbol_rankings]
                scores = [r['score'] for r in symbol_rankings]
                
                rank_stability = 1.0 / (1.0 + np.std(ranks))  # Higher std = lower stability
                score_stability = 1.0 - np.std(scores)  # Lower std = higher stability
                
                symbol_stability[symbol] = {
                    'rank_stability': rank_stability,
                    'score_stability': max(0, score_stability),
                    'appearances': len(symbol_rankings),
                    'avg_rank': np.mean(ranks),
                    'avg_score': np.mean(scores)
                }
        
        stability_analysis['cross_regime_stability'] = symbol_stability
        
        return stability_analysis
    
    def identify_regime_specialists(self, rankings: InstrumentRankings) -> Dict[str, Any]:
        """Identify instruments that excel in specific regimes"""
        specialists = {
            'regime_champions': {},  # Best in each regime
            'regime_specialists': {},  # Consistently good in specific regimes
            'generalists': []  # Good across multiple regimes
        }
        
        # Find champions (top performer) in each regime
        for strategy_name, regime_rankings in rankings.strategy_rankings.items():
            for regime_name, instruments in regime_rankings.items():
                if instruments:
                    champion = instruments[0]  # Top ranked
                    
                    regime_key = f"{strategy_name}_{regime_name}"
                    specialists['regime_champions'][regime_key] = {
                        'symbol': champion.symbol,
                        'score': champion.composite_score,
                        'expected_return': champion.expected_return,
                        'sharpe_ratio': champion.sharpe_ratio
                    }
        
        return specialists