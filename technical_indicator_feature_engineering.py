#!/usr/bin/env python3
"""
Advanced Feature Engineering with Technical Indicators
====================================================

This module creates sophisticated features from your technical indicators
data to enhance pair trading signal generation and market regime detection.

Features created:
✅ Relative strength indicators across pairs
✅ Momentum divergence signals  
✅ Volatility regime classification
✅ Mean reversion strength indicators
✅ Cross-symbol correlation features
✅ Multi-timeframe trend alignment
✅ Indicator ensemble scoring
"""

import pandas as pd
import numpy as np
import clickhouse_connect
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""
    lookback_windows: List[int] = None
    correlation_window: int = 20
    volatility_window: int = 10
    momentum_windows: List[int] = None
    trend_alignment_windows: List[int] = None
    
    def __post_init__(self):
        if self.lookback_windows is None:
            self.lookback_windows = [5, 10, 20, 40]
        if self.momentum_windows is None:
            self.momentum_windows = [5, 10, 20]
        if self.trend_alignment_windows is None:
            self.trend_alignment_windows = [10, 20, 50]

class TechnicalIndicatorFeatureEngine:
    """Advanced feature engineering using technical indicators"""
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.ch_client = clickhouse_connect.get_client(
            host="localhost",
            port=8123,
            database='polygon_data'
        )
        logger.info("✅ Feature engine initialized")
    
    def create_comprehensive_features(self, symbols: List[str], 
                                    start_date: str, end_date: str) -> pd.DataFrame:
        """Create comprehensive feature set from technical indicators"""
        logger.info(f"🔧 Creating comprehensive features for {symbols}")
        
        # Load base indicators data
        indicators_df = self._load_indicators_data(symbols, start_date, end_date)
        
        if indicators_df.empty:
            logger.warning("No indicators data available")
            return pd.DataFrame()
        
        features_list = []
        
        # 1. Individual symbol features
        for symbol in symbols:
            symbol_data = indicators_df[indicators_df['symbol'] == symbol].set_index('date')
            symbol_features = self._create_symbol_features(symbol_data, symbol)
            features_list.append(symbol_features)
        
        # 2. Cross-symbol features (for pairs)
        if len(symbols) == 2:
            cross_features = self._create_cross_symbol_features(indicators_df, symbols)
            features_list.append(cross_features)
        
        # 3. Market regime features
        regime_features = self._create_regime_features(indicators_df, symbols)
        features_list.append(regime_features)
        
        # 4. Momentum and trend features
        momentum_features = self._create_momentum_features(indicators_df, symbols)
        features_list.append(momentum_features)
        
        # 5. Volatility and risk features
        volatility_features = self._create_volatility_features(indicators_df, symbols)
        features_list.append(volatility_features)
        
        # Combine all features
        all_features = pd.concat([f for f in features_list if not f.empty], axis=1)
        
        # Remove duplicate columns
        all_features = all_features.loc[:, ~all_features.columns.duplicated()]
        
        logger.info(f"✅ Created {len(all_features.columns)} features across {len(all_features)} observations")
        
        return all_features
    
    def _load_indicators_data(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Load indicators data from ClickHouse"""
        query = f"""
        SELECT 
            symbol,
            date,
            sma_20,
            sma_50,
            ema_20,
            rsi_14,
            macd_line,
            macd_signal,
            macd_histogram
        FROM technical_indicators
        WHERE symbol IN ({','.join([f"'{s}'" for s in symbols])})
        AND date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date, symbol
        """
        
        result = self.ch_client.query(query)
        df = pd.DataFrame(result.result_set, columns=[
            'symbol', 'date', 'sma_20', 'sma_50', 'ema_20', 
            'rsi_14', 'macd_line', 'macd_signal', 'macd_histogram'
        ])
        
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def _create_symbol_features(self, symbol_data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Create features for individual symbol"""
        features = pd.DataFrame(index=symbol_data.index)
        
        # Trend features
        features[f'{symbol}_sma_trend'] = (symbol_data['sma_20'] > symbol_data['sma_50']).astype(int)
        features[f'{symbol}_sma_strength'] = (symbol_data['sma_20'] - symbol_data['sma_50']) / symbol_data['sma_50']
        
        # RSI features
        features[f'{symbol}_rsi_normalized'] = (symbol_data['rsi_14'] - 50) / 50
        features[f'{symbol}_rsi_extreme'] = ((symbol_data['rsi_14'] > 70) | (symbol_data['rsi_14'] < 30)).astype(int)
        features[f'{symbol}_rsi_overbought'] = (symbol_data['rsi_14'] > 70).astype(int)
        features[f'{symbol}_rsi_oversold'] = (symbol_data['rsi_14'] < 30).astype(int)
        
        # MACD features
        features[f'{symbol}_macd_bullish'] = (symbol_data['macd_line'] > symbol_data['macd_signal']).astype(int)
        features[f'{symbol}_macd_histogram_normalized'] = symbol_data['macd_histogram'] / symbol_data['macd_histogram'].rolling(20).std()
        features[f'{symbol}_macd_momentum'] = np.sign(symbol_data['macd_histogram'])
        
        # Moving average features
        for window in self.config.lookback_windows:
            if len(symbol_data) > window:
                # RSI momentum
                features[f'{symbol}_rsi_change_{window}d'] = symbol_data['rsi_14'].diff(window)
                features[f'{symbol}_rsi_momentum_{window}d'] = (
                    symbol_data['rsi_14'].rolling(window).mean() - symbol_data['rsi_14'].shift(window)
                )
                
                # SMA momentum
                features[f'{symbol}_sma_momentum_{window}d'] = (
                    symbol_data['sma_20'].pct_change(window)
                )
                
                # MACD momentum
                features[f'{symbol}_macd_momentum_{window}d'] = (
                    symbol_data['macd_histogram'].rolling(window).mean()
                )
        
        # Volatility proxy using RSI
        features[f'{symbol}_rsi_volatility'] = symbol_data['rsi_14'].rolling(10).std()
        
        return features
    
    def _create_cross_symbol_features(self, indicators_df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Create cross-symbol features for pairs"""
        symbol1, symbol2 = symbols[0], symbols[1]
        
        # Remove duplicates to prevent pivot issues
        indicators_df = indicators_df.drop_duplicates(subset=['date', 'symbol']).sort_values(['date', 'symbol'])
        
        # Pivot data for easier cross-symbol calculations
        pivot_data = {}
        for col in ['rsi_14', 'sma_20', 'sma_50', 'macd_histogram', 'macd_line']:
            try:
                pivot_data[col] = indicators_df.pivot(index='date', columns='symbol', values=col)
            except ValueError as e:
                print(f"Warning: Could not pivot {col}: {e}")
                continue
        
        # Check if we have both symbols in the pivot
        if symbol1 not in pivot_data['rsi_14'].columns or symbol2 not in pivot_data['rsi_14'].columns:
            print(f"Warning: Missing symbols in pivot data. Available: {list(pivot_data['rsi_14'].columns)}")
            return pd.DataFrame()
        
        features = pd.DataFrame(index=pivot_data['rsi_14'].index)
        
        # RSI divergence features
        features['rsi_divergence'] = abs(pivot_data['rsi_14'][symbol1] - pivot_data['rsi_14'][symbol2])
        features['rsi_relative_strength'] = pivot_data['rsi_14'][symbol1] - pivot_data['rsi_14'][symbol2]
        features['rsi_both_extreme'] = (
            ((pivot_data['rsi_14'][symbol1] > 70) | (pivot_data['rsi_14'][symbol1] < 30)) &
            ((pivot_data['rsi_14'][symbol2] > 70) | (pivot_data['rsi_14'][symbol2] < 30))
        ).astype(int).astype(int)
        
        # Trend alignment features
        features['trend_alignment'] = (
            (pivot_data['sma_20'][symbol1] > pivot_data['sma_50'][symbol1]) == 
            (pivot_data['sma_20'][symbol2] > pivot_data['sma_50'][symbol2])
        ).astype(int)
        
        features['trend_strength_ratio'] = (
            (pivot_data['sma_20'][symbol1] - pivot_data['sma_50'][symbol1]) /
            (pivot_data['sma_20'][symbol2] - pivot_data['sma_50'][symbol2])
        )
        
        # MACD momentum divergence
        features['macd_momentum_divergence'] = (
            np.sign(pivot_data['macd_histogram'][symbol1]) != 
            np.sign(pivot_data['macd_histogram'][symbol2])
        ).astype(int)
        
        features['macd_relative_momentum'] = (
            pivot_data['macd_histogram'][symbol1] - pivot_data['macd_histogram'][symbol2]
        )
        
        # Correlation features
        for window in [10, 20, 40]:
            # Calculate rolling correlation between the two symbols
            features[f'rsi_correlation_{window}d'] = (
                pivot_data['rsi_14'][symbol1].rolling(window).corr(
                    pivot_data['rsi_14'][symbol2]
                )
            )
            
            features[f'macd_correlation_{window}d'] = (
                pivot_data['macd_line'][symbol1].rolling(window).corr(
                    pivot_data['macd_line'][symbol2]
                )
            )
        
        return features
    
    def _create_regime_features(self, indicators_df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Create market regime classification features"""
        features = pd.DataFrame()
        
        for symbol in symbols:
            symbol_data = indicators_df[indicators_df['symbol'] == symbol].set_index('date')
            
            # Market regime classification
            regime_conditions = {
                'trending_up': (
                    (symbol_data['sma_20'] > symbol_data['sma_50']) &
                    (symbol_data['macd_histogram'] > 0) &
                    (symbol_data['rsi_14'] > 50)
                ),
                'trending_down': (
                    (symbol_data['sma_20'] < symbol_data['sma_50']) &
                    (symbol_data['macd_histogram'] < 0) &
                    (symbol_data['rsi_14'] < 50)
                ),
                'ranging': (
                    (abs(symbol_data['rsi_14'] - 50) < 20) &
                    (abs(symbol_data['macd_histogram']) < symbol_data['macd_histogram'].rolling(20).std())
                ),
                'overbought': symbol_data['rsi_14'] > 70,
                'oversold': symbol_data['rsi_14'] < 30
            }
            
            for regime, condition in regime_conditions.items():
                features[f'{symbol}_regime_{regime}'] = condition.astype(int)
            
            # Regime stability (how long in current regime)
            regime_primary = np.where(
                symbol_data['rsi_14'] > 70, 'overbought',
                np.where(symbol_data['rsi_14'] < 30, 'oversold',
                        np.where(symbol_data['sma_20'] > symbol_data['sma_50'], 'trending_up',
                               np.where(symbol_data['sma_20'] < symbol_data['sma_50'], 'trending_down', 'ranging')))
            )
            
            # Calculate regime persistence
            regime_changes = pd.Series(regime_primary).ne(pd.Series(regime_primary).shift()).cumsum()
            regime_duration = regime_changes.groupby(regime_changes).cumcount() + 1
            features[f'{symbol}_regime_persistence'] = regime_duration
        
        return features
    
    def _create_momentum_features(self, indicators_df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Create momentum-based features"""
        features = pd.DataFrame()
        
        for symbol in symbols:
            symbol_data = indicators_df[indicators_df['symbol'] == symbol].set_index('date')
            
            # Multi-timeframe momentum alignment
            for window in self.config.momentum_windows:
                if len(symbol_data) > window:
                    # RSI momentum
                    rsi_momentum = symbol_data['rsi_14'].diff(window)
                    features[f'{symbol}_rsi_momentum_{window}d'] = rsi_momentum
                    features[f'{symbol}_rsi_momentum_strength_{window}d'] = abs(rsi_momentum)
                    
                    # MACD momentum trend
                    macd_trend = symbol_data['macd_histogram'].rolling(window).apply(
                        lambda x: stats.linregress(range(len(x)), x)[0] if len(x) == window else np.nan
                    )
                    features[f'{symbol}_macd_trend_{window}d'] = macd_trend
                    
                    # SMA momentum
                    sma_momentum = symbol_data['sma_20'].pct_change(window)
                    features[f'{symbol}_sma_momentum_{window}d'] = sma_momentum
            
            # Momentum convergence/divergence
            features[f'{symbol}_momentum_convergence'] = (
                np.sign(symbol_data['rsi_14'].diff(5)) == 
                np.sign(symbol_data['macd_histogram'].diff(5))
            ).astype(int)
            
            # Momentum acceleration
            features[f'{symbol}_rsi_acceleration'] = symbol_data['rsi_14'].diff().diff()
            features[f'{symbol}_macd_acceleration'] = symbol_data['macd_histogram'].diff().diff()
        
        return features
    
    def _create_volatility_features(self, indicators_df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Create volatility and risk-based features"""
        features = pd.DataFrame()
        
        for symbol in symbols:
            symbol_data = indicators_df[indicators_df['symbol'] == symbol].set_index('date')
            
            # RSI-based volatility measures
            for window in [5, 10, 20]:
                rsi_vol = symbol_data['rsi_14'].rolling(window).std()
                features[f'{symbol}_rsi_volatility_{window}d'] = rsi_vol
                
                # Normalized volatility (compared to long-term average)
                rsi_vol_norm = rsi_vol / symbol_data['rsi_14'].rolling(60).std()
                features[f'{symbol}_rsi_vol_normalized_{window}d'] = rsi_vol_norm
            
            # MACD volatility
            macd_vol = symbol_data['macd_histogram'].rolling(10).std()
            features[f'{symbol}_macd_volatility'] = macd_vol
            
            # Trend stability (how stable is the SMA trend)
            sma_diff = symbol_data['sma_20'] - symbol_data['sma_50']
            sma_trend_stability = sma_diff.rolling(20).std() / abs(sma_diff.rolling(20).mean())
            features[f'{symbol}_trend_stability'] = sma_trend_stability
            
            # Extreme condition frequency
            extreme_frequency = (
                (symbol_data['rsi_14'] > 70) | (symbol_data['rsi_14'] < 30)
            ).rolling(20).mean()
            features[f'{symbol}_extreme_frequency'] = extreme_frequency
        
        return features
    
    def create_ensemble_score(self, features_df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Create ensemble scoring for trading signals"""
        logger.info("🎯 Creating ensemble trading scores")
        
        scores = pd.DataFrame(index=features_df.index)
        
        if len(symbols) == 2:
            symbol1, symbol2 = symbols[0], symbols[1]
            
            # Mean reversion opportunity score
            mean_reversion_factors = []
            
            # RSI divergence factor
            if f'rsi_divergence' in features_df.columns:
                rsi_factor = features_df['rsi_divergence'] / 50  # Normalize
                mean_reversion_factors.append(rsi_factor)
            
            # Momentum divergence factor
            if f'macd_momentum_divergence' in features_df.columns:
                momentum_factor = features_df['macd_momentum_divergence']
                mean_reversion_factors.append(momentum_factor)
            
            # Regime stability factor
            regime_cols = [col for col in features_df.columns if 'regime_persistence' in col]
            if regime_cols:
                regime_stability = features_df[regime_cols].mean(axis=1) / 10  # Normalize
                mean_reversion_factors.append(regime_stability)
            
            # Combine factors
            if mean_reversion_factors:
                scores['mean_reversion_score'] = pd.concat(mean_reversion_factors, axis=1).mean(axis=1)
            
            # Trend alignment score
            trend_factors = []
            
            if f'trend_alignment' in features_df.columns:
                trend_factors.append(features_df['trend_alignment'])
            
            # RSI correlation factor
            corr_cols = [col for col in features_df.columns if 'rsi_correlation' in col]
            if corr_cols:
                avg_correlation = features_df[corr_cols].mean(axis=1)
                trend_factors.append(abs(avg_correlation))
            
            if trend_factors:
                scores['trend_alignment_score'] = pd.concat(trend_factors, axis=1).mean(axis=1)
            
            # Risk score (higher = riskier)
            risk_factors = []
            
            # Volatility factor
            vol_cols = [col for col in features_df.columns if 'volatility' in col]
            if vol_cols:
                avg_volatility = features_df[vol_cols].mean(axis=1)
                risk_factors.append(avg_volatility)
            
            # Extreme conditions factor
            extreme_cols = [col for col in features_df.columns if 'extreme' in col]
            if extreme_cols:
                extreme_conditions = features_df[extreme_cols].mean(axis=1)
                risk_factors.append(extreme_conditions)
            
            if risk_factors:
                scores['risk_score'] = pd.concat(risk_factors, axis=1).mean(axis=1)
            
            # Overall trading score
            if 'mean_reversion_score' in scores.columns and 'risk_score' in scores.columns:
                scores['overall_trading_score'] = (
                    scores['mean_reversion_score'] * 0.6 +
                    scores.get('trend_alignment_score', 0) * 0.2 -
                    scores['risk_score'] * 0.2
                )
        
        logger.info(f"✅ Created {len(scores.columns)} ensemble scores")
        return scores

def demo_feature_engineering():
    """Demonstrate advanced feature engineering"""
    
    print("🔧 ADVANCED FEATURE ENGINEERING WITH TECHNICAL INDICATORS")
    print("="*70)
    
    # Test symbols from your pairs
    symbols = ["QQQ", "TQQQ"]
    start_date = "2024-01-01"
    end_date = "2024-12-31"
    
    print(f"📊 Creating features for: {symbols}")
    print(f"📅 Period: {start_date} to {end_date}")
    
    try:
        # Initialize feature engine
        config = FeatureConfig(
            lookback_windows=[5, 10, 20],
            momentum_windows=[5, 10, 20],
            correlation_window=20
        )
        
        engine = TechnicalIndicatorFeatureEngine(config)
        
        # Create comprehensive features
        features_df = engine.create_comprehensive_features(symbols, start_date, end_date)
        
        if not features_df.empty:
            print(f"\n✅ Created {len(features_df.columns)} features across {len(features_df)} observations")
            
            # Show feature categories
            feature_categories = {
                'Individual Symbol': [col for col in features_df.columns if any(s in col for s in symbols) and 'rsi' in col or 'sma' in col or 'macd' in col],
                'Cross-Symbol': [col for col in features_df.columns if 'divergence' in col or 'correlation' in col or 'alignment' in col],
                'Regime': [col for col in features_df.columns if 'regime' in col],
                'Momentum': [col for col in features_df.columns if 'momentum' in col and 'regime' not in col],
                'Volatility': [col for col in features_df.columns if 'volatility' in col or 'stability' in col]
            }
            
            print(f"\n📋 FEATURE CATEGORIES:")
            for category, cols in feature_categories.items():
                print(f"   {category}: {len(cols)} features")
            
            # Create ensemble scores
            scores_df = engine.create_ensemble_score(features_df, symbols)
            
            print(f"\n🎯 ENSEMBLE SCORES:")
            for col in scores_df.columns:
                if not scores_df[col].isna().all():
                    mean_score = scores_df[col].mean()
                    std_score = scores_df[col].std()
                    print(f"   {col}: μ={mean_score:.3f}, σ={std_score:.3f}")
            
            # Save results
            features_df.to_csv("technical_indicator_features.csv")
            scores_df.to_csv("ensemble_trading_scores.csv")
            
            # Show sample data
            print(f"\n📊 SAMPLE FEATURES (last 5 days):")
            print(features_df.tail().round(3))
            
            print(f"\n🎯 SAMPLE ENSEMBLE SCORES (last 5 days):")
            print(scores_df.tail().round(3))
            
            print(f"\n📁 Files saved:")
            print(f"   • technical_indicator_features.csv ({len(features_df.columns)} features)")
            print(f"   • ensemble_trading_scores.csv ({len(scores_df.columns)} scores)")
            
            # Feature importance analysis
            print(f"\n🧠 FEATURE INSIGHTS:")
            
            # Most volatile features
            feature_volatility = features_df.std().sort_values(ascending=False)
            print(f"   Most Volatile Features:")
            for feat in feature_volatility.head(5).index:
                print(f"     • {feat}: {feature_volatility[feat]:.3f}")
            
            # Correlation analysis for pair features
            pair_features = [col for col in features_df.columns if 'divergence' in col or 'relative' in col]
            if pair_features:
                print(f"   Pair Feature Correlations:")
                corr_matrix = features_df[pair_features].corr()
                for i, feat1 in enumerate(pair_features):
                    for feat2 in pair_features[i+1:]:
                        corr = corr_matrix.loc[feat1, feat2]
                        if abs(corr) > 0.5:
                            print(f"     • {feat1} ↔ {feat2}: {corr:.3f}")
            
        else:
            print("❌ No features could be created - check your data availability")
    
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "="*70)
    print("🎯 INTEGRATION WITH BACKTESTING")
    print("="*70)
    print("""
💡 These features can enhance your trading system:

1️⃣ SIGNAL ENHANCEMENT:
   • Use ensemble scores to filter trading signals
   • Weight positions by feature confidence
   • Combine multiple timeframe momentum

2️⃣ RISK MANAGEMENT:
   • Monitor regime persistence for stability
   • Use volatility features for position sizing
   • Track correlation breakdown warning

3️⃣ MARKET TIMING:
   • RSI divergence for entry timing
   • Momentum alignment for trend following
   • Regime transitions for strategy switching

🔧 NEXT STEPS:
   • Integrate with enhanced_backtesting_with_indicators.py
   • Add feature selection and importance ranking
   • Implement adaptive feature weights
   • Create real-time feature updating
    """)

if __name__ == "__main__":
    demo_feature_engineering()
