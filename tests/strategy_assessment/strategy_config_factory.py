"""
Strategy Config Factory
=======================

Factory for creating strategy-specific configurations for backtesting.

This factory enables the strategy tester to instantiate strategies with their
proper configuration classes instead of generic StrategyConfig.

Author: StatArb_Gemini Phase 3 Optimization
Version: 1.0.0
"""

import logging
from typing import List

# Import strategy-specific configs
from core_engine.trading.strategies.implementations.statistical_arbitrage.enhanced_statistical_arbitrage import (
    StatisticalArbitrageConfig
)
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import (
    MomentumConfig
)
from core_engine.trading.strategies.implementations.mean_reversion.enhanced_mean_reversion import (
    MeanReversionConfig
)
from core_engine.trading.strategies.implementations.pairs_trading.enhanced_pairs_trading import (
    PairsConfig as PairsTradingConfig  # Renamed for consistency
)
from core_engine.trading.strategies.implementations.trend_following.enhanced_trend_following import (
    TrendFollowingConfig
)
from core_engine.trading.strategies.implementations.breakout.enhanced_breakout import (
    BreakoutConfig
)
from core_engine.trading.strategies.implementations.volatility.enhanced_volatility import (
    VolatilityConfig
)
from core_engine.trading.strategies.implementations.arbitrage.enhanced_arbitrage import (
    ArbitrageConfig
)
from core_engine.trading.strategies.implementations.factor.enhanced_factor import (
    FactorConfig
)
from core_engine.trading.strategies.implementations.multi_asset.enhanced_multi_asset import (
    MultiAssetConfig
)
from core_engine.type_definitions.strategy import StrategyType

logger = logging.getLogger(__name__)


class StrategyConfigFactory:
    """
    Factory for creating strategy-specific configurations
    
    This factory provides optimized default configurations for each strategy type,
    with the ability to override any parameter via kwargs.
    """
    
    @staticmethod
    def create_config(
        strategy_type: str,
        symbols: List[str],
        **kwargs
    ):
        """
        Create strategy-specific configuration
        
        Args:
            strategy_type: Name of the strategy (e.g., 'statistical_arbitrage')
            symbols: List of symbols for the strategy
            **kwargs: Additional parameters to override defaults
        
        Returns:
            Strategy-specific config instance
        """
        
        strategy_type_lower = strategy_type.lower().replace('_', ' ').replace('-', ' ')
        
        if 'statistical' in strategy_type_lower or 'stat arb' in strategy_type_lower:
            return StrategyConfigFactory.create_statistical_arbitrage_config(symbols, **kwargs)
        
        elif 'momentum' in strategy_type_lower:
            return StrategyConfigFactory.create_momentum_config(symbols, **kwargs)
        
        elif 'mean reversion' in strategy_type_lower or 'mean_reversion' in strategy_type_lower:
            return StrategyConfigFactory.create_mean_reversion_config(symbols, **kwargs)
        
        elif 'pairs' in strategy_type_lower:
            return StrategyConfigFactory.create_pairs_trading_config(symbols, **kwargs)
        
        elif 'trend' in strategy_type_lower:
            return StrategyConfigFactory.create_trend_following_config(symbols, **kwargs)
        
        elif 'breakout' in strategy_type_lower:
            return StrategyConfigFactory.create_breakout_config(symbols, **kwargs)
        
        elif 'volatility' in strategy_type_lower:
            return StrategyConfigFactory.create_volatility_config(symbols, **kwargs)
        
        elif 'arbitrage' in strategy_type_lower and 'statistical' not in strategy_type_lower:
            return StrategyConfigFactory.create_arbitrage_config(symbols, **kwargs)
        
        elif 'factor' in strategy_type_lower:
            return StrategyConfigFactory.create_factor_config(symbols, **kwargs)
        
        elif 'multi' in strategy_type_lower or 'asset' in strategy_type_lower:
            return StrategyConfigFactory.create_multi_asset_config(symbols, **kwargs)
        
        else:
            logger.warning(f"Unknown strategy type '{strategy_type}', using StatisticalArbitrageConfig as fallback")
            return StrategyConfigFactory.create_statistical_arbitrage_config(symbols, **kwargs)
    
    @staticmethod
    def create_statistical_arbitrage_config(
        symbols: List[str],
        **kwargs
    ) -> StatisticalArbitrageConfig:
        """
        Create optimized Statistical Arbitrage configuration
        
        This configuration is based on Phase 3 optimization research:
        - Cointegration analysis for pair selection
        - Dynamic hedge ratios via Kalman filters
        - Error Correction Model for timing
        - Risk parity position sizing
        """
        
        # PROFESSIONAL APPROACH: Load pre-selected cointegrated pairs
        # These pairs were identified using offline analysis on daily data
        preloaded_pairs = kwargs.get('preloaded_pairs', None)
        use_preloaded_pairs = kwargs.get('use_preloaded_pairs', False)
        
        # If no preloaded pairs provided but use_preloaded_pairs=True, load from results file
        if use_preloaded_pairs and preloaded_pairs is None:
            import json
            import os
            
            pairs_file = os.path.join(os.path.dirname(__file__), 
                                     'results', 'cointegrated_pairs_2024.json')
            
            if os.path.exists(pairs_file):
                with open(pairs_file, 'r') as f:
                    pairs_data = json.load(f)
                    # Filter pairs based on symbols provided
                    all_pairs = pairs_data.get('pairs', [])
                    
                    preloaded_pairs = []
                    for pair_info in all_pairs:
                        asset1 = pair_info.get('asset1')
                        asset2 = pair_info.get('asset2')
                        
                        if asset1 in symbols and asset2 in symbols:
                            # Convert to expected format
                            preloaded_pairs.append({
                                'pair': (asset1, asset2),
                                'hedge_ratio': pair_info.get('hedge_ratio'),
                                'p_value': pair_info.get('cointegration_pvalue'),
                                'correlation': pair_info.get('correlation'),
                                'half_life': pair_info.get('half_life'),
                                'spread_mean': pair_info.get('spread_mean'),
                                'spread_std': pair_info.get('spread_std'),
                                'quality_score': pair_info.get('quality_score'),
                                'is_cointegrated': True
                            })
                    
                    logger.info(f"📊 Loaded {len(preloaded_pairs)} pre-selected pairs from {pairs_file}")
            else:
                logger.warning(f"⚠️ Pairs file not found: {pairs_file}, will use live testing")
                use_preloaded_pairs = False
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'statistical_arbitrage_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Statistical Arbitrage'),
            'strategy_type': StrategyType.STATISTICAL_ARBITRAGE,
            
            # Asset universe (from test symbols)
            'asset_universe': symbols,
            
            # PRE-LOADED PAIRS: Professional backtesting approach
            'preloaded_pairs': preloaded_pairs,
            'use_preloaded_pairs': use_preloaded_pairs,
            
            # Cointegration parameters (used only if not using preloaded pairs)
            'cointegration_lookback': kwargs.get('cointegration_lookback', 1000),  # ~2.5 trading days for 1-min data
            'min_cointegration_pvalue': kwargs.get('min_cointegration_pvalue', 0.05),  # 5% significance
            'min_correlation': kwargs.get('min_correlation', 0.70),  # 70% minimum correlation
            
            # Spread trading parameters (standard configuration)
            # Note: Extensive testing showed Statistical Arbitrage is not viable with
            # twin ETFs (SPY/IVV/VOO) due to artificial cointegration. Strategy requires
            # real economic relationships between assets and longer-term spreads.
            # These are reasonable starting parameters for proper pairs.
            'entry_zscore_threshold': kwargs.get('entry_zscore_threshold', 2.0),
            'exit_zscore_threshold': kwargs.get('exit_zscore_threshold', 0.5),
            'stop_loss_zscore': kwargs.get('stop_loss_zscore', 3.0),
            
            # Position sizing
            'max_spread_positions': kwargs.get('max_spread_positions', 5),
            'base_position_size': kwargs.get('base_position_size', 0.02),  # 2% per spread
            'position_size_method': kwargs.get('position_size_method', 'risk_parity'),
            
            # Risk management
            'max_holding_period': kwargs.get('max_holding_period', 20),  # 20 days max
            'correlation_decay_factor': kwargs.get('correlation_decay_factor', 0.95),
            
            # Model parameters
            'kalman_filter_enabled': kwargs.get('kalman_filter_enabled', True),
            'ou_process_modeling': kwargs.get('ou_process_modeling', True),
            'error_correction_model': kwargs.get('error_correction_model', True),
            
            # Performance settings
            'enable_monitoring': kwargs.get('enable_monitoring', True),
            'rebalance_frequency': kwargs.get('rebalance_frequency', 'daily'),
            
        }
        
        # Note: StatisticalArbitrageConfig extends StrategyConfig but dataclass doesn't properly 
        # pass through base class __init__ params. We only pass StatArb-specific params.
        # Base params like min_signal_confidence, max_position_size, etc. will use StrategyConfig defaults.
        
        if use_preloaded_pairs and preloaded_pairs:
            logger.info(f"📊 Created StatArb config with {len(preloaded_pairs)} pre-selected pairs (PROFESSIONAL MODE)")
        else:
            logger.info(f"📊 Created StatArb config with {len(symbols)} assets for live cointegration testing")
        
        return StatisticalArbitrageConfig(**config_params)
    
    @staticmethod
    def create_momentum_config(
        symbols: List[str],
        **kwargs
    ) -> MomentumConfig:
        """Create optimized Momentum configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'momentum_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Momentum'),
            'strategy_type': StrategyType.MOMENTUM,
            'symbols': symbols,
            
            # Momentum parameters (Phase 4.3: LONGER PERIODS for 5-MINUTE DATA)
            # Using same bar counts (10, 20, 50) on 5-min data = (50, 100, 250) minutes
            # This gives more robust momentum calculation and fewer, higher-quality signals
            'short_period': kwargs.get('short_period', 10),      # 50 minutes (10 x 5min)
            'medium_period': kwargs.get('medium_period', 20),    # 100 minutes (20 x 5min)
            'long_period': kwargs.get('long_period', 50),        # 250 minutes (50 x 5min)
            'momentum_threshold': kwargs.get('momentum_threshold', 0.005),  # 0.5% (optimal balance)
            
            # Trend quality indicators (BALANCED)
            'adx_period': kwargs.get('adx_period', 14),
            'adx_threshold': kwargs.get('adx_threshold', 25.0),  # Moderate trend required
            
            # Volume confirmation (BALANCED)
            'volume_ma_period': kwargs.get('volume_ma_period', 20),
            'volume_threshold': kwargs.get('volume_threshold', 0.8),  # 80% of average
            
            # Multi-timeframe analysis
            'primary_timeframe': kwargs.get('primary_timeframe', '5min'),
            'enable_multi_timeframe': kwargs.get('enable_multi_timeframe', True),
            
            # Breakout detection (DISABLED FOR INITIAL TEST)
            'enable_breakout_detection': kwargs.get('enable_breakout_detection', False),
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.03),
            'max_position_pct': kwargs.get('max_position_pct', 0.08),
            'momentum_scaling': kwargs.get('momentum_scaling', True),
            
            # Risk management (TIGHTER FOR 1-MINUTE DATA)
            'momentum_stop_pct': kwargs.get('momentum_stop_pct', 0.02),      # 2% stop (was 3%)
            'trailing_stop_pct': kwargs.get('trailing_stop_pct', 0.01),     # 1% trailing (was 2%)
            'profit_target_ratio': kwargs.get('profit_target_ratio', 2.0),  # 2:1 R/R (was 3:1)
        }
        
        logger.info(f"📈 Created Momentum config with {len(symbols)} symbols")
        
        return MomentumConfig(**config_params)
    
    @staticmethod
    def create_mean_reversion_config(
        symbols: List[str],
        **kwargs
    ) -> MeanReversionConfig:
        """Create optimized Mean Reversion configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'mean_reversion_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Mean Reversion'),
            'strategy_type': StrategyType.MEAN_REVERSION,
            'symbols': symbols,
            
            # Mean reversion parameters
            'lookback_period': kwargs.get('lookback_period', 20),
            'zscore_entry_threshold': kwargs.get('zscore_entry_threshold', 2.0),
            'zscore_exit_threshold': kwargs.get('zscore_exit_threshold', 0.5),
            
            # Technical indicators
            'bollinger_period': kwargs.get('bollinger_period', 20),
            'bollinger_std': kwargs.get('bollinger_std', 2.0),
            'rsi_period': kwargs.get('rsi_period', 14),
            'rsi_oversold': kwargs.get('rsi_oversold', 30.0),
            'rsi_overbought': kwargs.get('rsi_overbought', 70.0),
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.02),
            'max_position_pct': kwargs.get('max_position_pct', 0.05),
            
            # Risk management
            'stop_loss_atr_multiple': kwargs.get('stop_loss_atr_multiple', 2.0),
            'profit_target_ratio': kwargs.get('profit_target_ratio', 2.0),
            'max_holding_period': kwargs.get('max_holding_period', 10),
            
            # Regime filtering (CRITICAL - must be configurable!)
            'enable_regime_filter': kwargs.get('enable_regime_filter', True),
        }
        
        logger.info(f"Created Mean Reversion config with {len(symbols)} symbols")
        logger.info(f"  Z-Score Entry: {config_params['zscore_entry_threshold']}")
        logger.info(f"  RSI Thresholds: {config_params['rsi_oversold']}/{config_params['rsi_overbought']}")
        logger.info(f"  Regime Filter: {'ENABLED' if config_params['enable_regime_filter'] else 'DISABLED'}")
        
        return MeanReversionConfig(**config_params)
    
    @staticmethod
    def create_pairs_trading_config(
        symbols: List[str],
        **kwargs
    ) -> PairsTradingConfig:
        """Create optimized Pairs Trading configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'pairs_trading_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Pairs Trading'),
            'strategy_type': StrategyType.PAIRS_TRADING,
            
            # Pair selection parameters
            'min_correlation': kwargs.get('min_correlation', 0.7),
            'cointegration_pvalue': kwargs.get('cointegration_pvalue', 0.05),
            'lookback_period': kwargs.get('lookback_period', 60),  # Shorter for 1-min data
            
            # Spread trading parameters
            'entry_zscore': kwargs.get('entry_zscore', 2.0),
            'exit_zscore': kwargs.get('exit_zscore', 0.5),
            'stop_loss_zscore': kwargs.get('stop_loss_zscore', 3.5),
            
            # Position sizing
            'max_pairs': kwargs.get('max_pairs', 3),  # Fewer pairs for 1-min data
            'position_size_pct': kwargs.get('position_size_pct', 0.03),
            
            # Risk management
            'max_holding_period': kwargs.get('max_holding_period', 20),  # Shorter for 1-min
            'correlation_threshold': kwargs.get('correlation_threshold', 0.5),
            
            # Asset universe
            'asset_universe': kwargs.get('asset_universe', symbols),
        }
        
        logger.info(f"👥 Created Pairs Trading config with {len(symbols)} symbols")
        logger.info(f"  Min Correlation: {config_params['min_correlation']}")
        logger.info(f"  Entry Z-Score: {config_params['entry_zscore']}")
        logger.info(f"  Max Pairs: {config_params['max_pairs']}")
        
        return PairsTradingConfig(**config_params)
    
    @staticmethod
    def create_trend_following_config(
        symbols: List[str],
        **kwargs
    ) -> TrendFollowingConfig:
        """Create optimized Trend Following configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'trend_following_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Trend Following'),
            'strategy_type': StrategyType.TREND_FOLLOWING,
            'symbols': symbols,
            
            # Moving average parameters
            'fast_ma_period': kwargs.get('fast_ma_period', 12),
            'slow_ma_period': kwargs.get('slow_ma_period', 26),
            'signal_ma_period': kwargs.get('signal_ma_period', 9),
            'ma_type': kwargs.get('ma_type', 'EMA'),
            
            # MACD parameters
            'macd_fast': kwargs.get('macd_fast', 12),
            'macd_slow': kwargs.get('macd_slow', 26),
            'macd_signal': kwargs.get('macd_signal', 9),
            
            # Trend strength indicators
            'adx_period': kwargs.get('adx_period', 14),
            'adx_threshold': kwargs.get('adx_threshold', 25.0),
            
            # Multi-timeframe analysis
            'primary_timeframe': kwargs.get('primary_timeframe', '1min'),
            'enable_multi_timeframe': kwargs.get('enable_multi_timeframe', False),  # Disabled for 1-min testing
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.04),
            'max_position_pct': kwargs.get('max_position_pct', 0.10),
            'trend_scaling': kwargs.get('trend_scaling', True),
            
            # Risk management
            'atr_period': kwargs.get('atr_period', 14),
            'atr_stop_multiplier': kwargs.get('atr_stop_multiplier', 2.0),
            'trailing_stop_pct': kwargs.get('trailing_stop_pct', 0.02),
            'profit_target_ratio': kwargs.get('profit_target_ratio', 3.0),
            'max_holding_period': kwargs.get('max_holding_period', 50),
            
            # Trend filtering
            'enable_trend_filter': kwargs.get('enable_trend_filter', True),
            'min_trend_duration': kwargs.get('min_trend_duration', 5),
            'trend_reversal_threshold': kwargs.get('trend_reversal_threshold', 0.02),
            
            # Volatility filtering
            'enable_volatility_filter': kwargs.get('enable_volatility_filter', True),
            'volatility_lookback': kwargs.get('volatility_lookback', 20),
            'max_volatility_percentile': kwargs.get('max_volatility_percentile', 0.8),
        }
        
        logger.info(f"📊 Created Trend Following config with {len(symbols)} symbols")
        logger.info(f"  MA Periods: {config_params['fast_ma_period']}/{config_params['slow_ma_period']} ({config_params['ma_type']})")
        logger.info(f"  ADX Threshold: {config_params['adx_threshold']}")
        logger.info(f"  Filters: Trend={'ENABLED' if config_params['enable_trend_filter'] else 'DISABLED'}, "
                   f"Vol={'ENABLED' if config_params['enable_volatility_filter'] else 'DISABLED'}")
        
        return TrendFollowingConfig(**config_params)
    
    @staticmethod
    def create_breakout_config(
        symbols: List[str],
        **kwargs
    ) -> BreakoutConfig:
        """Create optimized Breakout configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'breakout_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Breakout'),
            'strategy_type': StrategyType.BREAKOUT,
            'symbols': symbols,
            
            # Breakout detection parameters (using actual BreakoutConfig field names)
            'lookback_period': kwargs.get('lookback_period', 20),
            'breakout_threshold': kwargs.get('breakout_threshold', 0.02),  # 2% breakout
            'volume_confirmation': kwargs.get('volume_confirmation', 1.5),  # 50% above average volume
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.04),
            'max_position_pct': kwargs.get('max_position_pct', 0.10),
            
            # Risk management
            'stop_loss_pct': kwargs.get('stop_loss_pct', 0.03),
            'profit_target_ratio': kwargs.get('profit_target_ratio', 2.0),
            
            # Base parameters
            'min_signal_confidence': kwargs.get('min_signal_confidence', 0.6),
        }
        
        logger.info(f"🚀 Created Breakout config with {len(symbols)} symbols")
        logger.info(f"  Lookback Period: {config_params['lookback_period']}")
        logger.info(f"  Breakout Threshold: {config_params['breakout_threshold']*100:.1f}%")
        logger.info(f"  Volume Confirmation: {config_params['volume_confirmation']:.1f}x")
        logger.info(f"  Position Size: {config_params['base_position_pct']*100:.1f}% base, {config_params['max_position_pct']*100:.1f}% max")
        
        return BreakoutConfig(**config_params)
    
    @staticmethod
    def create_volatility_config(
        symbols: List[str],
        **kwargs
    ) -> VolatilityConfig:
        """Create optimized Volatility configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'volatility_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Volatility'),
            'strategy_type': StrategyType.VOLATILITY,
            
            # Volatility parameters
            'volatility_lookback': kwargs.get('volatility_lookback', 20),
            'volatility_threshold': kwargs.get('volatility_threshold', 0.02),
            'regime_detection': kwargs.get('regime_detection', True),
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.025),
            'max_position_pct': kwargs.get('max_position_pct', 0.07),
            'volatility_scaling': kwargs.get('volatility_scaling', True),
            
            # Base parameters
            'min_signal_confidence': kwargs.get('min_signal_confidence', 0.6),
        }
        
        logger.info(f"📊 Created Volatility config with {len(symbols)} symbols")
        
        return VolatilityConfig(**config_params)
    
    @staticmethod
    def create_arbitrage_config(
        symbols: List[str],
        **kwargs
    ) -> ArbitrageConfig:
        """Create optimized Arbitrage configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'arbitrage_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Arbitrage'),
            'strategy_type': StrategyType.ARBITRAGE,
            
            # Arbitrage parameters
            'min_price_discrepancy': kwargs.get('min_spread', 0.001),
            'max_execution_time': kwargs.get('max_execution_time', 5.0),
            'confidence_threshold': kwargs.get('confidence_threshold', 0.8),
            
            # Risk management
            'max_position_pct': kwargs.get('base_position_size', 0.05),
            'transaction_cost_threshold': kwargs.get('transaction_cost_threshold', 0.0005),
            
            # Timing parameters
            'opportunity_timeout': kwargs.get('opportunity_timeout', 10.0),
            'price_update_frequency': kwargs.get('price_update_frequency', 1.0),
        }
        
        logger.info(f"⚡ Created Arbitrage config with {len(symbols)} symbols")
        
        return ArbitrageConfig(**config_params)
    
    @staticmethod
    def create_factor_config(
        symbols: List[str],
        **kwargs
    ) -> FactorConfig:
        """Create optimized Factor configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'factor_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Factor'),
            'strategy_type': StrategyType.FACTOR,
            'symbols': symbols,
            
            # Factor parameters
            'factors': kwargs.get('factors', ['momentum', 'value', 'quality']),
            'rebalance_frequency': kwargs.get('rebalance_frequency', 20),
            'factor_lookback': kwargs.get('factor_lookback', 60),
            
            # Position sizing
            'base_position_pct': kwargs.get('base_position_pct', 0.02),
            'max_position_pct': kwargs.get('max_position_pct', 0.06),
            
            # Base parameters
            'min_signal_confidence': kwargs.get('min_signal_confidence', 0.6),
        }
        
        logger.info(f"🔢 Created Factor config with {len(symbols)} symbols")
        
        return FactorConfig(**config_params)
    
    @staticmethod
    def create_multi_asset_config(
        symbols: List[str],
        **kwargs
    ) -> MultiAssetConfig:
        """Create optimized Multi-Asset configuration"""
        
        config_params = {
            'strategy_id': kwargs.get('strategy_id', 'multi_asset_v1'),
            'strategy_name': kwargs.get('strategy_name', 'Enhanced Multi-Asset'),
            'strategy_type': StrategyType.MULTI_ASSET,
            
            # Multi-asset parameters
            'rebalance_frequency': kwargs.get('rebalance_frequency', 10),
            'correlation_lookback': kwargs.get('correlation_lookback', 60),
            'max_correlation': kwargs.get('max_correlation', 0.8),
            
            # Risk management
            'portfolio_vol_target': kwargs.get('portfolio_vol_target', 0.12),
            'max_asset_weight': kwargs.get('max_asset_weight', 0.3),
            'min_asset_weight': kwargs.get('min_asset_weight', 0.05),
            
            # Base parameters
            'min_signal_confidence': kwargs.get('min_signal_confidence', 0.6),
        }
        
        logger.info(f"🌐 Created Multi-Asset config with {len(symbols)} symbols")
        
        return MultiAssetConfig(**config_params)


# Convenience function for direct config creation
def create_strategy_config(strategy_type: str, symbols: List[str], **kwargs):
    """
    Convenience function to create strategy-specific configuration
    
    Args:
        strategy_type: Strategy type (e.g., 'statistical_arbitrage')
        symbols: List of trading symbols
        **kwargs: Additional config parameters
    
    Returns:
        Strategy-specific config instance
    
    Example:
        config = create_strategy_config(
            'statistical_arbitrage',
            ['NVDA', 'TSLA', 'AAPL'],
            entry_zscore_threshold=2.5,
            exit_zscore_threshold=0.7
        )
    """
    return StrategyConfigFactory.create_config(strategy_type, symbols, **kwargs)
