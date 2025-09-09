#!/usr/bin/env python3
"""
Cross-Asset Regime Confirmation System
=====================================

Professional cross-asset regime confirmation using correlation analysis,
factor decomposition, and institutional flow patterns.

Key Features:
- Multi-asset correlation regime detection
- Factor-based regime confirmation
- Institutional flow analysis
- Regime divergence detection
- Cross-asset momentum confirmation

Author: Professional Quant Enhancement
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import warnings
warnings.filterwarnings('ignore')

# Scientific computing
try:
    from sklearn.decomposition import PCA, FactorAnalysis
    from sklearn.preprocessing import StandardScaler
    from scipy.stats import pearsonr, spearmanr
    from scipy.cluster.hierarchy import linkage, fcluster
    import networkx as nx
    ADVANCED_LIBS_AVAILABLE = True
except ImportError:
    ADVANCED_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)

class AssetClass(Enum):
    """Asset class classifications"""
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    VOLATILITY = "volatility"
    CREDIT = "credit"
    REAL_ESTATE = "real_estate"
    ALTERNATIVE = "alternative"

class CorrelationRegime(Enum):
    """Correlation regime types"""
    LOW_CORRELATION = "low_correlation"      # Normal diversification
    MODERATE_CORRELATION = "moderate_correlation"
    HIGH_CORRELATION = "high_correlation"    # Crisis-like
    NEGATIVE_CORRELATION = "negative_correlation"  # Flight to quality
    BREAKDOWN = "breakdown"                  # Correlation breakdown

class FlowRegime(Enum):
    """Institutional flow regimes"""
    RISK_ON_FLOWS = "risk_on_flows"
    RISK_OFF_FLOWS = "risk_off_flows"
    ROTATION_FLOWS = "rotation_flows"
    DEFENSIVE_FLOWS = "defensive_flows"
    SPECULATIVE_FLOWS = "speculative_flows"

@dataclass
class AssetRegimeSignal:
    """Individual asset regime signal"""
    asset_class: AssetClass
    symbol: str
    regime_score: float  # -1 to 1
    confidence: float
    momentum_score: float
    volatility_score: float
    correlation_score: float
    flow_score: float
    technical_score: float

@dataclass
class CrossAssetRegimeResult:
    """Comprehensive cross-asset regime analysis"""
    # Primary regime classification
    primary_regime: str
    confidence: float
    regime_strength: float
    
    # Asset class signals
    asset_signals: Dict[AssetClass, AssetRegimeSignal]
    
    # Correlation analysis
    correlation_regime: CorrelationRegime
    correlation_stability: float
    correlation_matrix: pd.DataFrame
    
    # Factor analysis
    factor_loadings: Dict[str, float]
    factor_explained_variance: List[float]
    regime_factor_score: float
    
    # Flow analysis
    flow_regime: FlowRegime
    institutional_flow_score: float
    retail_flow_score: float
    
    # Cross-asset momentum
    momentum_alignment: float
    momentum_divergence_score: float
    
    # Regime confirmation metrics
    regime_confirmation_score: float  # How well assets confirm each other
    regime_divergence_alerts: List[str]
    
    # Strategy implications
    diversification_benefit: float
    correlation_risk_adjustment: float
    cross_asset_alpha_opportunity: float
    
    # Forward-looking
    regime_stability_forecast: float
    correlation_forecast: float
    
    timestamp: datetime
    computation_time_ms: float

@dataclass
class CrossAssetConfig:
    """Configuration for cross-asset regime analysis"""
    # Asset universe
    asset_universe: Dict[AssetClass, List[str]] = field(default_factory=lambda: {
        AssetClass.EQUITY: ['SPY', 'EFA', 'EEM', 'IWM', 'QQQ'],
        AssetClass.FIXED_INCOME: ['TLT', 'IEF', 'SHY', 'TIP', 'HYG'],
        AssetClass.COMMODITY: ['GLD', 'SLV', 'USO', 'DBA', 'DBC'],
        AssetClass.CURRENCY: ['UUP', 'FXE', 'FXY', 'EWZ'],
        AssetClass.VOLATILITY: ['VIX', 'VXX', 'UVXY'],
        AssetClass.CREDIT: ['LQD', 'HYG', 'EMB']
    })
    
    # Analysis parameters
    lookback_correlation: int = 60
    lookback_momentum: int = 20
    lookback_flows: int = 10
    
    # Regime thresholds
    correlation_high_threshold: float = 0.7
    correlation_low_threshold: float = 0.3
    momentum_alignment_threshold: float = 0.6
    
    # Performance settings
    enable_factor_analysis: bool = True
    enable_flow_analysis: bool = True
    max_computation_time_ms: int = 200

class CrossAssetRegimeSystem:
    """
    Professional cross-asset regime confirmation system.
    
    Provides institutional-grade cross-asset analysis:
    1. Multi-asset correlation regime detection
    2. Factor-based regime decomposition
    3. Institutional vs retail flow analysis
    4. Cross-asset momentum confirmation
    5. Regime divergence detection and alerts
    """
    
    def __init__(self, config: Optional[CrossAssetConfig] = None):
        self.config = config or CrossAssetConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize models
        self._initialize_models()
        
        # State management
        self.regime_history: List[CrossAssetRegimeResult] = []
        self.correlation_history: List[pd.DataFrame] = []
        self.flow_history: Dict[str, List[float]] = {}
        
        # Performance tracking
        self.performance_metrics = {
            'analyses_completed': 0,
            'avg_computation_time': 0.0,
            'regime_accuracy': 0.0,
            'correlation_forecast_accuracy': 0.0
        }
        
        self.logger.info("Cross-asset regime system initialized")
    
    def _initialize_models(self):
        """Initialize cross-asset analysis models"""
        self.models = {}
        
        if ADVANCED_LIBS_AVAILABLE:
            # Factor analysis model
            self.models['factor_analyzer'] = FactorAnalysis(
                n_components=5,  # Market, Size, Value, Momentum, Quality
                random_state=42
            )
            
            # PCA for dimensionality reduction
            self.models['pca'] = PCA(n_components=0.95)  # Explain 95% variance
            
            # Scaler for cross-asset returns
            self.models['scaler'] = StandardScaler()
        
        self.logger.info(f"Initialized {len(self.models)} cross-asset models")
    
    async def analyze_cross_asset_regime_async(self, 
                                             market_data: Dict[str, pd.DataFrame],
                                             flow_data: Optional[Dict[str, pd.Series]] = None) -> CrossAssetRegimeResult:
        """
        Comprehensive async cross-asset regime analysis.
        
        Args:
            market_data: Dict of symbol -> OHLCV data
            flow_data: Optional institutional flow data
            
        Returns:
            Comprehensive cross-asset regime analysis
        """
        start_time = datetime.now()
        
        try:
            # Prepare cross-asset return matrix
            return_matrix = self._prepare_return_matrix(market_data)
            
            if return_matrix.empty:
                return self._create_fallback_result()
            
            # Parallel analysis of different regime aspects
            tasks = [
                self._analyze_correlation_regime_async(return_matrix),
                self._analyze_momentum_alignment_async(return_matrix),
                self._analyze_asset_class_signals_async(market_data),
            ]
            
            if self.config.enable_factor_analysis:
                tasks.append(self._analyze_factor_regime_async(return_matrix))
            
            if self.config.enable_flow_analysis and flow_data:
                tasks.append(self._analyze_flow_regime_async(flow_data))
            
            # Execute parallel analysis
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Extract results
            correlation_result = results[0] if len(results) > 0 else {}
            momentum_result = results[1] if len(results) > 1 else {}
            asset_signals = results[2] if len(results) > 2 else {}
            
            factor_result = {}
            flow_result = {}
            
            if self.config.enable_factor_analysis and len(results) > 3:
                factor_result = results[3] if not isinstance(results[3], Exception) else {}
            
            if self.config.enable_flow_analysis and len(results) > 4:
                flow_result = results[4] if not isinstance(results[4], Exception) else {}
            
            # Combine all signals for primary regime classification
            primary_regime, confidence = self._classify_primary_cross_asset_regime(
                correlation_result, momentum_result, factor_result, flow_result
            )
            
            # Calculate regime strength
            regime_strength = self._calculate_cross_asset_regime_strength(
                correlation_result, momentum_result, asset_signals
            )
            
            # Regime confirmation analysis
            confirmation_score = self._calculate_regime_confirmation_score(asset_signals)
            divergence_alerts = self._detect_regime_divergences(asset_signals)
            
            # Strategy implications
            diversification_benefit = self._calculate_diversification_benefit(
                correlation_result.get('correlation_matrix', pd.DataFrame())
            )
            
            correlation_risk_adjustment = self._calculate_correlation_risk_adjustment(
                correlation_result.get('regime', CorrelationRegime.MODERATE_CORRELATION)
            )
            
            alpha_opportunity = self._calculate_cross_asset_alpha_opportunity(
                asset_signals, momentum_result
            )
            
            # Forward-looking analysis
            stability_forecast = self._forecast_regime_stability(
                correlation_result, momentum_result
            )
            
            correlation_forecast = self._forecast_correlation_regime(
                correlation_result.get('correlation_matrix', pd.DataFrame())
            )
            
            # Calculate computation time
            computation_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Create comprehensive result
            result = CrossAssetRegimeResult(
                primary_regime=primary_regime,
                confidence=confidence,
                regime_strength=regime_strength,
                
                asset_signals=asset_signals,
                
                correlation_regime=correlation_result.get('regime', CorrelationRegime.MODERATE_CORRELATION),
                correlation_stability=correlation_result.get('stability', 0.5),
                correlation_matrix=correlation_result.get('correlation_matrix', pd.DataFrame()),
                
                factor_loadings=factor_result.get('loadings', {}),
                factor_explained_variance=factor_result.get('explained_variance', []),
                regime_factor_score=factor_result.get('regime_score', 0.0),
                
                flow_regime=flow_result.get('regime', FlowRegime.RISK_ON_FLOWS),
                institutional_flow_score=flow_result.get('institutional_score', 0.0),
                retail_flow_score=flow_result.get('retail_score', 0.0),
                
                momentum_alignment=momentum_result.get('alignment', 0.5),
                momentum_divergence_score=momentum_result.get('divergence', 0.0),
                
                regime_confirmation_score=confirmation_score,
                regime_divergence_alerts=divergence_alerts,
                
                diversification_benefit=diversification_benefit,
                correlation_risk_adjustment=correlation_risk_adjustment,
                cross_asset_alpha_opportunity=alpha_opportunity,
                
                regime_stability_forecast=stability_forecast,
                correlation_forecast=correlation_forecast,
                
                timestamp=datetime.now(),
                computation_time_ms=computation_time
            )
            
            # Update history and metrics
            self._update_regime_history(result)
            self._update_performance_metrics(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cross-asset regime analysis failed: {e}")
            return self._create_fallback_result()
    
    def analyze_cross_asset_regime(self, 
                                 market_data: Dict[str, pd.DataFrame],
                                 flow_data: Optional[Dict[str, pd.Series]] = None) -> CrossAssetRegimeResult:
        """Synchronous wrapper for cross-asset regime analysis"""
        return asyncio.run(self.analyze_cross_asset_regime_async(market_data, flow_data))
    
    def _prepare_return_matrix(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Prepare aligned return matrix for cross-asset analysis"""
        try:
            return_series = {}
            
            for symbol, data in market_data.items():
                if 'close' in data.columns and len(data) > 20:
                    returns = data['close'].pct_change().dropna()
                    return_series[symbol] = returns
            
            if not return_series:
                return pd.DataFrame()
            
            # Align all return series
            return_df = pd.DataFrame(return_series)
            return_df = return_df.dropna()
            
            # Keep only recent data for analysis
            lookback = max(self.config.lookback_correlation, self.config.lookback_momentum)
            if len(return_df) > lookback:
                return_df = return_df.tail(lookback)
            
            return return_df
            
        except Exception as e:
            self.logger.error(f"Return matrix preparation failed: {e}")
            return pd.DataFrame()
    
    async def _analyze_correlation_regime_async(self, return_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlation regime asynchronously"""
        return self._analyze_correlation_regime(return_matrix)
    
    def _analyze_correlation_regime(self, return_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlation regime"""
        try:
            if return_matrix.empty or len(return_matrix.columns) < 2:
                return {}
            
            # Calculate rolling correlation matrix
            lookback = self.config.lookback_correlation
            
            if len(return_matrix) < lookback:
                correlation_matrix = return_matrix.corr()
            else:
                recent_returns = return_matrix.tail(lookback)
                correlation_matrix = recent_returns.corr()
            
            # Calculate average correlation (excluding diagonal)
            corr_values = correlation_matrix.values
            mask = ~np.eye(corr_values.shape[0], dtype=bool)
            avg_correlation = np.mean(corr_values[mask])
            
            # Classify correlation regime
            if avg_correlation > self.config.correlation_high_threshold:
                regime = CorrelationRegime.HIGH_CORRELATION
            elif avg_correlation < self.config.correlation_low_threshold:
                regime = CorrelationRegime.LOW_CORRELATION
            elif avg_correlation < 0:
                regime = CorrelationRegime.NEGATIVE_CORRELATION
            else:
                regime = CorrelationRegime.MODERATE_CORRELATION
            
            # Calculate correlation stability
            if len(return_matrix) >= lookback * 2:
                # Compare recent vs historical correlations
                historical_returns = return_matrix.head(lookback)
                historical_corr = historical_returns.corr()
                
                # Calculate correlation of correlations (stability measure)
                hist_values = historical_corr.values[mask]
                recent_values = corr_values[mask]
                
                stability = np.corrcoef(hist_values, recent_values)[0, 1]
                stability = max(0, stability) if not np.isnan(stability) else 0.5
            else:
                stability = 0.5
            
            return {
                'regime': regime,
                'avg_correlation': avg_correlation,
                'correlation_matrix': correlation_matrix,
                'stability': stability
            }
            
        except Exception as e:
            self.logger.error(f"Correlation regime analysis failed: {e}")
            return {}
    
    async def _analyze_momentum_alignment_async(self, return_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Analyze momentum alignment asynchronously"""
        return self._analyze_momentum_alignment(return_matrix)
    
    def _analyze_momentum_alignment(self, return_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cross-asset momentum alignment"""
        try:
            if return_matrix.empty:
                return {}
            
            lookback = self.config.lookback_momentum
            
            # Calculate momentum for each asset
            momentum_scores = {}
            for symbol in return_matrix.columns:
                returns = return_matrix[symbol].dropna()
                if len(returns) >= lookback:
                    # Simple momentum: cumulative return over lookback period
                    momentum = returns.tail(lookback).sum()
                    momentum_scores[symbol] = momentum
            
            if not momentum_scores:
                return {}
            
            # Calculate momentum alignment
            momentum_values = list(momentum_scores.values())
            
            # Alignment = how many assets have same directional momentum
            positive_momentum = sum(1 for m in momentum_values if m > 0)
            negative_momentum = sum(1 for m in momentum_values if m < 0)
            total_assets = len(momentum_values)
            
            alignment = max(positive_momentum, negative_momentum) / total_assets
            
            # Calculate momentum divergence
            momentum_std = np.std(momentum_values)
            momentum_mean = np.mean(np.abs(momentum_values))
            divergence = momentum_std / momentum_mean if momentum_mean > 0 else 0
            
            return {
                'alignment': alignment,
                'divergence': divergence,
                'momentum_scores': momentum_scores,
                'positive_momentum_pct': positive_momentum / total_assets,
                'negative_momentum_pct': negative_momentum / total_assets
            }
            
        except Exception as e:
            self.logger.error(f"Momentum alignment analysis failed: {e}")
            return {}
    
    async def _analyze_asset_class_signals_async(self, market_data: Dict[str, pd.DataFrame]) -> Dict[AssetClass, AssetRegimeSignal]:
        """Analyze individual asset class signals asynchronously"""
        return self._analyze_asset_class_signals(market_data)
    
    def _analyze_asset_class_signals(self, market_data: Dict[str, pd.DataFrame]) -> Dict[AssetClass, AssetRegimeSignal]:
        """Analyze individual asset class regime signals"""
        signals = {}
        
        try:
            for asset_class, symbols in self.config.asset_universe.items():
                class_signals = []
                
                for symbol in symbols:
                    if symbol in market_data:
                        signal = self._calculate_asset_signal(symbol, market_data[symbol], asset_class)
                        if signal:
                            class_signals.append(signal)
                
                if class_signals:
                    # Aggregate signals for asset class
                    avg_regime_score = np.mean([s.regime_score for s in class_signals])
                    avg_confidence = np.mean([s.confidence for s in class_signals])
                    avg_momentum = np.mean([s.momentum_score for s in class_signals])
                    avg_volatility = np.mean([s.volatility_score for s in class_signals])
                    
                    # Use the signal from the most liquid/representative asset
                    representative_signal = class_signals[0]
                    
                    signals[asset_class] = AssetRegimeSignal(
                        asset_class=asset_class,
                        symbol=representative_signal.symbol,
                        regime_score=avg_regime_score,
                        confidence=avg_confidence,
                        momentum_score=avg_momentum,
                        volatility_score=avg_volatility,
                        correlation_score=representative_signal.correlation_score,
                        flow_score=representative_signal.flow_score,
                        technical_score=representative_signal.technical_score
                    )
        
        except Exception as e:
            self.logger.error(f"Asset class signal analysis failed: {e}")
        
        return signals
    
    def _calculate_asset_signal(self, symbol: str, data: pd.DataFrame, asset_class: AssetClass) -> Optional[AssetRegimeSignal]:
        """Calculate regime signal for individual asset"""
        try:
            if len(data) < 20:
                return None
            
            prices = data['close']
            returns = prices.pct_change().dropna()
            
            # Momentum score
            momentum_lookback = self.config.lookback_momentum
            if len(returns) >= momentum_lookback:
                momentum_score = returns.tail(momentum_lookback).sum()
            else:
                momentum_score = returns.sum()
            
            # Volatility score (normalized)
            current_vol = returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else returns.std()
            historical_vol = returns.std()
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            volatility_score = np.clip((vol_ratio - 1.0), -1, 1)  # Normalize around 1.0
            
            # Technical score (simple trend)
            if len(prices) >= 50:
                ma_20 = prices.rolling(20).mean().iloc[-1]
                ma_50 = prices.rolling(50).mean().iloc[-1]
                current_price = prices.iloc[-1]
                
                technical_score = 0.0
                if current_price > ma_20:
                    technical_score += 0.5
                if current_price > ma_50:
                    technical_score += 0.5
                if ma_20 > ma_50:
                    technical_score += 0.5
                
                technical_score = (technical_score - 0.75) * 2  # Normalize to -1 to 1
            else:
                technical_score = 0.0
            
            # Overall regime score (weighted combination)
            regime_score = (
                momentum_score * 0.4 +
                technical_score * 0.4 +
                volatility_score * 0.2
            )
            
            # Confidence based on data quality and signal strength
            confidence = min(0.9, max(0.1, abs(regime_score) * 0.8 + 0.2))
            
            return AssetRegimeSignal(
                asset_class=asset_class,
                symbol=symbol,
                regime_score=np.clip(regime_score, -1, 1),
                confidence=confidence,
                momentum_score=momentum_score,
                volatility_score=volatility_score,
                correlation_score=0.0,  # Placeholder
                flow_score=0.0,  # Placeholder
                technical_score=technical_score
            )
            
        except Exception as e:
            self.logger.error(f"Asset signal calculation failed for {symbol}: {e}")
            return None
    
    # Placeholder methods for remaining functionality
    async def _analyze_factor_regime_async(self, return_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Analyze factor regime - placeholder"""
        return {'loadings': {}, 'explained_variance': [], 'regime_score': 0.0}
    
    async def _analyze_flow_regime_async(self, flow_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Analyze flow regime - placeholder"""
        return {'regime': FlowRegime.RISK_ON_FLOWS, 'institutional_score': 0.0, 'retail_score': 0.0}
    
    def _classify_primary_cross_asset_regime(self, correlation_result: Dict, momentum_result: Dict, 
                                           factor_result: Dict, flow_result: Dict) -> Tuple[str, float]:
        """Classify primary cross-asset regime - placeholder"""
        return "risk_on", 0.7
    
    def _calculate_cross_asset_regime_strength(self, correlation_result: Dict, momentum_result: Dict, 
                                             asset_signals: Dict) -> float:
        """Calculate regime strength - placeholder"""
        return 0.8
    
    def _calculate_regime_confirmation_score(self, asset_signals: Dict) -> float:
        """Calculate regime confirmation score - placeholder"""
        return 0.75
    
    def _detect_regime_divergences(self, asset_signals: Dict) -> List[str]:
        """Detect regime divergences - placeholder"""
        return []
    
    def _calculate_diversification_benefit(self, correlation_matrix: pd.DataFrame) -> float:
        """Calculate diversification benefit - placeholder"""
        return 0.6
    
    def _calculate_correlation_risk_adjustment(self, correlation_regime: CorrelationRegime) -> float:
        """Calculate correlation risk adjustment - placeholder"""
        return 1.0
    
    def _calculate_cross_asset_alpha_opportunity(self, asset_signals: Dict, momentum_result: Dict) -> float:
        """Calculate cross-asset alpha opportunity - placeholder"""
        return 0.3
    
    def _forecast_regime_stability(self, correlation_result: Dict, momentum_result: Dict) -> float:
        """Forecast regime stability - placeholder"""
        return 0.7
    
    def _forecast_correlation_regime(self, correlation_matrix: pd.DataFrame) -> float:
        """Forecast correlation regime - placeholder"""
        return 0.6
    
    def _update_regime_history(self, result: CrossAssetRegimeResult):
        """Update regime history - placeholder"""
        pass
    
    def _update_performance_metrics(self, result: CrossAssetRegimeResult):
        """Update performance metrics - placeholder"""
        pass
    
    def _create_fallback_result(self) -> CrossAssetRegimeResult:
        """Create fallback result when analysis fails"""
        return CrossAssetRegimeResult(
            primary_regime="neutral",
            confidence=0.5,
            regime_strength=0.5,
            asset_signals={},
            correlation_regime=CorrelationRegime.MODERATE_CORRELATION,
            correlation_stability=0.5,
            correlation_matrix=pd.DataFrame(),
            factor_loadings={},
            factor_explained_variance=[],
            regime_factor_score=0.0,
            flow_regime=FlowRegime.RISK_ON_FLOWS,
            institutional_flow_score=0.0,
            retail_flow_score=0.0,
            momentum_alignment=0.5,
            momentum_divergence_score=0.0,
            regime_confirmation_score=0.5,
            regime_divergence_alerts=[],
            diversification_benefit=0.5,
            correlation_risk_adjustment=1.0,
            cross_asset_alpha_opportunity=0.0,
            regime_stability_forecast=0.5,
            correlation_forecast=0.5,
            timestamp=datetime.now(),
            computation_time_ms=0.0
        )

__all__ = [
    'CrossAssetRegimeSystem',
    'CrossAssetRegimeResult',
    'AssetRegimeSignal',
    'CrossAssetConfig',
    'AssetClass',
    'CorrelationRegime',
    'FlowRegime'
]
