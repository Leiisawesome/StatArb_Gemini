"""
Symbol Characteristic Analyzer

Analyzes symbol characteristics for strategy matching and optimization.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum


class LiquidityCategory(Enum):
    """Liquidity categorization"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class VolatilityCategory(Enum):
    """Volatility categorization"""
    VERY_HIGH = "very_high"  # > 60% annualized
    HIGH = "high"            # 40-60%
    MEDIUM = "medium"        # 20-40%
    LOW = "low"              # 10-20%
    VERY_LOW = "very_low"    # < 10%


class TrendCategory(Enum):
    """Trend strength categorization"""
    STRONG_UP = "strong_up"
    MODERATE_UP = "moderate_up"
    SIDEWAYS = "sideways"
    MODERATE_DOWN = "moderate_down"
    STRONG_DOWN = "strong_down"


@dataclass
class SymbolCharacteristics:
    """Comprehensive symbol characteristics"""
    
    # Identification
    symbol: str
    analysis_date: datetime
    
    # Volatility Metrics
    volatility_annualized: float  # Annualized volatility
    volatility_category: VolatilityCategory
    volatility_percentile: float  # 0-1, vs universe
    intraday_volatility: float    # Average intraday range
    
    # Liquidity Metrics
    avg_daily_volume: float       # Average daily dollar volume
    avg_daily_trades: float       # Average number of trades
    liquidity_score: float        # 0-100 composite score
    liquidity_category: LiquidityCategory
    bid_ask_spread_bps: float     # Average bid-ask spread
    
    # Trend Metrics
    trend_strength: float         # -1 to 1 (negative = downtrend)
    trend_category: TrendCategory
    trend_consistency: float      # 0-1, how consistent
    momentum_score: float         # 0-100
    
    # Correlation Metrics
    market_correlation: float     # Correlation to SPY
    sector_correlation: float     # Avg correlation to sector
    diversification_score: float  # 0-100 (higher = more diverse)
    
    # Market Metrics
    market_cap: Optional[float]   # Market capitalization
    avg_price: float              # Average price over period
    price_stability: float        # 0-1, price consistency
    
    # Statistical Metrics
    returns_skewness: float       # Return distribution skew
    returns_kurtosis: float       # Return distribution tail risk
    max_drawdown: float           # Maximum drawdown
    
    # Quality Scores
    overall_quality_score: float  # 0-100 composite quality
    data_quality_score: float     # 0-100 data completeness
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['volatility_category'] = self.volatility_category.value
        data['liquidity_category'] = self.liquidity_category.value
        data['trend_category'] = self.trend_category.value
        data['analysis_date'] = self.analysis_date.isoformat()
        return data


class SymbolCharacteristicAnalyzer:
    """
    Analyzes symbol characteristics for strategy optimization.
    
    Features:
    - Volatility analysis
    - Liquidity scoring
    - Trend strength assessment
    - Correlation analysis
    - Market metrics
    - Quality scoring
    """
    
    def __init__(self, universe_data: Optional[pd.DataFrame] = None):
        """
        Initialize analyzer.
        
        Args:
            universe_data: Optional universe data for percentile calculations
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.universe_data = universe_data
        self.analysis_cache: Dict[str, SymbolCharacteristics] = {}
        
        self.logger.info("SymbolCharacteristicAnalyzer initialized")
    
    def analyze_symbol(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame] = None,
        market_data: Optional[pd.DataFrame] = None
    ) -> SymbolCharacteristics:
        """
        Perform comprehensive symbol analysis.
        
        Args:
            symbol: Symbol to analyze
            price_data: Price data (must have 'close', 'high', 'low', 'open')
            volume_data: Optional volume/liquidity data
            market_data: Optional market data for correlation
            
        Returns:
            SymbolCharacteristics object
        """
        self.logger.info(f"Analyzing characteristics for {symbol}")
        
        # Calculate volatility metrics
        volatility_metrics = self._calculate_volatility_metrics(price_data)
        
        # Calculate liquidity metrics
        liquidity_metrics = self._calculate_liquidity_metrics(
            symbol, price_data, volume_data
        )
        
        # Calculate trend metrics
        trend_metrics = self._calculate_trend_metrics(price_data)
        
        # Calculate correlation metrics
        correlation_metrics = self._calculate_correlation_metrics(
            price_data, market_data
        )
        
        # Calculate market metrics
        market_metrics = self._calculate_market_metrics(price_data)
        
        # Calculate statistical metrics
        statistical_metrics = self._calculate_statistical_metrics(price_data)
        
        # Calculate quality scores
        quality_scores = self._calculate_quality_scores(
            price_data, volatility_metrics, liquidity_metrics
        )
        
        # Combine into SymbolCharacteristics
        characteristics = SymbolCharacteristics(
            symbol=symbol,
            analysis_date=datetime.now(),
            volatility_annualized=volatility_metrics['annualized'],
            volatility_category=volatility_metrics['category'],
            volatility_percentile=volatility_metrics['percentile'],
            intraday_volatility=volatility_metrics['intraday'],
            avg_daily_volume=liquidity_metrics['avg_daily_volume'],
            avg_daily_trades=liquidity_metrics['avg_daily_trades'],
            liquidity_score=liquidity_metrics['liquidity_score'],
            liquidity_category=liquidity_metrics['category'],
            bid_ask_spread_bps=liquidity_metrics['spread_bps'],
            trend_strength=trend_metrics['strength'],
            trend_category=trend_metrics['category'],
            trend_consistency=trend_metrics['consistency'],
            momentum_score=trend_metrics['momentum_score'],
            market_correlation=correlation_metrics['market_corr'],
            sector_correlation=correlation_metrics['sector_corr'],
            diversification_score=correlation_metrics['diversification'],
            market_cap=market_metrics.get('market_cap'),
            avg_price=market_metrics['avg_price'],
            price_stability=market_metrics['price_stability'],
            returns_skewness=statistical_metrics['skewness'],
            returns_kurtosis=statistical_metrics['kurtosis'],
            max_drawdown=statistical_metrics['max_drawdown'],
            overall_quality_score=quality_scores['overall'],
            data_quality_score=quality_scores['data_quality']
        )
        
        # Cache result
        self.analysis_cache[symbol] = characteristics
        
        self.logger.info(
            f"Analysis complete for {symbol}: "
            f"Vol={characteristics.volatility_category.value}, "
            f"Liq={characteristics.liquidity_category.value}, "
            f"Trend={characteristics.trend_category.value}"
        )
        
        return characteristics
    
    def _calculate_volatility_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate volatility metrics"""
        
        # Calculate returns
        returns = price_data['close'].pct_change().dropna()
        
        # Annualized volatility
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(252)
        
        # Categorize
        if annualized_vol > 0.60:
            category = VolatilityCategory.VERY_HIGH
        elif annualized_vol > 0.40:
            category = VolatilityCategory.HIGH
        elif annualized_vol > 0.20:
            category = VolatilityCategory.MEDIUM
        elif annualized_vol > 0.10:
            category = VolatilityCategory.LOW
        else:
            category = VolatilityCategory.VERY_LOW
        
        # Percentile (vs universe if available)
        percentile = 0.5  # Default
        if self.universe_data is not None:
            # Calculate percentile vs universe
            universe_vols = self.universe_data.get('volatility', [])
            if len(universe_vols) > 0:
                percentile = (universe_vols < annualized_vol).sum() / len(universe_vols)
        
        # Intraday volatility
        if all(col in price_data.columns for col in ['high', 'low']):
            intraday_range = (price_data['high'] - price_data['low']) / price_data['close']
            intraday_vol = intraday_range.mean()
        else:
            intraday_vol = daily_vol
        
        return {
            'annualized': annualized_vol,
            'category': category,
            'percentile': percentile,
            'intraday': intraday_vol
        }
    
    def _calculate_liquidity_metrics(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        volume_data: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Calculate liquidity metrics"""
        
        # Average daily dollar volume
        if 'volume' in price_data.columns:
            dollar_volume = price_data['close'] * price_data['volume']
            avg_daily_volume = dollar_volume.mean()
        else:
            avg_daily_volume = 1_000_000  # Default assumption
        
        # Average daily trades (estimate if not available)
        avg_daily_trades = 1000  # Default
        if volume_data is not None and 'trade_count' in volume_data.columns:
            avg_daily_trades = volume_data['trade_count'].mean()
        
        # Bid-ask spread (estimate based on volume)
        if avg_daily_volume > 10_000_000:
            spread_bps = 2.0  # Very liquid
        elif avg_daily_volume > 1_000_000:
            spread_bps = 5.0  # Liquid
        elif avg_daily_volume > 100_000:
            spread_bps = 10.0  # Medium
        else:
            spread_bps = 25.0  # Illiquid
        
        # Liquidity score (0-100)
        volume_score = min(100, (avg_daily_volume / 1_000_000) * 10)  # $1M = 10 points
        spread_score = max(0, 100 - spread_bps * 2)
        liquidity_score = (volume_score * 0.7 + spread_score * 0.3)
        
        # Categorize
        if liquidity_score >= 80:
            category = LiquidityCategory.VERY_HIGH
        elif liquidity_score >= 60:
            category = LiquidityCategory.HIGH
        elif liquidity_score >= 40:
            category = LiquidityCategory.MEDIUM
        elif liquidity_score >= 20:
            category = LiquidityCategory.LOW
        else:
            category = LiquidityCategory.VERY_LOW
        
        return {
            'avg_daily_volume': avg_daily_volume,
            'avg_daily_trades': avg_daily_trades,
            'spread_bps': spread_bps,
            'liquidity_score': liquidity_score,
            'category': category
        }
    
    def _calculate_trend_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trend metrics"""
        
        # Calculate returns
        returns = price_data['close'].pct_change().dropna()
        
        # Trend strength (using linear regression slope)
        prices = price_data['close'].values
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)
        trend_strength = slope / prices.mean()  # Normalized slope
        
        # Categorize trend
        if trend_strength > 0.001:  # > 0.1% per day
            if trend_strength > 0.002:
                category = TrendCategory.STRONG_UP
            else:
                category = TrendCategory.MODERATE_UP
        elif trend_strength < -0.001:
            if trend_strength < -0.002:
                category = TrendCategory.STRONG_DOWN
            else:
                category = TrendCategory.MODERATE_DOWN
        else:
            category = TrendCategory.SIDEWAYS
        
        # Trend consistency (what % of days follow the trend)
        if trend_strength > 0:
            consistency = (returns > 0).sum() / len(returns)
        elif trend_strength < 0:
            consistency = (returns < 0).sum() / len(returns)
        else:
            consistency = 0.5
        
        # Momentum score (0-100)
        momentum_score = min(100, abs(trend_strength) * 10000)
        
        return {
            'strength': trend_strength,
            'category': category,
            'consistency': consistency,
            'momentum_score': momentum_score
        }
    
    def _calculate_correlation_metrics(
        self,
        price_data: pd.DataFrame,
        market_data: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """Calculate correlation metrics"""
        
        returns = price_data['close'].pct_change().dropna()
        
        # Market correlation
        market_corr = 0.5  # Default
        if market_data is not None and 'close' in market_data.columns:
            market_returns = market_data['close'].pct_change().dropna()
            # Align indices
            common_idx = returns.index.intersection(market_returns.index)
            if len(common_idx) > 20:
                market_corr = returns.loc[common_idx].corr(market_returns.loc[common_idx])
        
        # Sector correlation (estimate)
        sector_corr = market_corr * 0.8  # Typically slightly less than market
        
        # Diversification score (inverse of correlation)
        diversification_score = (1 - abs(market_corr)) * 100
        
        return {
            'market_corr': market_corr,
            'sector_corr': sector_corr,
            'diversification': diversification_score
        }
    
    def _calculate_market_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate market metrics"""
        
        # Average price
        avg_price = price_data['close'].mean()
        
        # Price stability (inverse of coefficient of variation)
        price_std = price_data['close'].std()
        cv = price_std / avg_price if avg_price > 0 else 1.0
        price_stability = 1.0 / (1.0 + cv)
        
        return {
            'market_cap': None,  # Would need external data
            'avg_price': avg_price,
            'price_stability': price_stability
        }
    
    def _calculate_statistical_metrics(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistical metrics"""
        
        returns = price_data['close'].pct_change().dropna()
        
        # Skewness and kurtosis
        skewness = returns.skew()
        kurtosis = returns.kurtosis()
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'skewness': skewness,
            'kurtosis': kurtosis,
            'max_drawdown': abs(max_drawdown)
        }
    
    def _calculate_quality_scores(
        self,
        price_data: pd.DataFrame,
        volatility_metrics: Dict[str, Any],
        liquidity_metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate quality scores"""
        
        # Data quality score
        data_points = len(price_data)
        missing_data = price_data.isnull().sum().sum()
        data_quality = (1 - missing_data / (data_points * len(price_data.columns))) * 100
        
        # Overall quality score
        vol_score = 100 if volatility_metrics['category'] == VolatilityCategory.MEDIUM else 70
        liq_score = liquidity_metrics['liquidity_score']
        
        overall_quality = (
            vol_score * 0.3 +
            liq_score * 0.4 +
            data_quality * 0.3
        )
        
        return {
            'overall': overall_quality,
            'data_quality': data_quality
        }
    
    def analyze_universe(
        self,
        symbols: List[str],
        data_provider: Any
    ) -> Dict[str, SymbolCharacteristics]:
        """
        Analyze multiple symbols.
        
        Args:
            symbols: List of symbols to analyze
            data_provider: Data provider with get_price_data() method
            
        Returns:
            Dictionary mapping symbols to their characteristics
        """
        self.logger.info(f"Analyzing universe of {len(symbols)} symbols")
        
        results = {}
        for symbol in symbols:
            try:
                price_data = data_provider.get_price_data(symbol)
                characteristics = self.analyze_symbol(symbol, price_data)
                results[symbol] = characteristics
            except Exception as e:
                self.logger.error(f"Failed to analyze {symbol}: {e}")
        
        self.logger.info(f"Successfully analyzed {len(results)}/{len(symbols)} symbols")
        
        return results
    
    def filter_by_criteria(
        self,
        characteristics: Dict[str, SymbolCharacteristics],
        min_liquidity_score: float = 40.0,
        min_quality_score: float = 60.0,
        allowed_volatility: Optional[List[VolatilityCategory]] = None
    ) -> List[str]:
        """
        Filter symbols by criteria.
        
        Args:
            characteristics: Dictionary of symbol characteristics
            min_liquidity_score: Minimum liquidity score
            min_quality_score: Minimum quality score
            allowed_volatility: List of allowed volatility categories
            
        Returns:
            List of symbols meeting criteria
        """
        filtered = []
        
        for symbol, char in characteristics.items():
            # Check liquidity
            if char.liquidity_score < min_liquidity_score:
                continue
            
            # Check quality
            if char.overall_quality_score < min_quality_score:
                continue
            
            # Check volatility
            if allowed_volatility and char.volatility_category not in allowed_volatility:
                continue
            
            filtered.append(symbol)
        
        self.logger.info(
            f"Filtered {len(filtered)}/{len(characteristics)} symbols "
            f"meeting criteria"
        )
        
        return filtered


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    sample_data = pd.DataFrame({
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 102,
        'low': np.random.randn(len(dates)).cumsum() + 98,
        'volume': np.random.randint(1000000, 10000000, len(dates))
    }, index=dates)
    
    analyzer = SymbolCharacteristicAnalyzer()
    characteristics = analyzer.analyze_symbol('TEST', sample_data)
    
    print(f"Symbol: {characteristics.symbol}")
    print(f"Volatility: {characteristics.volatility_category.value}")
    print(f"Liquidity: {characteristics.liquidity_category.value}")
    print(f"Trend: {characteristics.trend_category.value}")
    print(f"Quality Score: {characteristics.overall_quality_score:.1f}")

