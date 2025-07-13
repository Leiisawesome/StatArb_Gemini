#!/usr/bin/env python3
"""
Sector Rotation and Style Factor Analysis System
Identifies pairs vulnerable to systematic risk and optimizes selection based on sector dynamics
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

class SectorType(Enum):
    """Major sector classifications"""
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIALS = "Financial Services"
    CONSUMER_CYCLICAL = "Consumer Cyclical"
    CONSUMER_DEFENSIVE = "Consumer Defensive"
    INDUSTRIALS = "Industrials"
    ENERGY = "Energy"
    UTILITIES = "Utilities"
    REAL_ESTATE = "Real Estate"
    MATERIALS = "Basic Materials"
    COMMUNICATION = "Communication Services"

class StyleFactor(Enum):
    """Style factor classifications"""
    GROWTH = "Growth"
    VALUE = "Value"
    MOMENTUM = "Momentum"
    QUALITY = "Quality"
    SIZE = "Size"
    VOLATILITY = "Volatility"
    PROFITABILITY = "Profitability"
    LEVERAGE = "Leverage"

@dataclass
class SectorMetrics:
    """Sector performance and rotation metrics"""
    sector: SectorType
    momentum_1m: float
    momentum_3m: float
    momentum_6m: float
    momentum_12m: float
    volatility: float
    sharpe_ratio: float
    relative_strength: float
    rotation_score: float
    trend_strength: float
    
@dataclass
class StyleFactorMetrics:
    """Style factor loadings and exposures"""
    factor: StyleFactor
    loading: float
    exposure: float
    significance: float
    contribution: float
    momentum: float
    
@dataclass
class PairSectorAnalysis:
    """Comprehensive pair sector analysis"""
    pair: Tuple[str, str]
    sector_1: SectorType
    sector_2: SectorType
    sector_correlation: float
    sector_divergence: float
    style_factor_loadings: Dict[StyleFactor, float]
    systematic_risk_score: float
    rotation_vulnerability: float
    diversification_benefit: float
    recommendation: str
    
@dataclass
class SectorRotationSignal:
    """Sector rotation trading signal"""
    timestamp: datetime
    from_sector: SectorType
    to_sector: SectorType
    signal_strength: float
    confidence: float
    duration_estimate: int  # days
    pairs_affected: List[Tuple[str, str]]
    
class SectorRotationAnalyzer:
    """
    Comprehensive sector rotation and style factor analysis system
    
    Analyzes:
    - Sector momentum and rotation patterns
    - Style factor exposures and loadings
    - Pair vulnerability to systematic risk
    - Optimal pair selection based on sector dynamics
    """
    
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
        
        # Sector ETF mappings for analysis
        self.sector_etfs = {
            SectorType.TECHNOLOGY: "XLK",
            SectorType.HEALTHCARE: "XLV", 
            SectorType.FINANCIALS: "XLF",
            SectorType.CONSUMER_CYCLICAL: "XLY",
            SectorType.CONSUMER_DEFENSIVE: "XLP",
            SectorType.INDUSTRIALS: "XLI",
            SectorType.ENERGY: "XLE",
            SectorType.UTILITIES: "XLU",
            SectorType.REAL_ESTATE: "XLRE",
            SectorType.MATERIALS: "XLB",
            SectorType.COMMUNICATION: "XLC"
        }
        
        # Style factor ETF mappings
        self.style_etfs = {
            StyleFactor.GROWTH: "IVW",
            StyleFactor.VALUE: "IVE",
            StyleFactor.MOMENTUM: "MTUM",
            StyleFactor.QUALITY: "QUAL",
            StyleFactor.SIZE: "IJR",  # Small cap
            StyleFactor.VOLATILITY: "USMV",  # Low vol
            StyleFactor.PROFITABILITY: "PROF",
            StyleFactor.LEVERAGE: "SPLV"  # Low leverage
        }
        
        # Common stock sector mappings
        self.stock_sectors = {
            # Technology
            'AAPL': SectorType.TECHNOLOGY, 'MSFT': SectorType.TECHNOLOGY,
            'GOOGL': SectorType.TECHNOLOGY, 'META': SectorType.TECHNOLOGY,
            'NVDA': SectorType.TECHNOLOGY, 'TSLA': SectorType.TECHNOLOGY,
            'AMZN': SectorType.TECHNOLOGY, 'NFLX': SectorType.TECHNOLOGY,
            
            # Healthcare
            'JNJ': SectorType.HEALTHCARE, 'PFE': SectorType.HEALTHCARE,
            'UNH': SectorType.HEALTHCARE, 'ABBV': SectorType.HEALTHCARE,
            
            # Financials
            'JPM': SectorType.FINANCIALS, 'BAC': SectorType.FINANCIALS,
            'WFC': SectorType.FINANCIALS, 'GS': SectorType.FINANCIALS,
            
            # Consumer
            'WMT': SectorType.CONSUMER_DEFENSIVE, 'PG': SectorType.CONSUMER_DEFENSIVE,
            'KO': SectorType.CONSUMER_DEFENSIVE, 'PEP': SectorType.CONSUMER_DEFENSIVE,
            
            # Energy
            'XOM': SectorType.ENERGY, 'CVX': SectorType.ENERGY,
            
            # Industrials
            'BA': SectorType.INDUSTRIALS, 'CAT': SectorType.INDUSTRIALS,
            'MMM': SectorType.INDUSTRIALS, 'HON': SectorType.INDUSTRIALS,
            
            # ETFs and special cases
            'SPY': SectorType.TECHNOLOGY, 'QQQ': SectorType.TECHNOLOGY,
            'IWM': SectorType.TECHNOLOGY, 'TLT': SectorType.FINANCIALS,
            'TMF': SectorType.FINANCIALS, 'TQQQ': SectorType.TECHNOLOGY,
            'TNA': SectorType.TECHNOLOGY, 'UPRO': SectorType.TECHNOLOGY,
            
            # Chinese stocks
            'BABA': SectorType.TECHNOLOGY, 'YINN': SectorType.TECHNOLOGY,
            'VNET': SectorType.TECHNOLOGY, 'GDS': SectorType.TECHNOLOGY
        }
        
        # Cache for market data
        self.market_data_cache = {}
        self.sector_data_cache = {}
        self.style_data_cache = {}
        
    def get_stock_sector(self, symbol: str) -> SectorType:
        """Get sector for a stock symbol"""
        if symbol in self.stock_sectors:
            return self.stock_sectors[symbol]
        
        # Try to get from yfinance if not in our mapping
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            sector = info.get('sector', 'Unknown')
            
            # Map to our sector types
            sector_mapping = {
                'Technology': SectorType.TECHNOLOGY,
                'Healthcare': SectorType.HEALTHCARE,
                'Financial Services': SectorType.FINANCIALS,
                'Consumer Cyclical': SectorType.CONSUMER_CYCLICAL,
                'Consumer Defensive': SectorType.CONSUMER_DEFENSIVE,
                'Industrials': SectorType.INDUSTRIALS,
                'Energy': SectorType.ENERGY,
                'Utilities': SectorType.UTILITIES,
                'Real Estate': SectorType.REAL_ESTATE,
                'Basic Materials': SectorType.MATERIALS,
                'Communication Services': SectorType.COMMUNICATION
            }
            
            return sector_mapping.get(sector, SectorType.TECHNOLOGY)
            
        except Exception as e:
            self.logger.warning(f"Could not determine sector for {symbol}: {e}")
            return SectorType.TECHNOLOGY  # Default
    
    def load_sector_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load sector ETF data for analysis"""
        
        cache_key = f"sectors_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        if cache_key in self.sector_data_cache:
            return self.sector_data_cache[cache_key]
        
        self.logger.info("Loading sector ETF data...")
        
        sector_data = {}
        
        for sector, etf in self.sector_etfs.items():
            try:
                ticker = yf.Ticker(etf)
                data = ticker.history(start=start_date, end=end_date)
                
                if not data.empty:
                    sector_data[sector.value] = data['Close']
                    
            except Exception as e:
                self.logger.warning(f"Failed to load data for {etf}: {e}")
        
        if sector_data:
            df = pd.DataFrame(sector_data)
            df = df.fillna(method='ffill').fillna(method='bfill')
            self.sector_data_cache[cache_key] = df
            return df
        
        return pd.DataFrame()
    
    def load_style_factor_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load style factor ETF data for analysis"""
        
        cache_key = f"styles_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        if cache_key in self.style_data_cache:
            return self.style_data_cache[cache_key]
        
        self.logger.info("Loading style factor ETF data...")
        
        style_data = {}
        
        for factor, etf in self.style_etfs.items():
            try:
                ticker = yf.Ticker(etf)
                data = ticker.history(start=start_date, end=end_date)
                
                if not data.empty:
                    style_data[factor.value] = data['Close']
                    
            except Exception as e:
                self.logger.warning(f"Failed to load data for {etf}: {e}")
        
        if style_data:
            df = pd.DataFrame(style_data)
            df = df.fillna(method='ffill').fillna(method='bfill')
            self.style_data_cache[cache_key] = df
            return df
        
        return pd.DataFrame()
    
    def calculate_sector_metrics(self, sector_data: pd.DataFrame) -> Dict[SectorType, SectorMetrics]:
        """Calculate comprehensive sector performance metrics"""
        
        metrics = {}
        
        for sector_name in sector_data.columns:
            try:
                sector = SectorType(sector_name)
                prices = sector_data[sector_name].dropna()
                
                if len(prices) < 30:
                    continue
                
                # Calculate returns
                returns = prices.pct_change().dropna()
                
                # Momentum calculations
                momentum_1m = (prices.iloc[-1] / prices.iloc[-21] - 1) if len(prices) >= 21 else 0
                momentum_3m = (prices.iloc[-1] / prices.iloc[-63] - 1) if len(prices) >= 63 else 0
                momentum_6m = (prices.iloc[-1] / prices.iloc[-126] - 1) if len(prices) >= 126 else 0
                momentum_12m = (prices.iloc[-1] / prices.iloc[-252] - 1) if len(prices) >= 252 else 0
                
                # Risk metrics
                volatility = returns.std() * np.sqrt(252)
                sharpe_ratio = (returns.mean() * 252) / (volatility + 1e-8)
                
                # Relative strength vs market (using first sector as proxy)
                market_returns = sector_data.iloc[:, 0].pct_change().dropna()
                if len(market_returns) >= len(returns):
                    market_returns = market_returns.iloc[-len(returns):]
                    relative_strength = (returns.mean() - market_returns.mean()) / (returns.std() + 1e-8)
                else:
                    relative_strength = 0
                
                # Rotation score (combination of momentum and relative strength)
                rotation_score = (momentum_3m * 0.4 + momentum_6m * 0.3 + 
                                momentum_12m * 0.2 + relative_strength * 0.1)
                
                # Trend strength (consistency of returns)
                trend_strength = len(returns[returns > 0]) / len(returns) if len(returns) > 0 else 0.5
                
                metrics[sector] = SectorMetrics(
                    sector=sector,
                    momentum_1m=momentum_1m,
                    momentum_3m=momentum_3m,
                    momentum_6m=momentum_6m,
                    momentum_12m=momentum_12m,
                    volatility=volatility,
                    sharpe_ratio=sharpe_ratio,
                    relative_strength=relative_strength,
                    rotation_score=rotation_score,
                    trend_strength=trend_strength
                )
                
            except Exception as e:
                self.logger.warning(f"Error calculating metrics for {sector_name}: {e}")
                continue
        
        return metrics
    
    def calculate_style_factor_loadings(self, stock_data: pd.DataFrame, 
                                      style_data: pd.DataFrame) -> Dict[StyleFactor, StyleFactorMetrics]:
        """Calculate style factor loadings for stocks"""
        
        loadings = {}
        
        # Align data
        common_dates = stock_data.index.intersection(style_data.index)
        if len(common_dates) < 30:
            return loadings
        
        stock_aligned = stock_data.loc[common_dates]
        style_aligned = style_data.loc[common_dates]
        
        # Calculate returns
        stock_returns = stock_aligned.pct_change().dropna()
        style_returns = style_aligned.pct_change().dropna()
        
        # Align returns
        common_dates = stock_returns.index.intersection(style_returns.index)
        if len(common_dates) < 20:
            return loadings
        
        stock_returns = stock_returns.loc[common_dates]
        style_returns = style_returns.loc[common_dates]
        
        # Calculate loadings for each style factor
        for factor_name in style_returns.columns:
            try:
                factor = StyleFactor(factor_name)
                
                # Run regression for each stock
                stock_loadings = []
                
                for stock_col in stock_returns.columns:
                    y = stock_returns[stock_col].values
                    x = style_returns[factor_name].values
                    
                    # Remove NaN values
                    mask = ~(np.isnan(y) | np.isnan(x))
                    if np.sum(mask) < 10:
                        continue
                    
                    y_clean = y[mask]
                    x_clean = x[mask]
                    
                    # Calculate correlation and regression
                    correlation = np.corrcoef(x_clean, y_clean)[0, 1]
                    
                    if not np.isnan(correlation):
                        # Simple regression
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
                        stock_loadings.append({
                            'loading': slope,
                            'correlation': correlation,
                            'significance': 1 - p_value,
                            'r_squared': r_value**2
                        })
                
                if stock_loadings:
                    # Aggregate loadings
                    avg_loading = np.mean([l['loading'] for l in stock_loadings])
                    avg_correlation = np.mean([l['correlation'] for l in stock_loadings])
                    avg_significance = np.mean([l['significance'] for l in stock_loadings])
                    avg_r_squared = np.mean([l['r_squared'] for l in stock_loadings])
                    
                    # Calculate factor momentum
                    factor_momentum = (style_returns[factor_name].iloc[-21:].mean() * 252) if len(style_returns) >= 21 else 0
                    
                    # Calculate exposure (loading * current factor momentum)
                    exposure = avg_loading * factor_momentum
                    
                    # Calculate contribution to portfolio risk
                    factor_vol = style_returns[factor_name].std() * np.sqrt(252)
                    contribution = abs(avg_loading) * factor_vol
                    
                    loadings[factor] = StyleFactorMetrics(
                        factor=factor,
                        loading=avg_loading,
                        exposure=exposure,
                        significance=avg_significance,
                        contribution=contribution,
                        momentum=factor_momentum
                    )
                    
            except Exception as e:
                self.logger.warning(f"Error calculating loadings for {factor_name}: {e}")
                continue
        
        return loadings
    
    def analyze_pair_sector_risk(self, pair: Tuple[str, str], 
                               sector_metrics: Dict[SectorType, SectorMetrics],
                               style_loadings: Dict[StyleFactor, StyleFactorMetrics]) -> PairSectorAnalysis:
        """Analyze sector risk for a trading pair"""
        
        symbol1, symbol2 = pair
        
        # Get sectors
        sector1 = self.get_stock_sector(symbol1)
        sector2 = self.get_stock_sector(symbol2)
        
        # Calculate sector correlation
        sector_correlation = self._calculate_sector_correlation(sector1, sector2, sector_metrics)
        
        # Calculate sector divergence (how different the sectors are performing)
        sector_divergence = self._calculate_sector_divergence(sector1, sector2, sector_metrics)
        
        # Get style factor loadings for both stocks
        pair_style_loadings = self._calculate_pair_style_loadings(pair, style_loadings)
        
        # Calculate systematic risk score
        systematic_risk = self._calculate_systematic_risk_score(
            sector1, sector2, sector_metrics, pair_style_loadings
        )
        
        # Calculate rotation vulnerability
        rotation_vulnerability = self._calculate_rotation_vulnerability(
            sector1, sector2, sector_metrics
        )
        
        # Calculate diversification benefit
        diversification_benefit = self._calculate_diversification_benefit(
            sector_correlation, sector_divergence, pair_style_loadings
        )
        
        # Generate recommendation
        recommendation = self._generate_pair_recommendation(
            systematic_risk, rotation_vulnerability, diversification_benefit
        )
        
        return PairSectorAnalysis(
            pair=pair,
            sector_1=sector1,
            sector_2=sector2,
            sector_correlation=sector_correlation,
            sector_divergence=sector_divergence,
            style_factor_loadings=pair_style_loadings,
            systematic_risk_score=systematic_risk,
            rotation_vulnerability=rotation_vulnerability,
            diversification_benefit=diversification_benefit,
            recommendation=recommendation
        )
    
    def _calculate_sector_correlation(self, sector1: SectorType, sector2: SectorType,
                                    sector_metrics: Dict[SectorType, SectorMetrics]) -> float:
        """Calculate correlation between two sectors"""
        
        if sector1 == sector2:
            return 1.0
        
        if sector1 not in sector_metrics or sector2 not in sector_metrics:
            return 0.5  # Default moderate correlation
        
        # Use momentum correlations as proxy
        metrics1 = sector_metrics[sector1]
        metrics2 = sector_metrics[sector2]
        
        # Calculate correlation based on momentum patterns
        momentum_corr = np.corrcoef([
            [metrics1.momentum_1m, metrics1.momentum_3m, metrics1.momentum_6m, metrics1.momentum_12m],
            [metrics2.momentum_1m, metrics2.momentum_3m, metrics2.momentum_6m, metrics2.momentum_12m]
        ])[0, 1]
        
        return momentum_corr if not np.isnan(momentum_corr) else 0.5
    
    def _calculate_sector_divergence(self, sector1: SectorType, sector2: SectorType,
                                   sector_metrics: Dict[SectorType, SectorMetrics]) -> float:
        """Calculate how much sectors are diverging"""
        
        if sector1 not in sector_metrics or sector2 not in sector_metrics:
            return 0.0
        
        metrics1 = sector_metrics[sector1]
        metrics2 = sector_metrics[sector2]
        
        # Calculate divergence in rotation scores
        rotation_divergence = abs(metrics1.rotation_score - metrics2.rotation_score)
        
        # Calculate divergence in momentum
        momentum_divergence = abs(metrics1.momentum_3m - metrics2.momentum_3m)
        
        # Calculate divergence in relative strength
        strength_divergence = abs(metrics1.relative_strength - metrics2.relative_strength)
        
        # Combined divergence score
        total_divergence = (rotation_divergence * 0.4 + 
                          momentum_divergence * 0.4 + 
                          strength_divergence * 0.2)
        
        return total_divergence
    
    def _calculate_pair_style_loadings(self, pair: Tuple[str, str],
                                     style_loadings: Dict[StyleFactor, StyleFactorMetrics]) -> Dict[StyleFactor, float]:
        """Calculate style factor loadings for a pair"""
        
        # For simplicity, return the average loadings
        # In practice, you'd calculate loadings for each stock separately
        
        pair_loadings = {}
        
        for factor, metrics in style_loadings.items():
            # Use the loading as pair loading (simplified)
            pair_loadings[factor] = metrics.loading
        
        return pair_loadings
    
    def _calculate_systematic_risk_score(self, sector1: SectorType, sector2: SectorType,
                                       sector_metrics: Dict[SectorType, SectorMetrics],
                                       style_loadings: Dict[StyleFactor, float]) -> float:
        """Calculate systematic risk score for the pair"""
        
        risk_score = 0.0
        
        # Sector risk component
        if sector1 == sector2:
            risk_score += 0.3  # Same sector = higher systematic risk
        
        # Sector volatility risk
        if sector1 in sector_metrics:
            risk_score += sector_metrics[sector1].volatility * 0.2
        
        if sector2 in sector_metrics:
            risk_score += sector_metrics[sector2].volatility * 0.2
        
        # Style factor risk
        for factor, loading in style_loadings.items():
            risk_score += abs(loading) * 0.1
        
        return min(risk_score, 1.0)  # Cap at 1.0
    
    def _calculate_rotation_vulnerability(self, sector1: SectorType, sector2: SectorType,
                                        sector_metrics: Dict[SectorType, SectorMetrics]) -> float:
        """Calculate vulnerability to sector rotation"""
        
        vulnerability = 0.0
        
        # Same sector pairs are more vulnerable
        if sector1 == sector2:
            vulnerability += 0.4
        
        # High momentum sectors are more vulnerable to rotation
        if sector1 in sector_metrics:
            vulnerability += abs(sector_metrics[sector1].rotation_score) * 0.3
        
        if sector2 in sector_metrics:
            vulnerability += abs(sector_metrics[sector2].rotation_score) * 0.3
        
        return min(vulnerability, 1.0)
    
    def _calculate_diversification_benefit(self, sector_correlation: float,
                                         sector_divergence: float,
                                         style_loadings: Dict[StyleFactor, float]) -> float:
        """Calculate diversification benefit of the pair"""
        
        # Lower correlation = higher diversification
        correlation_benefit = (1 - abs(sector_correlation)) * 0.4
        
        # Higher divergence = higher diversification
        divergence_benefit = sector_divergence * 0.3
        
        # Style factor diversification
        style_benefit = 0.0
        if len(style_loadings) > 0:
            # Lower average absolute loading = more diversified
            avg_loading = np.mean([abs(loading) for loading in style_loadings.values()])
            style_benefit = (1 - min(avg_loading, 1.0)) * 0.3
        
        total_benefit = correlation_benefit + divergence_benefit + style_benefit
        
        return min(total_benefit, 1.0)
    
    def _generate_pair_recommendation(self, systematic_risk: float,
                                    rotation_vulnerability: float,
                                    diversification_benefit: float) -> str:
        """Generate trading recommendation for the pair"""
        
        # Calculate overall score
        score = diversification_benefit - (systematic_risk * 0.6 + rotation_vulnerability * 0.4)
        
        if score > 0.3:
            return "STRONG BUY - Excellent diversification with low systematic risk"
        elif score > 0.1:
            return "BUY - Good diversification benefits"
        elif score > -0.1:
            return "HOLD - Moderate systematic risk"
        elif score > -0.3:
            return "CAUTION - Higher systematic risk, monitor closely"
        else:
            return "AVOID - High systematic risk and rotation vulnerability"
    
    def detect_sector_rotation_signals(self, sector_metrics: Dict[SectorType, SectorMetrics]) -> List[SectorRotationSignal]:
        """Detect sector rotation signals"""
        
        signals = []
        
        # Sort sectors by rotation score
        sorted_sectors = sorted(sector_metrics.items(), 
                              key=lambda x: x[1].rotation_score, 
                              reverse=True)
        
        # Look for strong rotation signals
        for i, (sector, metrics) in enumerate(sorted_sectors):
            
            # Strong momentum with trend consistency
            if (metrics.rotation_score > 0.15 and 
                metrics.trend_strength > 0.6 and 
                metrics.momentum_3m > 0.05):
                
                # Find sectors to rotate from (weak performers)
                for j, (weak_sector, weak_metrics) in enumerate(sorted_sectors[-3:]):
                    if (weak_metrics.rotation_score < -0.1 and 
                        weak_metrics.trend_strength < 0.4):
                        
                        # Calculate signal strength
                        signal_strength = (metrics.rotation_score - weak_metrics.rotation_score) / 2
                        
                        # Calculate confidence
                        confidence = (metrics.trend_strength + (1 - weak_metrics.trend_strength)) / 2
                        
                        # Estimate duration based on momentum
                        duration = max(30, min(90, int(abs(metrics.momentum_3m) * 200)))
                        
                        signal = SectorRotationSignal(
                            timestamp=datetime.now(),
                            from_sector=weak_sector,
                            to_sector=sector,
                            signal_strength=signal_strength,
                            confidence=confidence,
                            duration_estimate=duration,
                            pairs_affected=[]  # Would be populated with actual pairs
                        )
                        
                        signals.append(signal)
        
        return signals
    
    def run_comprehensive_analysis(self, pairs: List[Tuple[str, str]], 
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, any]:
        """Run comprehensive sector rotation analysis"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=self.lookback_days)
        if end_date is None:
            end_date = datetime.now()
        
        self.logger.info(f"Running sector rotation analysis for {len(pairs)} pairs")
        
        # Load market data
        sector_data = self.load_sector_data(start_date, end_date)
        style_data = self.load_style_factor_data(start_date, end_date)
        
        # Calculate sector metrics
        sector_metrics = self.calculate_sector_metrics(sector_data)
        
        # Calculate style factor loadings (simplified for demo)
        style_loadings = {}
        if not style_data.empty:
            # Create dummy stock data for style analysis
            dummy_stock_data = pd.DataFrame({
                'STOCK1': sector_data.iloc[:, 0] * (1 + np.random.normal(0, 0.1, len(sector_data))),
                'STOCK2': sector_data.iloc[:, 1] * (1 + np.random.normal(0, 0.1, len(sector_data)))
            }, index=sector_data.index)
            
            style_loadings = self.calculate_style_factor_loadings(dummy_stock_data, style_data)
        
        # Analyze each pair
        pair_analyses = []
        for pair in pairs:
            try:
                analysis = self.analyze_pair_sector_risk(pair, sector_metrics, style_loadings)
                pair_analyses.append(analysis)
            except Exception as e:
                self.logger.warning(f"Error analyzing pair {pair}: {e}")
                continue
        
        # Detect rotation signals
        rotation_signals = self.detect_sector_rotation_signals(sector_metrics)
        
        # Generate summary statistics
        summary = self._generate_analysis_summary(pair_analyses, sector_metrics, rotation_signals)
        
        return {
            'sector_metrics': sector_metrics,
            'style_loadings': style_loadings,
            'pair_analyses': pair_analyses,
            'rotation_signals': rotation_signals,
            'summary': summary,
            'timestamp': datetime.now()
        }
    
    def _generate_analysis_summary(self, pair_analyses: List[PairSectorAnalysis],
                                 sector_metrics: Dict[SectorType, SectorMetrics],
                                 rotation_signals: List[SectorRotationSignal]) -> Dict[str, any]:
        """Generate analysis summary"""
        
        if not pair_analyses:
            return {'error': 'No pair analyses available'}
        
        # Pair statistics
        avg_systematic_risk = np.mean([p.systematic_risk_score for p in pair_analyses])
        avg_rotation_vulnerability = np.mean([p.rotation_vulnerability for p in pair_analyses])
        avg_diversification_benefit = np.mean([p.diversification_benefit for p in pair_analyses])
        
        # Recommendation distribution
        recommendations = [p.recommendation for p in pair_analyses]
        recommendation_counts = {rec: recommendations.count(rec) for rec in set(recommendations)}
        
        # Sector performance
        best_sectors = sorted(sector_metrics.items(), 
                            key=lambda x: x[1].rotation_score, 
                            reverse=True)[:3]
        
        worst_sectors = sorted(sector_metrics.items(), 
                             key=lambda x: x[1].rotation_score)[:3]
        
        return {
            'total_pairs_analyzed': len(pair_analyses),
            'average_systematic_risk': avg_systematic_risk,
            'average_rotation_vulnerability': avg_rotation_vulnerability,
            'average_diversification_benefit': avg_diversification_benefit,
            'recommendation_distribution': recommendation_counts,
            'rotation_signals_detected': len(rotation_signals),
            'best_performing_sectors': [(s[0].value, s[1].rotation_score) for s in best_sectors],
            'worst_performing_sectors': [(s[0].value, s[1].rotation_score) for s in worst_sectors],
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def generate_sector_rotation_report(self, analysis_results: Dict[str, any]) -> str:
        """Generate comprehensive sector rotation report"""
        
        report = f"""
=== SECTOR ROTATION ANALYSIS REPORT ===

Analysis Date: {analysis_results['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

EXECUTIVE SUMMARY:
- Total Pairs Analyzed: {analysis_results['summary']['total_pairs_analyzed']}
- Average Systematic Risk: {analysis_results['summary']['average_systematic_risk']:.2%}
- Average Rotation Vulnerability: {analysis_results['summary']['average_rotation_vulnerability']:.2%}
- Average Diversification Benefit: {analysis_results['summary']['average_diversification_benefit']:.2%}
- Rotation Signals Detected: {analysis_results['summary']['rotation_signals_detected']}

SECTOR PERFORMANCE RANKINGS:
Best Performing Sectors:
"""
        
        for sector, score in analysis_results['summary']['best_performing_sectors']:
            report += f"  {sector}: {score:.2%}\n"
        
        report += "\nWorst Performing Sectors:\n"
        for sector, score in analysis_results['summary']['worst_performing_sectors']:
            report += f"  {sector}: {score:.2%}\n"
        
        report += f"""
PAIR RECOMMENDATIONS:
"""
        
        for rec, count in analysis_results['summary']['recommendation_distribution'].items():
            report += f"  {rec}: {count} pairs\n"
        
        report += f"""
DETAILED PAIR ANALYSIS:
"""
        
        for analysis in analysis_results['pair_analyses'][:10]:  # Top 10
            report += f"""
Pair: {analysis.pair[0]}/{analysis.pair[1]}
  Sectors: {analysis.sector_1.value} / {analysis.sector_2.value}
  Systematic Risk: {analysis.systematic_risk_score:.2%}
  Rotation Vulnerability: {analysis.rotation_vulnerability:.2%}
  Diversification Benefit: {analysis.diversification_benefit:.2%}
  Recommendation: {analysis.recommendation}
"""
        
        if analysis_results['rotation_signals']:
            report += f"""
ACTIVE ROTATION SIGNALS:
"""
            for signal in analysis_results['rotation_signals'][:5]:  # Top 5
                report += f"""
Signal: {signal.from_sector.value} → {signal.to_sector.value}
  Strength: {signal.signal_strength:.2%}
  Confidence: {signal.confidence:.2%}
  Duration: {signal.duration_estimate} days
"""
        
        return report 