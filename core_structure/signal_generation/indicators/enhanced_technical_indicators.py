from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MomentumHorizon(Enum):
    """Multi-horizon momentum based on Moskowitz et al. (2012)"""
    SHORT_TERM = "1w"      # 1 week (5 days)
    MEDIUM_TERM = "1m"     # 1 month (21 days)
    LONG_TERM = "3m"       # 3 months (63 days)
    INTERMEDIATE = "6m"    # 6 months (126 days)
    LONG_TERM_EXTENDED = "12m"  # 12 months (252 days)

class RegimeType(Enum):
    """Market regimes based on Cooper et al. (2004)"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    MOMENTUM_CRASH = "momentum_crash"

@dataclass
class AcademicMomentumConfig:
    """Academic momentum configuration based on latest research"""
    
    # Multi-horizon momentum (Moskowitz et al., 2012)
    momentum_lookback_short: int = 5
    momentum_lookback_medium: int = 21
    momentum_lookback_long: int = 63
    momentum_lookback_intermediate: int = 126
    
    # Multi-horizon weights
    short_term_weight: float = 0.2
    medium_term_weight: float = 0.3
    long_term_weight: float = 0.3
    intermediate_weight: float = 0.2
    
    # Volume-weighted momentum (Gervais et al., 2001)
    volume_weight: float = 0.3
    volume_threshold: float = 1_000_000  # $1M minimum volume
    volume_lookback: int = 20  # 20-day volume average
    
    # Regime detection (Cooper et al., 2004)
    regime_lookback: int = 252  # 1 year for regime detection
    volatility_threshold: float = 0.25  # 25% volatility threshold
    market_state_threshold: float = 0.0  # 0% market return threshold
    
    # Crash protection (Daniel & Moskowitz, 2016)
    crash_detection_enabled: bool = True
    crash_volatility_threshold: float = 0.40  # 40% volatility for crash detection
    crash_market_drawdown_threshold: float = -0.15  # -15% market drawdown
    
    # Business cycle effects (Chordia & Shivakumar, 2002)
    macro_factor_enabled: bool = True
    gdp_growth_weight: float = 0.2
    inflation_weight: float = 0.1
    interest_rate_weight: float = 0.1
    
    # News diffusion (Hong & Stein, 1999)
    analyst_coverage_weight: float = 0.15
    earnings_momentum_weight: float = 0.25
    news_sentiment_weight: float = 0.1
    
    def __post_init__(self):
        """Validate academic parameters on initialization"""
        self._validate_momentum_parameters()
        self._validate_volume_parameters()
        self._validate_regime_parameters()
    
    def _validate_momentum_parameters(self):
        """Validate momentum parameters based on academic research"""
        # Validate momentum lookback periods (academic research ranges)
        if not (1 <= self.momentum_lookback_short <= 50):
            raise ValueError("Short-term momentum should be 1-50 days")
        
        if not (20 <= self.momentum_lookback_medium <= 100):
            raise ValueError("Medium-term momentum should be 20-100 days")
        
        if not (50 <= self.momentum_lookback_long <= 150):
            raise ValueError("Long-term momentum should be 50-150 days")
    
    def _validate_volume_parameters(self):
        """Validate volume parameters"""
        # Validate volume threshold (reasonable range)
        if self.volume_threshold < 100000:  # $100K minimum
            raise ValueError("Volume threshold too low (minimum $100K)")
        
        if self.volume_threshold > 10000000:  # $10M maximum
            raise ValueError("Volume threshold too high (maximum $10M)")
        
        # Validate volume weight
        if not (0.0 <= self.volume_weight <= 1.0):
            raise ValueError("Volume weight should be between 0 and 1")
    
    def _validate_regime_parameters(self):
        """Validate regime detection parameters"""
        # Validate regime lookback
        if not (100 <= self.regime_lookback <= 500):
            raise ValueError("Regime lookback should be 100-500 days")
        
        # Validate volatility threshold (empirical ranges)
        if not (0.1 <= self.volatility_threshold <= 0.5):
            raise ValueError("Volatility threshold should be 10-50%")
        
        # Validate crash thresholds
        if not (0.2 <= self.crash_volatility_threshold <= 0.6):
            raise ValueError("Crash volatility threshold should be 20-60%")
        
        if not (-0.3 <= self.crash_market_drawdown_threshold <= -0.05):
            raise ValueError("Crash drawdown threshold should be -30% to -5%")

class EnhancedTechnicalIndicatorEngine:
    """Enhanced technical indicators with latest academic foundations"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
        # Validate academic parameters on initialization
        self.config.__post_init__()
        
        self.regime_detector = MarketRegimeDetector(config)
        self.volume_analyzer = VolumeMomentumAnalyzer(config)
        self.crash_protector = MomentumCrashProtector(config)
        
        # Minimal data quality and error handling
        self.data_quality_enabled = True
        self.error_handling_enabled = True
    
    def _validate_data_for_momentum(self, data: pd.DataFrame) -> bool:
        """Validate data quality for momentum calculations"""
        try:
            # Check minimum data points
            if len(data) < 60:
                logger.warning(f"Insufficient data for momentum calculation: {len(data)} rows")
                return False
            
            # Check for required columns
            required_columns = ['close']
            for col in required_columns:
                if col not in data.columns:
                    logger.warning(f"Missing required column: {col}")
                    return False
            
            # Check for NaN values
            if data['close'].isna().sum() > len(data) * 0.1:  # More than 10% NaN
                logger.warning(f"Too many NaN values in close prices: {data['close'].isna().sum()}")
                return False
            
            # Check for zero or negative prices
            if (data['close'] <= 0).any():
                logger.warning("Found zero or negative prices")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False
        
    def calculate_academic_momentum_signals(self, data: Dict[str, pd.DataFrame], 
                                          spy_data: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Calculate momentum signals based on latest academic research with minimal validation"""
        
        signals = {}
        
        for symbol, symbol_data in data.items():
            if symbol == 'SPY':
                continue  # Skip benchmark
                
            # Minimal data quality validation
            if self.data_quality_enabled and not self._validate_data_for_momentum(symbol_data):
                logger.warning(f"Skipping {symbol} - insufficient data quality")
                continue
            
            # Generate signals with error handling
            try:
                symbol_signals = {}
                
                # 1. Multi-horizon momentum (Moskowitz et al., 2012)
                multi_horizon_signals = self._calculate_multi_horizon_momentum(symbol_data)
                symbol_signals.update(multi_horizon_signals)
                
                # 2. Volume-weighted momentum (Gervais et al., 2001)
                volume_signals = self._calculate_volume_weighted_momentum(symbol_data)
                symbol_signals.update(volume_signals)
                
                # 3. Regime-adjusted momentum (Cooper et al., 2004)
                regime_signals = self._calculate_regime_adjusted_momentum(symbol_data, spy_data)
                symbol_signals.update(regime_signals)
                
                # 4. Crash-protected momentum (Daniel & Moskowitz, 2016)
                crash_signals = self._calculate_crash_protected_momentum(symbol_data, spy_data)
                symbol_signals.update(crash_signals)
                
                # 5. Business cycle adjusted momentum (Chordia & Shivakumar, 2002)
                macro_signals = self._calculate_macro_adjusted_momentum(symbol_data, spy_data)
                symbol_signals.update(macro_signals)
                
                signals[symbol] = symbol_signals
                
            except Exception as e:
                if self.error_handling_enabled:
                    logger.error(f"Signal calculation failed for {symbol}: {e}")
                    continue
                else:
                    raise
        
        return signals
    
    def _calculate_multi_horizon_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate multi-horizon momentum (Moskowitz et al., 2012) with error handling"""
        signals = {}
        
        horizon_periods = {
            MomentumHorizon.SHORT_TERM: self.config.momentum_lookback_short,
            MomentumHorizon.MEDIUM_TERM: self.config.momentum_lookback_medium,
            MomentumHorizon.LONG_TERM: self.config.momentum_lookback_long,
            MomentumHorizon.INTERMEDIATE: self.config.momentum_lookback_intermediate
        }
        
        try:
            returns = data['close'].pct_change()
            
            for horizon, period in horizon_periods.items():
                if len(data) >= period:
                    # Calculate momentum for each horizon
                    momentum = returns.rolling(period).mean()
                    volatility = returns.rolling(period).std()
                    
                    # Risk-adjusted momentum with division by zero protection
                    if volatility.iloc[-1] > 0:
                        risk_adjusted_momentum = momentum / volatility
                        signals[f'momentum_{horizon.value}'] = risk_adjusted_momentum.iloc[-1]
                    else:
                        signals[f'momentum_{horizon.value}'] = 0.0
                    
                    # Skip recent month to avoid reversal (Jegadeesh & Titman, 1993)
                    if len(data) >= period + 21:
                        skip_momentum = returns.iloc[:-21].rolling(period).mean()
                        skip_volatility = returns.iloc[:-21].rolling(period).std()
                        if skip_volatility.iloc[-1] > 0:
                            skip_risk_adjusted = skip_momentum / skip_volatility
                            signals[f'momentum_{horizon.value}_skip'] = skip_risk_adjusted.iloc[-1]
                        else:
                            signals[f'momentum_{horizon.value}_skip'] = 0.0
                            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Multi-horizon momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals
    
    def _calculate_volume_weighted_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume-weighted momentum (Gervais et al., 2001)"""
        signals = {}
        
        if 'volume' not in data.columns:
            return signals
        
        try:
            # Calculate volume-weighted returns
            returns = data['close'].pct_change()
            volume = data['volume']
            
            # Volume threshold filter
            volume_threshold = self.config.volume_threshold
            high_volume_mask = volume > volume_threshold
            
            # Volume-weighted momentum
            volume_weighted_returns = returns * volume
            volume_weighted_momentum = volume_weighted_returns.rolling(20).mean()
            
            # High-volume momentum premium
            high_volume_momentum = returns[high_volume_mask].rolling(20).mean()
            
            signals['volume_weighted_momentum'] = volume_weighted_momentum.iloc[-1]
            signals['high_volume_momentum'] = high_volume_momentum.iloc[-1] if len(high_volume_momentum) > 0 else 0
            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Volume-weighted momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals
    
    def _calculate_regime_adjusted_momentum(self, data: pd.DataFrame, 
                                          spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate regime-adjusted momentum (Cooper et al., 2004)"""
        signals = {}
        
        try:
            # Detect market regime
            regime = self.regime_detector.detect_regime(spy_data)
            
            # Calculate base momentum
            returns = data['close'].pct_change()
            base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
            
            # Regime-dependent adjustment
            if regime == RegimeType.BULL_MARKET:
                # Momentum stronger in bull markets
                regime_adjusted = base_momentum * 1.2
            elif regime == RegimeType.BEAR_MARKET:
                # Momentum weaker in bear markets
                regime_adjusted = base_momentum * 0.8
            elif regime == RegimeType.HIGH_VOLATILITY:
                # Momentum crashes in high volatility
                regime_adjusted = base_momentum * 0.5
            elif regime == RegimeType.MOMENTUM_CRASH:
                # Crash protection
                regime_adjusted = base_momentum * 0.0
            else:
                regime_adjusted = base_momentum
            
            signals['regime_adjusted_momentum'] = regime_adjusted.iloc[-1]
            signals['market_regime'] = regime.value
            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Regime-adjusted momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals
    
    def _calculate_crash_protected_momentum(self, data: pd.DataFrame, 
                                          spy_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate crash-protected momentum (Daniel & Moskowitz, 2016)"""
        signals = {}
        
        if not self.config.crash_detection_enabled:
            return signals
        
        try:
            # Detect momentum crash conditions
            spy_returns = spy_data['close'].pct_change()
            spy_volatility = spy_returns.rolling(20).std()
            spy_drawdown = (spy_data['close'] / spy_data['close'].rolling(252).max() - 1)
            
            # Crash detection
            is_crash = (
                spy_volatility.iloc[-1] > self.config.crash_volatility_threshold or
                spy_drawdown.iloc[-1] < self.config.crash_market_drawdown_threshold
            )
            
            # Calculate base momentum
            returns = data['close'].pct_change()
            base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
            
            # Apply crash protection
            if is_crash:
                crash_protected_momentum = 0.0  # Zero out momentum during crashes
                signals['crash_protection_active'] = 1.0
            else:
                crash_protected_momentum = base_momentum.iloc[-1]
                signals['crash_protection_active'] = 0.0
            
            signals['crash_protected_momentum'] = crash_protected_momentum
            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Crash-protected momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals
    
    def _calculate_macro_adjusted_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate macro-adjusted momentum (Chordia & Shivakumar, 2002)"""
        signals = {}
        
        if not self.config.macro_factor_enabled:
            return signals
        
        try:
            # Calculate base momentum
            returns = data['close'].pct_change()
            base_momentum = returns.rolling(63).mean() / returns.rolling(63).std()
            
            # Macro factor adjustments (simplified proxies)
            # GDP growth proxy: Market trend
            market_trend = spy_data['close'].pct_change(252).iloc[-1]
            gdp_adjustment = market_trend * self.config.gdp_growth_weight
            
            # Inflation proxy: Volatility trend
            spy_volatility = spy_data['close'].pct_change().rolling(20).std()
            inflation_proxy = spy_volatility.pct_change(60).iloc[-1]
            inflation_adjustment = inflation_proxy * self.config.inflation_weight
            
            # Interest rate proxy: Market beta
            market_returns = spy_data['close'].pct_change()
            beta = returns.rolling(60).cov(market_returns) / market_returns.rolling(60).var()
            interest_rate_adjustment = beta.iloc[-1] * self.config.interest_rate_weight
            
            # Apply macro adjustments
            macro_adjusted_momentum = (
                base_momentum.iloc[-1] + 
                gdp_adjustment + 
                inflation_adjustment + 
                interest_rate_adjustment
            )
            
            signals['macro_adjusted_momentum'] = macro_adjusted_momentum
            signals['gdp_adjustment'] = gdp_adjustment
            signals['inflation_adjustment'] = inflation_adjustment
            signals['interest_rate_adjustment'] = interest_rate_adjustment
            
        except Exception as e:
            if self.error_handling_enabled:
                logger.error(f"Macro-adjusted momentum calculation failed: {e}")
                return {}
            else:
                raise
        
        return signals

class MarketRegimeDetector:
    """Market regime detection based on Cooper et al. (2004)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def detect_regime(self, spy_data: pd.DataFrame) -> RegimeType:
        """Detect current market regime"""
        
        try:
            returns = spy_data['close'].pct_change()
            
            # Calculate regime indicators
            market_return = returns.rolling(self.config.regime_lookback).mean().iloc[-1]
            volatility = returns.rolling(self.config.regime_lookback).std().iloc[-1]
            
            # Regime classification
            if volatility > self.config.crash_volatility_threshold:
                return RegimeType.MOMENTUM_CRASH
            elif volatility > self.config.volatility_threshold:
                return RegimeType.HIGH_VOLATILITY
            elif market_return > self.config.market_state_threshold:
                return RegimeType.BULL_MARKET
            else:
                return RegimeType.BEAR_MARKET
                
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return RegimeType.BULL_MARKET  # Default to bull market

class VolumeMomentumAnalyzer:
    """Volume-momentum analysis based on Gervais et al. (2001)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def analyze_volume_momentum(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analyze volume-momentum interaction"""
        
        if 'volume' not in data.columns:
            return {}
        
        try:
            returns = data['close'].pct_change()
            volume = data['volume']
            
            # Volume-momentum correlation
            volume_momentum_corr = returns.rolling(20).corr(volume)
            
            # High-volume return premium
            high_volume_returns = returns[volume > self.config.volume_threshold]
            high_volume_premium = high_volume_returns.rolling(20).mean()
            
            return {
                'volume_momentum_correlation': volume_momentum_corr.iloc[-1],
                'high_volume_premium': high_volume_premium.iloc[-1] if len(high_volume_premium) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Volume-momentum analysis failed: {e}")
            return {}

class MomentumCrashProtector:
    """Momentum crash protection based on Daniel & Moskowitz (2016)"""
    
    def __init__(self, config: AcademicMomentumConfig):
        self.config = config
    
    def detect_crash_conditions(self, spy_data: pd.DataFrame) -> bool:
        """Detect momentum crash conditions"""
        
        try:
            returns = spy_data['close'].pct_change()
            volatility = returns.rolling(20).std()
            drawdown = (spy_data['close'] / spy_data['close'].rolling(252).max() - 1)
            
            return (
                volatility.iloc[-1] > self.config.crash_volatility_threshold or
                drawdown.iloc[-1] < self.config.crash_market_drawdown_threshold
            )
        except Exception as e:
            logger.error(f"Crash detection failed: {e}")
            return False  # Default to no crash if detection fails

    def _validate_data_for_momentum(self, data: pd.DataFrame) -> bool:
        """Minimal data validation for momentum calculations"""
        
        # Check minimum data length (need at least 1 year for momentum)
        if len(data) < 252:
            return False
        
        # Check for missing data (max 5% missing)
        if data['close'].isnull().sum() > len(data) * 0.05:
            return False
        
        # Check for price variation (no flat prices)
        if data['close'].std() == 0:
            return False
        
        # Check for reasonable price range
        if data['close'].min() <= 0 or data['close'].max() > 10000:
            return False
        
        return True

    def _validate_data_for_momentum(self, data: pd.DataFrame) -> bool:
        """Validate data quality for momentum calculations"""
        try:
            # Check minimum data points
            if len(data) < 60:
                logger.warning(f"Insufficient data for momentum calculation: {len(data)} rows")
                return False
            
            # Check for required columns
            required_columns = ['close']
            for col in required_columns:
                if col not in data.columns:
                    logger.warning(f"Missing required column: {col}")
                    return False
            
            # Check for NaN values
            if data['close'].isna().sum() > len(data) * 0.1:  # More than 10% NaN
                logger.warning(f"Too many NaN values in close prices: {data['close'].isna().sum()}")
                return False
            
            # Check for zero or negative prices
            if (data['close'] <= 0).any():
                logger.warning("Found zero or negative prices")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False 