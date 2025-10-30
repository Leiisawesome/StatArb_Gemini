"""
Regime Detection Engine - Market Regime Analyzer
Comprehensive market regime analysis including macro environment assessment,
sector rotation analysis, and multi-asset regime identification
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy import stats

# Import centralized configuration (Rule 1, Section 7)
try:
    from ..config.component_config import RegimeConfig
except ImportError:
    RegimeConfig = None

# Import regime components
from .regime_detector import RegimeType

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MacroRegime(Enum):
    """Macro economic regimes"""
    EXPANSION = "expansion"
    RECESSION = "recession"
    RECOVERY = "recovery"
    STAGFLATION = "stagflation"
    DEFLATION = "deflation"
    INFLATION = "inflation"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CREDIT_EXPANSION = "credit_expansion"
    UNKNOWN = "unknown"


class MarketCycle(Enum):
    """Market cycle phases"""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    CONSOLIDATION = "consolidation"
    BREAKOUT = "breakout"
    UNKNOWN = "unknown"


class RiskEnvironment(Enum):
    """Risk environment types"""
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    RISK_NEUTRAL = "risk_neutral"
    FLIGHT_TO_QUALITY = "flight_to_quality"
    CARRY_TRADE = "carry_trade"
    DELEVERAGING = "deleveraging"
    UNKNOWN = "unknown"


@dataclass
class AssetRegimeProfile:
    """Asset-specific regime profile"""
    
    asset_name: str = ""
    current_regime: RegimeType = RegimeType.UNKNOWN
    regime_confidence: float = 0.0
    
    # Asset characteristics in current regime
    volatility: float = 0.0
    correlation_to_market: float = 0.0
    beta: float = 1.0
    momentum: float = 0.0
    
    # Regime stability
    regime_persistence: float = 0.0
    last_regime_change: Optional[datetime] = None
    
    # Risk metrics
    var_95: float = 0.0
    expected_shortfall: float = 0.0
    max_drawdown: float = 0.0
    
    # Factor loadings
    factor_loadings: Dict[str, float] = field(default_factory=dict)
    
    # Relative performance
    relative_strength: float = 0.0
    sector_rotation_signal: float = 0.0


@dataclass
class CrossAssetRegime:
    """Cross-asset regime analysis"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Regime classifications
    equity_regime: RegimeType = RegimeType.UNKNOWN
    fixed_income_regime: RegimeType = RegimeType.UNKNOWN
    commodity_regime: RegimeType = RegimeType.UNKNOWN
    currency_regime: RegimeType = RegimeType.UNKNOWN
    
    # Macro regime assessment
    macro_regime: MacroRegime = MacroRegime.UNKNOWN
    market_cycle: MarketCycle = MarketCycle.UNKNOWN
    risk_environment: RiskEnvironment = RiskEnvironment.UNKNOWN
    
    # Cross-asset relationships
    equity_bond_correlation: float = 0.0
    commodity_dollar_correlation: float = 0.0
    risk_on_off_signal: float = 0.0
    
    # Confidence and quality metrics
    confidence: float = 0.0  # Overall confidence in regime assessment (0-1)
    data_quality: float = 1.0  # Quality of underlying data (0-1)
    regime_strength: float = 0.0  # Strength of regime signals (0-1)
    consensus_score: float = 0.0  # Agreement across different methods (0-1)
    
    # Regime coherence
    regime_alignment: float = 0.0  # How aligned are different asset classes
    regime_stability: float = 0.0   # How stable is the current regime
    
    # Factor analysis
    dominant_factors: Dict[str, float] = field(default_factory=dict)
    factor_variance_explained: float = 0.0
    
    # Stress indicators
    systemic_stress: float = 0.0
    liquidity_stress: float = 0.0
    credit_stress: float = 0.0
    
    # Confidence measures
    analysis_confidence: float = 0.0
    prediction_horizon: int = 20  # Days
    
    # Supporting data
    asset_profiles: Dict[str, AssetRegimeProfile] = field(default_factory=dict)
    correlation_matrix: Optional[pd.DataFrame] = None


class FactorAnalyzer:
    """Analyze market factors and their regime implications"""
    
    def __init__(self, config: Any = None):
        self.config = config
        self.pca = PCA(n_components=self._get_config_attr("n_components_pca", 5))
        self.scaler = StandardScaler()
        self.fitted = False
        
        logger.info("Factor analyzer initialized")
    
    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)
    
    def analyze_factors(self, returns_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze underlying market factors"""
        
        try:
            if len(returns_data) < self._get_config_attr("factor_analysis_window", 252):
                logger.warning("Insufficient data for factor analysis")
                return {}
            
            # Prepare data
            clean_data = returns_data.dropna()
            if len(clean_data.columns) < 3:
                logger.warning("Insufficient assets for factor analysis")
                return {}
            
            # Fit PCA - adjust components to available features
            n_components = min(self._get_config_attr("n_components_pca", 5), len(clean_data.columns))
            if n_components != self.pca.n_components:
                from sklearn.decomposition import PCA
                self.pca = PCA(n_components=n_components)
            
            scaled_data = self.scaler.fit_transform(clean_data)
            pca_result = self.pca.fit_transform(scaled_data)
            
            self.fitted = True
            
            # Analyze factor loadings
            factor_loadings = pd.DataFrame(
                self.pca.components_.T,
                columns=[f'Factor_{i+1}' for i in range(n_components)],
                index=clean_data.columns
            )
            
            # Calculate factor returns
            factor_returns = pd.DataFrame(
                pca_result,
                index=clean_data.index,
                columns=[f'Factor_{i+1}' for i in range(n_components)]
            )
            
            # Analyze factor characteristics
            factor_analysis = {}
            
            for i, factor_name in enumerate(factor_loadings.columns):
                factor_data = factor_returns[factor_name]
                
                factor_analysis[factor_name] = {
                    'variance_explained': self.pca.explained_variance_ratio_[i],
                    'volatility': factor_data.std() * np.sqrt(252),
                    'skewness': factor_data.skew(),
                    'kurtosis': factor_data.kurtosis(),
                    'sharpe_ratio': factor_data.mean() / factor_data.std() * np.sqrt(252) if factor_data.std() > 0 else 0,
                    'max_drawdown': self._calculate_max_drawdown(factor_data),
                    'top_loadings': factor_loadings[factor_name].abs().nlargest(3).to_dict()
                }
            
            # Identify regime-relevant factors
            regime_factors = self._identify_regime_factors(factor_loadings, factor_returns)
            
            return {
                'factor_loadings': factor_loadings,
                'factor_returns': factor_returns,
                'factor_analysis': factor_analysis,
                'regime_factors': regime_factors,
                'total_variance_explained': sum(self.pca.explained_variance_ratio_),
                'factor_correlations': factor_returns.corr()
            }
            
        except Exception as e:
            logger.error(f"Error in factor analysis: {e}")
            return {}
    
    def _identify_regime_factors(self, factor_loadings: pd.DataFrame, 
                               factor_returns: pd.DataFrame) -> Dict[str, Any]:
        """Identify factors most relevant to regime changes"""
        
        try:
            regime_factors = {}
            
            # Analyze factor stability (regime-relevant factors tend to be less stable)
            for factor in factor_returns.columns:
                factor_data = factor_returns[factor]
                
                # Rolling volatility to assess stability
                rolling_vol = factor_data.rolling(20).std()
                vol_stability = 1 - (rolling_vol.std() / rolling_vol.mean()) if rolling_vol.mean() > 0 else 0
                
                # Factor momentum
                momentum = factor_data.rolling(20).mean()
                
                # Regime relevance score
                regime_relevance = (1 - vol_stability) + abs(momentum.iloc[-1])
                
                regime_factors[factor] = {
                    'stability_score': vol_stability,
                    'momentum': momentum.iloc[-1] if len(momentum) > 0 else 0,
                    'regime_relevance': regime_relevance,
                    'volatility_trend': rolling_vol.tail(10).mean() - rolling_vol.head(10).mean()
                }
            
            return regime_factors
            
        except Exception as e:
            logger.error(f"Error identifying regime factors: {e}")
            return {}
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0


class CrossAssetAnalyzer:
    """Analyze cross-asset relationships and regimes"""
    
    def __init__(self, config: Any = None):
        self.config = config
        logger.info("Cross-asset analyzer initialized")
    
    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)
    
    def analyze_cross_asset_regime(self, market_data: Dict[str, pd.DataFrame]) -> CrossAssetRegime:
        """Analyze cross-asset regime"""
        
        try:
            # Extract returns for all assets
            returns_data = self._extract_returns(market_data)
            
            if returns_data.empty:
                return CrossAssetRegime()
            
            # Analyze individual asset regimes
            asset_profiles = self._analyze_asset_regimes(returns_data)
            
            # Analyze cross-asset relationships
            correlations = self._analyze_correlations(returns_data)
            
            # Identify macro regime
            macro_regime = self._identify_macro_regime(returns_data, correlations)
            
            # Assess market cycle
            market_cycle = self._assess_market_cycle(returns_data)
            
            # Determine risk environment
            risk_environment = self._determine_risk_environment(returns_data, correlations)
            
            # Calculate regime coherence
            regime_alignment = self._calculate_regime_alignment(asset_profiles)
            regime_stability = self._calculate_regime_stability(asset_profiles)
            
            # Analyze stress indicators
            stress_indicators = self._analyze_stress_indicators(returns_data, correlations)
            
            # Create cross-asset regime object
            cross_asset_regime = CrossAssetRegime(
                timestamp=datetime.now(),
                macro_regime=macro_regime,
                market_cycle=market_cycle,
                risk_environment=risk_environment,
                regime_alignment=regime_alignment,
                regime_stability=regime_stability,
                asset_profiles=asset_profiles,
                correlation_matrix=correlations,
                **stress_indicators
            )
            
            # Set asset class regimes
            cross_asset_regime = self._set_asset_class_regimes(cross_asset_regime, asset_profiles)
            
            # Calculate confidence metrics
            confidence_metrics = self._calculate_confidence_metrics(
                asset_profiles, regime_alignment, regime_stability, returns_data
            )
            
            # Set confidence attributes
            cross_asset_regime.confidence = confidence_metrics.get('overall_confidence', 0.5)
            cross_asset_regime.data_quality = confidence_metrics.get('data_quality', 1.0)
            cross_asset_regime.regime_strength = confidence_metrics.get('regime_strength', 0.0)
            cross_asset_regime.consensus_score = confidence_metrics.get('consensus_score', 0.0)
            
            return cross_asset_regime
            
        except Exception as e:
            logger.error(f"Error analyzing cross-asset regime: {e}")
            return CrossAssetRegime()
    
    def _calculate_confidence_metrics(self, asset_profiles: Dict, regime_alignment: float, 
                                    regime_stability: float, returns_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive confidence metrics for cross-asset regime analysis"""
        
        try:
            # Data quality assessment
            data_quality = self._assess_data_quality(returns_data)
            
            # Regime strength based on signal clarity
            regime_strength = self._calculate_regime_strength(asset_profiles)
            
            # Consensus score based on agreement across assets
            consensus_score = self._calculate_consensus_score(asset_profiles, regime_alignment)
            
            # Overall confidence (weighted combination)
            overall_confidence = (
                0.3 * data_quality +
                0.3 * regime_strength +
                0.2 * consensus_score +
                0.1 * regime_alignment +
                0.1 * regime_stability
            )
            
            # Ensure confidence is in valid range
            overall_confidence = np.clip(overall_confidence, 0.1, 0.95)
            
            return {
                'overall_confidence': overall_confidence,
                'data_quality': data_quality,
                'regime_strength': regime_strength,
                'consensus_score': consensus_score
            }
            
        except Exception as e:
            logger.error(f"Error calculating confidence metrics: {e}")
            return {
                'overall_confidence': 0.5,
                'data_quality': 1.0,
                'regime_strength': 0.0,
                'consensus_score': 0.0
            }
    
    def _assess_data_quality(self, returns_data: pd.DataFrame) -> float:
        """Assess quality of underlying data"""
        
        if returns_data.empty:
            return 0.0
        
        # Check for missing data
        missing_ratio = returns_data.isnull().sum().sum() / (returns_data.shape[0] * returns_data.shape[1])
        
        # Check for sufficient data points
        min_required_points = 50
        data_sufficiency = min(1.0, len(returns_data) / min_required_points)
        
        # Check for extreme outliers
        outlier_ratio = 0.0
        for col in returns_data.columns:
            z_scores = np.abs(stats.zscore(returns_data[col].dropna()))
            outliers = (z_scores > 3).sum()
            outlier_ratio += outliers / len(returns_data[col].dropna())
        outlier_ratio /= len(returns_data.columns)
        
        # Combine quality metrics
        quality_score = (
            (1 - missing_ratio) * 0.4 +
            data_sufficiency * 0.4 +
            (1 - min(outlier_ratio, 0.2) / 0.2) * 0.2
        )
        
        return np.clip(quality_score, 0.0, 1.0)
    
    def _calculate_regime_strength(self, asset_profiles: Dict) -> float:
        """Calculate strength of regime signals across assets"""
        
        if not asset_profiles:
            return 0.0
        
        strengths = []
        for profile in asset_profiles.values():
            if hasattr(profile, 'regime_confidence'):
                strengths.append(profile.regime_confidence)
            elif hasattr(profile, 'confidence'):
                strengths.append(profile.confidence)
            else:
                strengths.append(0.5)  # Default moderate strength
        
        return np.mean(strengths) if strengths else 0.0
    
    def _calculate_consensus_score(self, asset_profiles: Dict, regime_alignment: float) -> float:
        """Calculate consensus score based on agreement across different assets"""
        
        if not asset_profiles:
            return 0.0
        
        # Use regime alignment as primary consensus measure
        consensus = regime_alignment
        
        # Adjust based on number of assets (more assets = higher confidence if aligned)
        num_assets = len(asset_profiles)
        asset_bonus = min(0.2, (num_assets - 1) * 0.05)  # Bonus up to 0.2 for more assets
        
        consensus = min(1.0, consensus + asset_bonus)
        
        return consensus
    
    def _extract_returns(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract returns from market data"""
        
        try:
            returns_dict = {}
            
            for symbol, data in market_data.items():
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                elif 'price' in data.columns:
                    returns = data['price'].pct_change().dropna()
                else:
                    # Use first numeric column
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        returns = data[numeric_cols[0]].pct_change().dropna()
                    else:
                        continue
                
                returns_dict[symbol] = returns
            
            if not returns_dict:
                return pd.DataFrame()
            
            # Combine into single DataFrame
            returns_df = pd.DataFrame(returns_dict)
            
            # Align dates and remove NaN rows
            returns_df = returns_df.dropna()
            
            return returns_df
            
        except Exception as e:
            logger.error(f"Error extracting returns: {e}")
            return pd.DataFrame()
    
    def _analyze_asset_regimes(self, returns_data: pd.DataFrame) -> Dict[str, AssetRegimeProfile]:
        """Analyze regime for each asset"""
        
        try:
            asset_profiles = {}
            
            # Calculate market benchmark (equal-weighted portfolio)
            market_returns = returns_data.mean(axis=1)
            
            for symbol in returns_data.columns:
                asset_returns = returns_data[symbol]
                
                # Basic statistics
                volatility = asset_returns.std() * np.sqrt(252)
                
                # Correlation to market
                correlation = asset_returns.corr(market_returns)
                
                # Beta calculation
                covariance = np.cov(asset_returns, market_returns)[0, 1]
                market_variance = np.var(market_returns)
                beta = covariance / market_variance if market_variance > 0 else 1.0
                
                # Momentum
                momentum = asset_returns.rolling(20).mean().iloc[-1] if len(asset_returns) >= 20 else 0
                
                # Risk metrics
                var_95 = np.percentile(asset_returns, 5)
                expected_shortfall = asset_returns[asset_returns <= var_95].mean()
                max_drawdown = self._calculate_max_drawdown(asset_returns)
                
                # Relative strength
                relative_strength = (asset_returns.rolling(20).mean() - market_returns.rolling(20).mean()).iloc[-1]
                
                # Simple regime classification based on characteristics
                regime_type = self._classify_asset_regime(volatility, momentum, correlation)
                
                # Create asset profile
                profile = AssetRegimeProfile(
                    asset_name=symbol,
                    current_regime=regime_type,
                    regime_confidence=0.75,  # Default confidence
                    volatility=volatility,
                    correlation_to_market=correlation,
                    beta=beta,
                    momentum=momentum,
                    var_95=var_95,
                    expected_shortfall=expected_shortfall,
                    max_drawdown=max_drawdown,
                    relative_strength=relative_strength
                )
                
                asset_profiles[symbol] = profile
            
            return asset_profiles
            
        except Exception as e:
            logger.error(f"Error analyzing asset regimes: {e}")
            return {}
    
    def _classify_asset_regime(self, volatility: float, momentum: float, correlation: float) -> RegimeType:
        """Classify asset regime based on characteristics"""
        
        try:
            # High volatility regimes
            if volatility > self.config.volatility_percentile_threshold:
                if momentum < -self.config.momentum_threshold:
                    return RegimeType.CRISIS
                else:
                    return RegimeType.HIGH_VOLATILITY
            
            # Low volatility regimes
            elif volatility < 0.15:  # Low volatility threshold
                if momentum > self.config.momentum_threshold:
                    return RegimeType.BULL_MARKET
                elif momentum < -self.config.momentum_threshold:
                    return RegimeType.BEAR_MARKET
                else:
                    return RegimeType.LOW_VOLATILITY
            
            # Medium volatility regimes
            else:
                if momentum > self.config.momentum_threshold:
                    return RegimeType.BULL_MARKET
                elif momentum < -self.config.momentum_threshold:
                    return RegimeType.BEAR_MARKET
                else:
                    return RegimeType.SIDEWAYS
                    
        except Exception as e:
            logger.error(f"Error classifying asset regime: {e}")
            return RegimeType.UNKNOWN
    
    def _analyze_correlations(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """Analyze correlation structure"""
        
        try:
            # Rolling correlation matrix
            correlation_window = min(self._get_config_attr("correlation_window", 60), len(returns_data))
            correlations = returns_data.tail(correlation_window).corr()
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return pd.DataFrame()
    
    def _identify_macro_regime(self, returns_data: pd.DataFrame, 
                             correlations: pd.DataFrame) -> MacroRegime:
        """Identify macro economic regime"""
        
        try:
            # Analyze equity performance
            equity_assets = [asset for asset in returns_data.columns 
                           if asset in self.config.equity_indices]
            
            if equity_assets:
                equity_returns = returns_data[equity_assets].mean(axis=1)
                equity_performance = equity_returns.rolling(60).mean().iloc[-1] * 252
            else:
                equity_performance = 0
            
            # Analyze fixed income performance
            bond_assets = [asset for asset in returns_data.columns 
                          if asset in self.config.fixed_income]
            
            if bond_assets:
                bond_returns = returns_data[bond_assets].mean(axis=1)
                bond_performance = bond_returns.rolling(60).mean().iloc[-1] * 252
            else:
                bond_performance = 0
            
            # Analyze volatility
            if equity_assets:
                equity_vol = returns_data[equity_assets].mean(axis=1).std() * np.sqrt(252)
            else:
                equity_vol = 0
            
            # Macro regime classification
            if equity_performance > 0.1 and equity_vol < 0.2:
                return MacroRegime.EXPANSION
            elif equity_performance < -0.1 and equity_vol > 0.3:
                return MacroRegime.RECESSION
            elif equity_performance > 0 and equity_vol > 0.25:
                return MacroRegime.RECOVERY
            elif equity_performance < 0 and bond_performance < 0:
                return MacroRegime.STAGFLATION
            elif equity_performance < -0.05 and bond_performance > 0.05:
                return MacroRegime.DEFLATION
            else:
                return MacroRegime.UNKNOWN
                
        except Exception as e:
            logger.error(f"Error identifying macro regime: {e}")
            return MacroRegime.UNKNOWN
    
    def _assess_market_cycle(self, returns_data: pd.DataFrame) -> MarketCycle:
        """Assess market cycle phase"""
        
        try:
            # Use equity indices for market cycle assessment
            equity_assets = [asset for asset in returns_data.columns 
                           if asset in self.config.equity_indices]
            
            if not equity_assets:
                return MarketCycle.UNKNOWN
            
            market_returns = returns_data[equity_assets].mean(axis=1)
            
            # Calculate trend measures
            short_ma = market_returns.rolling(20).mean()
            long_ma = market_returns.rolling(60).mean()
            
            # Current trend
            trend_short = short_ma.iloc[-1] - short_ma.iloc[-10] if len(short_ma) >= 10 else 0
            trend_long = long_ma.iloc[-1] - long_ma.iloc[-30] if len(long_ma) >= 30 else 0
            
            # Volatility trend
            volatility = market_returns.rolling(20).std()
            vol_trend = volatility.iloc[-5:].mean() - volatility.iloc[-20:-15].mean()
            
            # Cycle classification
            if trend_short > 0 and trend_long > 0 and vol_trend < 0:
                return MarketCycle.MARKUP
            elif trend_short < 0 and trend_long < 0 and vol_trend > 0:
                return MarketCycle.MARKDOWN
            elif trend_short > 0 and trend_long < 0:
                return MarketCycle.ACCUMULATION
            elif trend_short < 0 and trend_long > 0:
                return MarketCycle.DISTRIBUTION
            elif abs(trend_short) < 0.001 and abs(trend_long) < 0.001:
                return MarketCycle.CONSOLIDATION
            else:
                return MarketCycle.UNKNOWN
                
        except Exception as e:
            logger.error(f"Error assessing market cycle: {e}")
            return MarketCycle.UNKNOWN
    
    def _determine_risk_environment(self, returns_data: pd.DataFrame, 
                                  correlations: pd.DataFrame) -> RiskEnvironment:
        """Determine risk environment"""
        
        try:
            # Analyze risk-on vs risk-off assets
            risk_on_assets = [asset for asset in returns_data.columns 
                            if asset in self.config.equity_indices + self.config.commodities]
            
            risk_off_assets = [asset for asset in returns_data.columns 
                             if asset in self.config.fixed_income]
            
            if not risk_on_assets or not risk_off_assets:
                return RiskEnvironment.UNKNOWN
            
            # Recent performance
            risk_on_performance = returns_data[risk_on_assets].mean(axis=1).rolling(20).mean().iloc[-1]
            risk_off_performance = returns_data[risk_off_assets].mean(axis=1).rolling(20).mean().iloc[-1]
            
            # Cross-asset correlations
            if len(correlations) > 0:
                avg_correlation = correlations.values[np.triu_indices_from(correlations.values, k=1)].mean()
            else:
                avg_correlation = 0
            
            # Volatility
            market_vol = returns_data.mean(axis=1).std() * np.sqrt(252)
            
            # Risk environment classification
            if risk_on_performance > risk_off_performance and avg_correlation < 0.5:
                return RiskEnvironment.RISK_ON
            elif risk_off_performance > risk_on_performance and market_vol > 0.25:
                return RiskEnvironment.RISK_OFF
            elif avg_correlation > 0.8 and market_vol > 0.3:
                return RiskEnvironment.DELEVERAGING
            elif risk_off_performance > risk_on_performance and market_vol < 0.15:
                return RiskEnvironment.FLIGHT_TO_QUALITY
            else:
                return RiskEnvironment.RISK_NEUTRAL
                
        except Exception as e:
            logger.error(f"Error determining risk environment: {e}")
            return RiskEnvironment.UNKNOWN
    
    def _calculate_regime_alignment(self, asset_profiles: Dict[str, AssetRegimeProfile]) -> float:
        """Calculate how aligned asset regimes are"""
        
        try:
            if not asset_profiles:
                return 0.0
            
            # Count regime types
            regime_counts = {}
            for profile in asset_profiles.values():
                regime = profile.current_regime
                if regime not in regime_counts:
                    regime_counts[regime] = 0
                regime_counts[regime] += 1
            
            # Calculate alignment (concentration)
            total_assets = len(asset_profiles)
            max_count = max(regime_counts.values())
            alignment = max_count / total_assets
            
            return alignment
            
        except Exception as e:
            logger.error(f"Error calculating regime alignment: {e}")
            return 0.0
    
    def _calculate_regime_stability(self, asset_profiles: Dict[str, AssetRegimeProfile]) -> float:
        """Calculate regime stability"""
        
        try:
            if not asset_profiles:
                return 0.0
            
            # Average regime confidence
            confidences = [profile.regime_confidence for profile in asset_profiles.values()]
            avg_confidence = sum(confidences) / len(confidences)
            
            return avg_confidence
            
        except Exception as e:
            logger.error(f"Error calculating regime stability: {e}")
            return 0.0
    
    def _analyze_stress_indicators(self, returns_data: pd.DataFrame, 
                                 correlations: pd.DataFrame) -> Dict[str, float]:
        """Analyze various stress indicators"""
        
        try:
            stress_indicators = {}
            
            # Systemic stress (average correlation)
            if len(correlations) > 0:
                triu_indices = np.triu_indices_from(correlations.values, k=1)
                triu_values = correlations.values[triu_indices]
                if len(triu_values) > 0:
                    avg_correlation = triu_values.mean()
                    stress_indicators['systemic_stress'] = max(0, min(1, (avg_correlation - 0.3) / 0.5))
                else:
                    stress_indicators['systemic_stress'] = 0.0
            else:
                stress_indicators['systemic_stress'] = 0.0
            
            # Liquidity stress (volatility spike)
            market_returns = returns_data.mean(axis=1)
            current_vol = market_returns.rolling(20).std().iloc[-1] * np.sqrt(252)
            avg_vol = market_returns.rolling(252).std().mean() * np.sqrt(252) if len(market_returns) >= 252 else current_vol
            
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
            stress_indicators['liquidity_stress'] = max(0, min(1, (vol_ratio - 1) / 2))
            
            # Credit stress (high yield vs treasury performance)
            credit_assets = [asset for asset in returns_data.columns if asset in ['HYG', 'LQD']]
            treasury_assets = [asset for asset in returns_data.columns if asset in ['TLT', 'IEF']]
            
            if credit_assets and treasury_assets:
                credit_perf = returns_data[credit_assets].mean(axis=1).rolling(60).mean().iloc[-1]
                treasury_perf = returns_data[treasury_assets].mean(axis=1).rolling(60).mean().iloc[-1]
                
                credit_spread_proxy = treasury_perf - credit_perf
                stress_indicators['credit_stress'] = max(0, min(1, credit_spread_proxy * 50))
            else:
                stress_indicators['credit_stress'] = 0.0
            
            return stress_indicators
            
        except Exception as e:
            logger.error(f"Error analyzing stress indicators: {e}")
            return {'systemic_stress': 0.0, 'liquidity_stress': 0.0, 'credit_stress': 0.0}
    
    def _set_asset_class_regimes(self, regime: CrossAssetRegime, 
                               asset_profiles: Dict[str, AssetRegimeProfile]) -> CrossAssetRegime:
        """Set asset class specific regimes"""
        
        try:
            # Equity regime
            equity_assets = [symbol for symbol in asset_profiles.keys() 
                           if symbol in self.config.equity_indices]
            if equity_assets:
                equity_regimes = [asset_profiles[symbol].current_regime for symbol in equity_assets]
                regime.equity_regime = max(set(equity_regimes), key=equity_regimes.count)
            
            # Fixed income regime
            bond_assets = [symbol for symbol in asset_profiles.keys() 
                         if symbol in self.config.fixed_income]
            if bond_assets:
                bond_regimes = [asset_profiles[symbol].current_regime for symbol in bond_assets]
                regime.fixed_income_regime = max(set(bond_regimes), key=bond_regimes.count)
            
            # Commodity regime
            commodity_assets = [symbol for symbol in asset_profiles.keys() 
                              if symbol in self.config.commodities]
            if commodity_assets:
                commodity_regimes = [asset_profiles[symbol].current_regime for symbol in commodity_assets]
                regime.commodity_regime = max(set(commodity_regimes), key=commodity_regimes.count)
            
            # Currency regime
            currency_assets = [symbol for symbol in asset_profiles.keys() 
                             if symbol in self.config.currencies]
            if currency_assets:
                currency_regimes = [asset_profiles[symbol].current_regime for symbol in currency_assets]
                regime.currency_regime = max(set(currency_regimes), key=currency_regimes.count)
            
            return regime
            
        except Exception as e:
            logger.error(f"Error setting asset class regimes: {e}")
            return regime
    
    def _calculate_analysis_confidence(self, asset_profiles: Dict[str, AssetRegimeProfile],
                                     regime_alignment: float, regime_stability: float) -> float:
        """Calculate overall analysis confidence"""
        
        try:
            # Factors affecting confidence
            data_quality = 1.0 if len(asset_profiles) >= 5 else len(asset_profiles) / 5
            
            # Combine factors
            confidence = (data_quality + regime_alignment + regime_stability) / 3
            
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating analysis confidence: {e}")
            return 0.5
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min()
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0


class SectorRotationAnalyzer:
    """Analyze sector rotation patterns and regime implications"""
    
    def __init__(self, config: Any = None):
        self.config = config
    
    def _get_config_attr(self, attr_name, default):
        """Safely get config attribute with default fallback"""
        if self.config is None:
            return default
        return getattr(self.config, attr_name, default)
        
        # Standard sector ETFs
        self.sector_etfs = {
            'Technology': 'XLK',
            'Healthcare': 'XLV',
            'Financials': 'XLF',
            'Consumer_Discretionary': 'XLY',
            'Communication': 'XLC',
            'Industrials': 'XLI',
            'Consumer_Staples': 'XLP',
            'Energy': 'XLE',
            'Utilities': 'XLU',
            'Real_Estate': 'XLRE',
            'Materials': 'XLB'
        }
        
        logger.info("Sector rotation analyzer initialized")
    
    def analyze_sector_rotation(self, sector_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze sector rotation patterns"""
        
        try:
            # Extract sector returns
            sector_returns = self._extract_sector_returns(sector_data)
            
            if sector_returns.empty:
                return {}
            
            # Calculate relative performance
            relative_performance = self._calculate_relative_performance(sector_returns)
            
            # Identify rotation patterns
            rotation_signals = self._identify_rotation_patterns(relative_performance)
            
            # Analyze momentum
            momentum_analysis = self._analyze_sector_momentum(sector_returns)
            
            # Risk-on vs risk-off sectors
            risk_analysis = self._analyze_risk_sectors(sector_returns)
            
            # Economic cycle analysis
            cycle_analysis = self._analyze_economic_cycle(relative_performance)
            
            return {
                'sector_returns': sector_returns,
                'relative_performance': relative_performance,
                'rotation_signals': rotation_signals,
                'momentum_analysis': momentum_analysis,
                'risk_analysis': risk_analysis,
                'cycle_analysis': cycle_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sector rotation: {e}")
            return {}
    
    def _extract_sector_returns(self, sector_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Extract returns from sector data"""
        
        try:
            returns_dict = {}
            
            for sector, data in sector_data.items():
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                else:
                    # Use first numeric column
                    numeric_cols = data.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        returns = data[numeric_cols[0]].pct_change().dropna()
                    else:
                        continue
                
                returns_dict[sector] = returns
            
            return pd.DataFrame(returns_dict).dropna()
            
        except Exception as e:
            logger.error(f"Error extracting sector returns: {e}")
            return pd.DataFrame()
    
    def _calculate_relative_performance(self, sector_returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate sector relative performance"""
        
        try:
            # Market benchmark (equal-weighted sectors)
            market_returns = sector_returns.mean(axis=1)
            
            # Relative performance
            relative_perf = sector_returns.sub(market_returns, axis=0)
            
            # Rolling relative performance
            rolling_periods = [20, 60, 252]
            relative_performance = {}
            
            for period in rolling_periods:
                if len(relative_perf) >= period:
                    relative_performance[f'{period}d'] = relative_perf.rolling(period).sum()
            
            return pd.DataFrame(relative_performance)
            
        except Exception as e:
            logger.error(f"Error calculating relative performance: {e}")
            return pd.DataFrame()
    
    def _identify_rotation_patterns(self, relative_performance: pd.DataFrame) -> Dict[str, Any]:
        """Identify sector rotation patterns"""
        
        try:
            if relative_performance.empty:
                return {}
            
            rotation_signals = {}
            
            # Current leaders and laggards
            if '20d' in relative_performance.columns:
                latest_perf = relative_performance['20d'].iloc[-1]
                
                rotation_signals['leaders'] = latest_perf.nlargest(3).to_dict()
                rotation_signals['laggards'] = latest_perf.nsmallest(3).to_dict()
            
            # Momentum shifts
            if '20d' in relative_performance.columns and '60d' in relative_performance.columns:
                short_term = relative_performance['20d'].iloc[-1]
                medium_term = relative_performance['60d'].iloc[-1]
                
                momentum_shift = short_term - medium_term
                rotation_signals['momentum_shifts'] = momentum_shift.to_dict()
            
            # Rotation strength
            if '20d' in relative_performance.columns:
                perf_spread = (relative_performance['20d'].iloc[-1].max() - 
                             relative_performance['20d'].iloc[-1].min())
                rotation_signals['rotation_strength'] = perf_spread
            
            return rotation_signals
            
        except Exception as e:
            logger.error(f"Error identifying rotation patterns: {e}")
            return {}
    
    def _analyze_sector_momentum(self, sector_returns: pd.DataFrame) -> Dict[str, Any]:
        """Analyze sector momentum"""
        
        try:
            momentum_analysis = {}
            
            for sector in sector_returns.columns:
                sector_data = sector_returns[sector]
                
                # Multiple timeframe momentum
                momentum_20d = sector_data.rolling(20).mean().iloc[-1] * 252
                momentum_60d = sector_data.rolling(60).mean().iloc[-1] * 252 if len(sector_data) >= 60 else momentum_20d
                
                # Momentum consistency
                rolling_returns = sector_data.rolling(20).sum()
                momentum_consistency = (rolling_returns > 0).rolling(60).mean().iloc[-1] if len(rolling_returns) >= 60 else 0.5
                
                momentum_analysis[sector] = {
                    'momentum_20d': momentum_20d,
                    'momentum_60d': momentum_60d,
                    'momentum_consistency': momentum_consistency,
                    'momentum_acceleration': momentum_20d - momentum_60d
                }
            
            return momentum_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sector momentum: {e}")
            return {}
    
    def _analyze_risk_sectors(self, sector_returns: pd.DataFrame) -> Dict[str, Any]:
        """Analyze risk-on vs risk-off sector performance"""
        
        try:
            # Define risk-on and risk-off sectors
            risk_on_sectors = ['Technology', 'Consumer_Discretionary', 'Financials', 'Materials']
            risk_off_sectors = ['Utilities', 'Consumer_Staples', 'Healthcare']
            
            risk_analysis = {}
            
            # Risk-on performance
            risk_on_cols = [col for col in sector_returns.columns if any(risk in col for risk in risk_on_sectors)]
            if risk_on_cols:
                risk_on_perf = sector_returns[risk_on_cols].mean(axis=1).rolling(20).mean().iloc[-1] * 252
                risk_analysis['risk_on_performance'] = risk_on_perf
            
            # Risk-off performance
            risk_off_cols = [col for col in sector_returns.columns if any(risk in col for risk in risk_off_sectors)]
            if risk_off_cols:
                risk_off_perf = sector_returns[risk_off_cols].mean(axis=1).rolling(20).mean().iloc[-1] * 252
                risk_analysis['risk_off_performance'] = risk_off_perf
            
            # Risk appetite signal
            if 'risk_on_performance' in risk_analysis and 'risk_off_performance' in risk_analysis:
                risk_analysis['risk_appetite'] = risk_analysis['risk_on_performance'] - risk_analysis['risk_off_performance']
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing risk sectors: {e}")
            return {}
    
    def _analyze_economic_cycle(self, relative_performance: pd.DataFrame) -> Dict[str, Any]:
        """Analyze economic cycle positioning"""
        
        try:
            if relative_performance.empty or '60d' not in relative_performance.columns:
                return {}
            
            # Economic cycle sector patterns
            cycle_sectors = {
                'early_cycle': ['Financials', 'Technology', 'Industrials'],
                'mid_cycle': ['Consumer_Discretionary', 'Materials', 'Energy'],
                'late_cycle': ['Energy', 'Materials', 'Industrials'],
                'recession': ['Consumer_Staples', 'Healthcare', 'Utilities']
            }
            
            cycle_analysis = {}
            latest_perf = relative_performance['60d'].iloc[-1]
            
            for cycle_phase, sectors in cycle_sectors.items():
                cycle_cols = [col for col in latest_perf.index if any(sector in col for sector in sectors)]
                
                if cycle_cols:
                    cycle_performance = latest_perf[cycle_cols].mean()
                    cycle_analysis[cycle_phase] = cycle_performance
            
            # Identify dominant cycle phase
            if cycle_analysis:
                dominant_cycle = max(cycle_analysis.keys(), key=lambda x: cycle_analysis[x])
                cycle_analysis['dominant_cycle'] = dominant_cycle
                cycle_analysis['cycle_strength'] = cycle_analysis[dominant_cycle]
            
            return cycle_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing economic cycle: {e}")
            return {}


class MarketRegimeAnalyzer:
    """
    Comprehensive Market Regime Analyzer
    
    Integrates multiple analysis methods to provide comprehensive market regime
    assessment including cross-asset analysis, factor decomposition, and 
    sector rotation patterns.
    """
    
    def __init__(self, config: Optional[Any] = None):
        """
        Initialize market regime analyzer with centralized configuration
        
        Args:
            config: RegimeConfig or dict (for backward compatibility)
        """
        
        # Use centralized RegimeConfig (Rule 1, Section 7)
        from ..config.component_config import RegimeConfig as CentralizedRegimeConfig
        
        # Handle different config input types
        if isinstance(config, CentralizedRegimeConfig):
            self.config = config
        elif isinstance(config, dict):
            self.config = CentralizedRegimeConfig(**config) if config else CentralizedRegimeConfig()
        elif config is None:
            self.config = CentralizedRegimeConfig()
        else:
            self.config = config
        
        logger.info("✅ MarketRegimeAnalyzer using centralized RegimeConfig (Rule 1, Section 7)")
        
        # Initialize analyzers
        self.cross_asset_analyzer = CrossAssetAnalyzer(self.config)
        self.factor_analyzer = FactorAnalyzer(self.config)
        self.sector_analyzer = SectorRotationAnalyzer(self.config)
        
        # Analysis history
        self.analysis_history: List[CrossAssetRegime] = []
        self.factor_history: List[Dict[str, Any]] = []
        
        logger.info("Market regime analyzer initialized")
    
    def analyze_market_regime(self, market_data: Dict[str, pd.DataFrame],
                            sector_data: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Any]:
        """Perform comprehensive market regime analysis"""
        
        try:
            logger.info("Starting comprehensive market regime analysis")
            
            # Cross-asset regime analysis
            cross_asset_regime = self.cross_asset_analyzer.analyze_cross_asset_regime(market_data)
            
            # Factor analysis
            returns_data = self.cross_asset_analyzer._extract_returns(market_data)
            factor_analysis = self.factor_analyzer.analyze_factors(returns_data) if not returns_data.empty else {}
            
            # Sector rotation analysis
            sector_analysis = {}
            if sector_data:
                sector_analysis = self.sector_analyzer.analyze_sector_rotation(sector_data)
            
            # Combine all analyses
            comprehensive_analysis = {
                'timestamp': datetime.now(),
                'cross_asset_regime': cross_asset_regime,
                'factor_analysis': factor_analysis,
                'sector_analysis': sector_analysis,
                'regime_summary': self._create_regime_summary(cross_asset_regime, factor_analysis, sector_analysis)
            }
            
            # Store history
            self.analysis_history.append(cross_asset_regime)
            if factor_analysis:
                self.factor_history.append(factor_analysis)
            
            # Limit history size
            if len(self.analysis_history) > 100:
                self.analysis_history = self.analysis_history[-50:]
            
            if len(self.factor_history) > 100:
                self.factor_history = self.factor_history[-50:]
            
            logger.info("Market regime analysis completed")
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"Error in market regime analysis: {e}")
            return {}
    
    def _create_regime_summary(self, cross_asset_regime: CrossAssetRegime,
                             factor_analysis: Dict[str, Any],
                             sector_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive regime summary"""
        
        try:
            summary = {
                'primary_regime': cross_asset_regime.macro_regime.value,
                'market_cycle': cross_asset_regime.market_cycle.value,
                'risk_environment': cross_asset_regime.risk_environment.value,
                'regime_stability': cross_asset_regime.regime_stability,
                'confidence': cross_asset_regime.analysis_confidence
            }
            
            # Factor insights
            if factor_analysis and 'regime_factors' in factor_analysis:
                dominant_factor = max(
                    factor_analysis['regime_factors'].keys(),
                    key=lambda x: factor_analysis['regime_factors'][x]['regime_relevance']
                )
                summary['dominant_factor'] = dominant_factor
                summary['factor_strength'] = factor_analysis['regime_factors'][dominant_factor]['regime_relevance']
            
            # Sector insights
            if sector_analysis and 'rotation_signals' in sector_analysis:
                rotation_signals = sector_analysis['rotation_signals']
                if 'leaders' in rotation_signals:
                    summary['sector_leaders'] = list(rotation_signals['leaders'].keys())[:3]
                if 'rotation_strength' in rotation_signals:
                    summary['rotation_strength'] = rotation_signals['rotation_strength']
            
            # Stress levels
            summary['stress_levels'] = {
                'systemic': cross_asset_regime.systemic_stress,
                'liquidity': cross_asset_regime.liquidity_stress,
                'credit': cross_asset_regime.credit_stress
            }
            
            # Risk assessment
            max_stress = max(summary['stress_levels'].values())
            if max_stress > 0.7:
                summary['risk_level'] = 'High'
            elif max_stress > 0.4:
                summary['risk_level'] = 'Medium'
            else:
                summary['risk_level'] = 'Low'
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating regime summary: {e}")
            return {}
    
    def get_regime_trends(self, lookback_periods: int = 30) -> Dict[str, Any]:
        """Analyze regime trends over time"""
        
        try:
            if len(self.analysis_history) < 2:
                return {}
            
            recent_history = self.analysis_history[-lookback_periods:]
            
            # Regime stability trend
            stability_trend = [regime.regime_stability for regime in recent_history]
            
            # Stress trend
            stress_trend = [(regime.systemic_stress + regime.liquidity_stress + regime.credit_stress) / 3 
                          for regime in recent_history]
            
            # Regime changes
            regime_changes = []
            prev_regime = None
            
            for regime in recent_history:
                if prev_regime and regime.macro_regime != prev_regime.macro_regime:
                    regime_changes.append({
                        'date': regime.timestamp,
                        'from': prev_regime.macro_regime.value,
                        'to': regime.macro_regime.value
                    })
                prev_regime = regime
            
            return {
                'stability_trend': stability_trend,
                'stress_trend': stress_trend,
                'regime_changes': regime_changes,
                'current_stability': stability_trend[-1] if stability_trend else 0,
                'current_stress': stress_trend[-1] if stress_trend else 0,
                'stability_direction': 'improving' if len(stability_trend) >= 2 and stability_trend[-1] > stability_trend[-2] else 'deteriorating'
            }
            
        except Exception as e:
            logger.error(f"Error analyzing regime trends: {e}")
            return {}
    
    def export_regime_analysis(self, analysis: Dict[str, Any], filename: Optional[str] = None) -> str:
        """Export regime analysis to file"""
        
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"regime_analysis_{timestamp}.json"
            
            # Prepare data for export (remove non-serializable objects)
            export_data = {}
            
            for key, value in analysis.items():
                if key == 'cross_asset_regime':
                    # Convert CrossAssetRegime to dict
                    regime_dict = {
                        'timestamp': value.timestamp.isoformat(),
                        'macro_regime': value.macro_regime.value,
                        'market_cycle': value.market_cycle.value,
                        'risk_environment': value.risk_environment.value,
                        'regime_stability': value.regime_stability,
                        'analysis_confidence': value.analysis_confidence,
                        'stress_levels': {
                            'systemic': value.systemic_stress,
                            'liquidity': value.liquidity_stress,
                            'credit': value.credit_stress
                        }
                    }
                    export_data[key] = regime_dict
                else:
                    export_data[key] = value
            
            # Export to JSON
            import json
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Regime analysis exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting regime analysis: {e}")
            return ""