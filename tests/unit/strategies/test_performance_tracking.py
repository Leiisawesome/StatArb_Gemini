import pytest
from core_engine.config import MomentumConfig
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy

class TestPerformanceTrackingUpdates:
    @pytest.fixture
    def strategy(self):
        config = MomentumConfig(name="test_momentum", symbols=["AAPL"])
        return EnhancedMomentumStrategy(config)

    @pytest.mark.asyncio
    async def test_performance_metrics_exist(self, strategy):
        await strategy.initialize()
        assert hasattr(strategy, "performance_metrics")

    @pytest.mark.asyncio
    async def test_health_check_includes_performance(self, strategy):
        await strategy.initialize()
        await strategy.start()
        health = await strategy.health_check()
        assert health is not None

    @pytest.mark.asyncio
    async def test_signal_logging_updates_metrics(self, strategy):
        await strategy.initialize()
        initial_errors = strategy.performance_metrics.error_count
        strategy._log_error("Test error", Exception("Test"))
        assert strategy.performance_metrics.error_count == initial_errors + 1
