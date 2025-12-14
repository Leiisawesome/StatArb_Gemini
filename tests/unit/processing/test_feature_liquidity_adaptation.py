from core_engine.config import FeatureConfig
from core_engine.processing.features.engineer import EnhancedFeatureEngineer

def test_feature_adapt_to_liquidity_modes():
    engine = EnhancedFeatureEngineer(FeatureConfig())
    base_method = engine.config.normalization_method
    base_lookbacks = list(engine.config.lookback_periods)

    low_context = {'overall_score': 25, 'liquidity_regime': 'illiquid'}
    low_adjustments = engine.adapt_to_liquidity(low_context)
    assert low_adjustments['mode'] == 'low_liquidity'
    assert engine.config.normalization_method == 'robust'
    assert all(new >= old for new, old in zip(engine.config.lookback_periods, base_lookbacks))

    high_context = {'overall_score': 90, 'liquidity_regime': 'high_liquidity'}
    high_adjustments = engine.adapt_to_liquidity(high_context)
    assert high_adjustments['mode'] == 'high_liquidity'
    assert engine.config.normalization_method == base_method
    assert all(new <= old for new, old in zip(engine.config.lookback_periods, base_lookbacks))

    normal_context = {'overall_score': 65, 'liquidity_regime': 'normal_liquidity'}
    normal_adjustments = engine.adapt_to_liquidity(normal_context)
    assert normal_adjustments['mode'] == 'normal'
    assert engine.config.normalization_method == base_method
    assert engine.config.lookback_periods == base_lookbacks

