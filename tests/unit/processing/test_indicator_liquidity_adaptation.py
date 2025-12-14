from core_engine.config import IndicatorConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators

def test_indicator_adapt_to_liquidity_modes():
    engine = EnhancedTechnicalIndicators(IndicatorConfig())
    base_std = engine.config.bb_std
    base_period = engine.config.bb_period
    base_volume = engine.config.volume_sma_period

    low_context = {'overall_score': 30, 'liquidity_regime': 'low_liquidity'}
    low_adjustments = engine.adapt_to_liquidity(low_context)
    assert low_adjustments['mode'] == 'low_liquidity'
    assert engine.config.bb_std >= base_std
    assert engine.config.bb_period >= base_period
    assert engine.config.volume_sma_period >= base_volume

    high_context = {'overall_score': 90, 'liquidity_regime': 'high_liquidity'}
    high_adjustments = engine.adapt_to_liquidity(high_context)
    assert high_adjustments['mode'] == 'high_liquidity'
    assert engine.config.bb_std <= base_std
    assert engine.config.volume_sma_period <= base_volume

    normal_context = {'overall_score': 65, 'liquidity_regime': 'normal_liquidity'}
    normal_adjustments = engine.adapt_to_liquidity(normal_context)
    assert normal_adjustments['mode'] == 'normal'
    assert engine.config.bb_std == base_std
    assert engine.config.bb_period == base_period
    assert engine.config.volume_sma_period == base_volume

