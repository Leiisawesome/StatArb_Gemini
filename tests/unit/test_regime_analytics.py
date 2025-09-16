import pytest
from datetime import datetime, timedelta

# Provide lightweight stubs for Phase 1/2 components so imports inside
# `core_structure.analytics.regime_analytics` succeed in the test environment.
import sys
import types

stub_mod = types.ModuleType("core_structure.components.market_regime.professional_regime_system")
setattr(stub_mod, 'get_professional_regime_system', lambda: None)
setattr(stub_mod, 'ProfessionalRegimeSystem', type('ProfessionalRegimeSystem', (object,), {}))
sys.modules['core_structure.components.market_regime.professional_regime_system'] = stub_mod

stub_mod2 = types.ModuleType("core_structure.orchestration.multi_strategy_orchestrator")
setattr(stub_mod2, 'MultiStrategyOrchestrator', type('MultiStrategyOrchestrator', (object,), {}))
setattr(stub_mod2, 'OrchestrationSession', type('OrchestrationSession', (object,), {}))
sys.modules['core_structure.orchestration.multi_strategy_orchestrator'] = stub_mod2

stub_mod3 = types.ModuleType("core_structure.components.portfolio.portfolio_manager")
setattr(stub_mod3, 'PortfolioManager', type('PortfolioManager', (object,), {}))
setattr(stub_mod3, 'PortfolioMetrics', type('PortfolioMetrics', (object,), {}))
sys.modules['core_structure.components.portfolio.portfolio_manager'] = stub_mod3

from core_structure.analytics.regime_analytics import create_regime_analytics_engine, RegimeAnalyticsEngine


@pytest.mark.asyncio
async def test_regime_engine_synthetic_generation_and_summary():
    engine = create_regime_analytics_engine(lookback_days=1, min_regime_duration=5)

    # Use a short time window for deterministic behavior
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    time_period = (start_time, end_time)

    result = await engine.analyze_regime_performance(time_period=time_period)

    # Basic assertions about result structure
    assert result.analysis_type.name == 'PERFORMANCE_ATTRIBUTION'
    assert isinstance(result.regime_performance, dict)
    assert isinstance(result.transition_analysis, list)
    assert result.data_quality_score >= 0
    assert result.analysis_confidence >= 0
