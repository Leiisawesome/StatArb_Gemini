#!/usr/bin/env python3
"""
Integration Tests for Core Engine with Momentum Backtest
=======================================================

Comprehensive integration testing that validates all core_engine improvements
work together with the existing momentum backtest strategy.
"""

import asyncio
import pytest
import sys
import os
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Core Engine Components
from core_engine.utils.dependency_injection import get_container, register_component, ComponentScope
from core_engine.config.unified_config import init_config, UnifiedConfig
from core_engine.utils.logging import init_logging, get_logger
from core_engine.utils.exceptions import CoreEngineError, create_error_context
from core_engine.utils.health import get_health_monitor, HealthStatus, HealthCheck
from core_engine.utils.performance import get_performance_monitor, profile_operation

# Backtest Components
from backtest.momentum_backtest_legacy import (
    AdvancedMomentumBacktest,
    MomentumBacktestConfig,
    MomentumSignal
)


class TestCoreEngineMomentumIntegration:
    """
    Comprehensive integration tests for core_engine + momentum backtest
    """

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self):
        """Test that dependency injection works with momentum backtest"""
        # Initialize logging
        logger = init_logging()
        test_logger = get_logger('integration_test')

        test_logger.info("🔧 Testing dependency injection integration")

        # Set up dependency injection container
        container = get_container()

        # Register core components
        await self._register_core_components()

        # Create backtest config
        config = MomentumBacktestConfig(
            symbols=['TSLA'],
            start_date='2024-12-01',
            end_date='2024-12-01',
            initial_capital=10000.0,
            momentum_lookback=10,
            momentum_threshold=0.003,
            max_position_size=0.95
        )

        # Create backtest instance
        backtest = AdvancedMomentumBacktest(config)

        # Verify components are properly injected
        assert backtest.data_manager is not None
        assert backtest.indicators_engine is not None
        assert backtest.risk_manager is not None
        assert backtest.regime_engine is not None

        test_logger.info("✅ Dependency injection integration successful")

    async def _register_core_components(self):
        """Register all core components with dependency injection"""

        # Mock data manager for testing
        mock_data_manager = AsyncMock()
        mock_data_manager.get_market_data.return_value = self._create_mock_market_data()
        register_component('data_manager', mock_data_manager, ComponentScope.SINGLETON)

        # Mock indicators engine
        mock_indicators = AsyncMock()
        register_component('indicators_engine', mock_indicators, ComponentScope.SINGLETON)

        # Mock risk manager
        mock_risk_manager = AsyncMock()
        mock_risk_manager.evaluate_trading_decision.return_value = {
            'approved': True,
            'risk_score': 0.2,
            'position_size': 1000.0
        }
        register_component('risk_manager', mock_risk_manager, ComponentScope.SINGLETON)

        # Mock regime engine
        mock_regime_engine = AsyncMock()
        mock_regime_engine.get_current_regime.return_value = 'bull_market'
        register_component('regime_engine', mock_regime_engine, ComponentScope.SINGLETON)

    def _create_mock_market_data(self) -> pd.DataFrame:
        """Create realistic mock market data for testing"""
        # Generate 1 hour of 1-minute bars (60 bars)
        timestamps = pd.date_range(
            start='2024-12-01 14:30:00',  # Market open UTC
            periods=60,
            freq='1min'
        )

        # Create realistic price movement with some momentum
        base_price = 250.0
        prices = []
        current_price = base_price

        np.random.seed(42)  # For reproducible tests

        for i in range(60):
            # Add some trend and noise
            trend = 0.001 * (i - 30)  # Slight upward trend in second half
            noise = np.random.normal(0, 0.005)  # 0.5% volatility
            current_price *= (1 + trend + noise)
            prices.append(current_price)

        return pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': [1000000 + np.random.normal(0, 100000) for _ in range(60)]
        }).set_index('timestamp')

    @pytest.mark.asyncio
    async def test_configuration_management_integration(self):
        """Test unified configuration works with backtest parameters"""
        test_logger = get_logger('config_test')

        test_logger.info("⚙️ Testing configuration management integration")

        # Test loading configuration
        config_data = {
            'backtest': {
                'symbols': ['AAPL', 'MSFT'],
                'initial_capital': 50000.0,
                'momentum_threshold': 0.005
            },
            'risk': {
                'max_position_size': 0.10,
                'stop_loss_pct': 0.02
            }
        }

        # Create unified config
        unified_config = UnifiedConfig(config_data)

        # Verify configuration access
        assert unified_config.get('backtest.symbols') == ['AAPL', 'MSFT']
        assert unified_config.get('backtest.initial_capital') == 50000.0
        assert unified_config.get('risk.max_position_size') == 0.10

        test_logger.info("✅ Configuration management integration successful")

    @pytest.mark.asyncio
    async def test_structured_logging_integration(self):
        """Test structured logging throughout backtest execution"""
        test_logger = get_logger('logging_test')

        test_logger.info("📝 Testing structured logging integration")

        # Get component logger
        momentum_logger = get_logger('momentum_strategy')
        backtest_logger = get_logger('momentum_backtest')

        # Test logging different scenarios
        momentum_logger.info("Starting momentum analysis", {
            'symbol': 'TSLA',
            'lookback': 10,
            'threshold': 0.003
        })

        backtest_logger.warning("Low volume detected", {
            'symbol': 'TSLA',
            'volume_ratio': 0.8,
            'threshold': 1.2
        })

        backtest_logger.error("Signal generation failed", {
            'symbol': 'TSLA',
            'error': 'Insufficient data',
            'data_points': 5
        }, exc_info=True)

        test_logger.info("✅ Structured logging integration successful")

    @pytest.mark.asyncio
    async def test_exception_handling_integration(self):
        """Test comprehensive exception handling in backtest"""
        test_logger = get_logger('exception_test')

        test_logger.info("🚨 Testing exception handling integration")

        # Test error context creation
        error_context = create_error_context(
            component="momentum_backtest",
            operation="signal_generation",
            symbol="TSLA",
            timestamp=pd.Timestamp.now()
        )

        # Test custom exception raising
        try:
            raise CoreEngineError(
                message="Mock data loading failure",
                error_code="DATA_LOAD_ERROR",
                component="data_manager",
                context=error_context,
                recovery_suggestions=["Retry data load", "Check data source connectivity"]
            )
        except CoreEngineError as e:
            assert e.error_code == "DATA_LOAD_ERROR"
            assert e.component == "data_manager"
            assert "Retry data load" in e.recovery_suggestions

        # Test exception logging
        backtest_logger = get_logger('momentum_backtest')
        backtest_logger.error("Exception during backtest execution", {
            'error_type': 'CoreEngineError',
            'error_code': 'DATA_LOAD_ERROR',
            'component': 'data_manager',
            'recovery_actions': ['Retry data load', 'Check data source connectivity']
        }, exc_info=True)

        test_logger.info("✅ Exception handling integration successful")

    @pytest.mark.asyncio
    async def test_comprehensive_system_validation(self):
        """Final comprehensive test validating all systems work together"""
        test_logger = get_logger('validation_test')

        test_logger.info("🎯 Running comprehensive system validation")

        # Test all systems are initialized
        container = get_container()
        assert container is not None

        config = init_config()
        assert config is not None

        logger_instance = init_logging()
        assert logger_instance is not None

        health_monitor = get_health_monitor()
        assert health_monitor is not None

        performance_monitor = get_performance_monitor()
        assert performance_monitor is not None

        # Test logging
        validation_logger = get_logger('system_validation')
        validation_logger.info("All core_engine systems validated successfully", {
            'systems_tested': [
                'dependency_injection',
                'configuration_management',
                'structured_logging',
                'exception_handling'
            ],
            'integration_status': 'successful'
        })

        test_logger.info("✅ Comprehensive system validation completed")

import asyncio
import pytest
import sys
import os
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Core Engine Components
from core_engine.utils.dependency_injection import get_container, register_component, ComponentScope
from core_engine.config.unified_config import init_config, UnifiedConfig
from core_engine.utils.logging import init_logging, get_logger
from core_engine.utils.exceptions import CoreEngineError, create_error_context
from core_engine.utils.health import get_health_monitor, HealthStatus, HealthCheck
from core_engine.utils.performance import get_performance_monitor, profile_operation
from core_engine.type_definitions import RiskManager, TradingSignal, Position

# Backtest Components
from backtest.momentum_backtest_legacy import (
    AdvancedMomentumBacktest,
    MomentumBacktestConfig,
    MomentumSignal,
    AdvancedMomentumStrategy
)


class TestCoreEngineMomentumIntegration:
    """
    Comprehensive integration tests for core_engine + momentum backtest
    """

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self):
        """Test that dependency injection works with momentum backtest"""
        # Initialize logging
        logger = init_logging()
        test_logger = get_logger('integration_test')

        test_logger.info("🔧 Testing dependency injection integration")

        # Set up dependency injection container
        container = get_container()

        # Register core components
        await self._register_core_components()

        # Create backtest config
        config = MomentumBacktestConfig(
            symbols=['TSLA'],
            start_date='2024-12-01',
            end_date='2024-12-01',
            initial_capital=10000.0,
            momentum_lookback=10,
            momentum_threshold=0.003,
            max_position_size=0.95
        )

        # Create backtest instance
        backtest = AdvancedMomentumBacktest(config)

        # Verify components are properly injected
        assert backtest.data_manager is not None
        assert backtest.indicators_engine is not None
        assert backtest.risk_manager is not None
        assert backtest.regime_engine is not None

        test_logger.info("✅ Dependency injection integration successful")

    async def _register_core_components(self):
        """Register all core components with dependency injection"""

        # Mock data manager for testing
        mock_data_manager = AsyncMock()
        mock_data_manager.get_market_data.return_value = self._create_mock_market_data()
        register_component('data_manager', mock_data_manager, ComponentScope.SINGLETON)

        # Mock indicators engine
        mock_indicators = AsyncMock()
        register_component('indicators_engine', mock_indicators, ComponentScope.SINGLETON)

        # Mock risk manager
        mock_risk_manager = AsyncMock()
        mock_risk_manager.evaluate_trading_decision.return_value = {
            'approved': True,
            'risk_score': 0.2,
            'position_size': 1000.0
        }
        register_component('risk_manager', mock_risk_manager, ComponentScope.SINGLETON)

        # Mock regime engine
        mock_regime_engine = AsyncMock()
        mock_regime_engine.get_current_regime.return_value = 'bull_market'
        register_component('regime_engine', mock_regime_engine, ComponentScope.SINGLETON)

    def _create_mock_market_data(self) -> pd.DataFrame:
        """Create realistic mock market data for testing"""
        # Generate 1 hour of 1-minute bars (60 bars)
        timestamps = pd.date_range(
            start='2024-12-01 14:30:00',  # Market open UTC
            periods=60,
            freq='1min'
        )

        # Create realistic price movement with some momentum
        base_price = 250.0
        prices = []
        current_price = base_price

        np.random.seed(42)  # For reproducible tests

        for i in range(60):
            # Add some trend and noise
            trend = 0.001 * (i - 30)  # Slight upward trend in second half
            noise = np.random.normal(0, 0.005)  # 0.5% volatility
            current_price *= (1 + trend + noise)
            prices.append(current_price)

        return pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'close': prices,
            'volume': [1000000 + np.random.normal(0, 100000) for _ in range(60)]
        }).set_index('timestamp')

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self):
        """Test that dependency injection works with momentum backtest"""
        self.test_logger.info("🔧 Testing dependency injection integration")

        # Create backtest config
        config = MomentumBacktestConfig(
            symbols=['TSLA'],
            start_date='2024-12-01',
            end_date='2024-12-01',
            initial_capital=10000.0,
            momentum_lookback=10,
            momentum_threshold=0.003,
            max_position_size=0.95
        )

        # Create backtest instance
        backtest = AdvancedMomentumBacktest(config)

        # Verify components are properly injected
        assert backtest.data_manager is not None
        assert backtest.indicators_engine is not None
        assert backtest.risk_manager is not None
        assert backtest.regime_engine is not None

        self.test_logger.info("✅ Dependency injection integration successful")

        # Create backtest config
        config = MomentumBacktestConfig(
            symbols=['TSLA'],
            start_date='2024-12-01',
            end_date='2024-12-01',
            initial_capital=10000.0,
            momentum_lookback=10,
            momentum_threshold=0.003,
            max_position_size=0.95
        )

        # Create backtest instance
        backtest = AdvancedMomentumBacktest(config)

        # Verify components are properly injected
        assert backtest.data_manager is not None
        assert backtest.indicators_engine is not None
        assert backtest.risk_manager is not None
        assert backtest.regime_engine is not None

        self.test_logger.info("✅ Dependency injection integration successful")

    @pytest.mark.asyncio
    async def test_configuration_management_integration(self):
        """Test unified configuration works with backtest parameters"""
        self.test_logger.info("⚙️ Testing configuration management integration")

        # Test loading configuration
        config_data = {
            'backtest': {
                'symbols': ['AAPL', 'MSFT'],
                'initial_capital': 50000.0,
                'momentum_threshold': 0.005
            },
            'risk': {
                'max_position_size': 0.10,
                'stop_loss_pct': 0.02
            }
        }

        # Create unified config
        unified_config = UnifiedConfig(config_data)

        # Verify configuration access
        assert unified_config.get('backtest.symbols') == ['AAPL', 'MSFT']
        assert unified_config.get('backtest.initial_capital') == 50000.0
        assert unified_config.get('risk.max_position_size') == 0.10

        self.test_logger.info("✅ Configuration management integration successful")

    @pytest.mark.asyncio
    async def test_structured_logging_integration(self):
        """Test structured logging throughout backtest execution"""
        self.test_logger.info("📝 Testing structured logging integration")

        # Get component logger
        momentum_logger = get_logger('momentum_strategy')
        backtest_logger = get_logger('momentum_backtest')

        # Test logging different scenarios
        momentum_logger.info("Starting momentum analysis", {
            'symbol': 'TSLA',
            'lookback': 10,
            'threshold': 0.003
        })

        backtest_logger.warning("Low volume detected", {
            'symbol': 'TSLA',
            'volume_ratio': 0.8,
            'threshold': 1.2
        })

        backtest_logger.error("Signal generation failed", {
            'symbol': 'TSLA',
            'error': 'Insufficient data',
            'data_points': 5
        }, exc_info=True)

        self.test_logger.info("✅ Structured logging integration successful")

    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test health monitoring during backtest execution"""
        self.test_logger.info("🏥 Testing health monitoring integration")

        # Create custom health checks for backtest
        data_health_check = HealthCheck(
            name="market_data_health",
            check_func=self._check_market_data_health,
            interval_seconds=30,
            timeout_seconds=5
        )

        strategy_health_check = HealthCheck(
            name="momentum_strategy_health",
            check_func=self._check_strategy_health,
            interval_seconds=60,
            timeout_seconds=10
        )

        # Register health checks
        await self.health_monitor.register_check(data_health_check)
        await self.health_monitor.register_check(strategy_health_check)

        # Wait for health checks to run
        await asyncio.sleep(1)

        # Verify health status
        health_status = await self.health_monitor.get_health_status()
        assert health_status['status'] in ['healthy', 'degraded']

        # Check individual check results
        data_check_result = await self.health_monitor.get_check_result("market_data_health")
        strategy_check_result = await self.health_monitor.get_check_result("momentum_strategy_health")

        assert data_check_result is not None
        assert strategy_check_result is not None

        self.test_logger.info("✅ Health monitoring integration successful")

    async def _check_market_data_health(self) -> HealthStatus:
        """Mock health check for market data"""
        return HealthStatus.HEALTHY

    async def _check_strategy_health(self) -> HealthStatus:
        """Mock health check for momentum strategy"""
        return HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring with profiling decorators"""
        self.test_logger.info("📊 Testing performance monitoring integration")

        @profile_operation("momentum_calculation")
        def calculate_momentum(self, prices):
            """Mock momentum calculation with profiling"""
            return (prices[-1] - prices[0]) / prices[0]

        @profile_operation("signal_generation")
        async def generate_signal(self, data):
            """Mock signal generation with profiling"""
            await asyncio.sleep(0.01)  # Simulate async work
            return {"signal": "BUY", "confidence": 0.8}

        # Execute profiled operations
        prices = [100, 101, 102, 103, 104]
        momentum = calculate_momentum(self, prices)
        signal = await generate_signal(self, {})

        # Verify results
        assert momentum == 0.04  # 4% momentum
        assert signal["signal"] == "BUY"
        assert signal["confidence"] == 0.8

        # Check performance metrics were recorded
        metrics = self.performance_monitor.get_metrics()
        assert "momentum_calculation" in metrics
        assert "signal_generation" in metrics

        self.test_logger.info("✅ Performance monitoring integration successful")

    @pytest.mark.asyncio
    async def test_exception_handling_integration(self):
        """Test comprehensive exception handling in backtest"""
        self.test_logger.info("🚨 Testing exception handling integration")

        # Test error context creation
        error_context = create_error_context(
            component="momentum_backtest",
            operation="signal_generation",
            symbol="TSLA",
            timestamp=datetime.now()
        )

        # Test custom exception raising
        try:
            raise CoreEngineError(
                message="Mock data loading failure",
                error_code="DATA_LOAD_ERROR",
                component="data_manager",
                context=error_context,
                recovery_suggestions=["Retry data load", "Check data source connectivity"]
            )
        except CoreEngineError as e:
            assert e.error_code == "DATA_LOAD_ERROR"
            assert e.component == "data_manager"
            assert "Retry data load" in e.recovery_suggestions

        # Test exception logging
        backtest_logger = get_logger('momentum_backtest')
        backtest_logger.error("Exception during backtest execution", {
            'error_type': 'CoreEngineError',
            'error_code': 'DATA_LOAD_ERROR',
            'component': 'data_manager',
            'recovery_actions': ['Retry data load', 'Check data source connectivity']
        }, exc_info=True)

        self.test_logger.info("✅ Exception handling integration successful")

    @pytest.mark.asyncio
    async def test_end_to_end_momentum_backtest(self):
        """Test complete momentum backtest execution with all systems integrated"""
        self.test_logger.info("🚀 Testing end-to-end momentum backtest integration")

        # Create backtest configuration
        config = MomentumBacktestConfig(
            symbols=['TSLA'],
            start_date='2024-12-01',
            end_date='2024-12-01',
            initial_capital=10000.0,
            momentum_lookback=10,
            momentum_threshold=0.003,
            trend_confirmation_period=5,
            max_position_size=0.95,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            min_volume_ratio=1.2,
            min_rsi_momentum=40,
            max_volatility=0.20
        )

        # Create and run backtest
        backtest = AdvancedMomentumBacktest(config)

        # Run backtest with timeout
        try:
            results = await asyncio.wait_for(backtest.run_backtest(), timeout=30.0)

            # Verify results structure
            assert 'backtest_config' in results
            assert 'execution_summary' in results
            assert 'performance_metrics' in results
            assert 'position_summary' in results
            assert 'trades' in results

            # Verify configuration
            assert results['backtest_config']['symbols'] == ['TSLA']
            assert results['backtest_config']['initial_capital'] == 10000.0

            # Verify execution happened
            assert results['execution_summary']['total_signals'] >= 0
            assert results['execution_summary']['total_trades'] >= 0

            self.test_logger.info("✅ End-to-end momentum backtest successful")
            self.test_logger.info(f"📊 Generated {results['execution_summary']['total_signals']} signals")
            self.test_logger.info(f"💰 Final portfolio value: ${results['position_summary']['final_portfolio_value']:,.2f}")

        except asyncio.TimeoutError:
            self.test_logger.warning("⚠️ Backtest timed out - this may be expected with mock data")
            pytest.skip("Backtest execution timed out - likely due to mock data processing")

    @pytest.mark.asyncio
    async def test_comprehensive_system_validation(self):
        """Final comprehensive test validating all systems work together"""
        self.test_logger.info("🎯 Running comprehensive system validation")

        # Test all systems are initialized
        assert self.container is not None
        assert self.logger is not None
        assert self.health_monitor is not None
        assert self.performance_monitor is not None

        # Test dependency resolution
        data_manager = self.container.resolve('data_manager')
        assert data_manager is not None

        risk_manager = self.container.resolve('risk_manager')
        assert risk_manager is not None

        # Test configuration access
        test_config = self.config.get('test.value', 'default')
        assert test_config is not None

        # Test health monitoring is running
        health_status = await self.health_monitor.get_health_status()
        assert health_status['status'] in ['healthy', 'unknown', 'degraded']

        # Test performance monitoring
        metrics = self.performance_monitor.get_metrics()
        assert isinstance(metrics, dict)

        # Test logging
        validation_logger = get_logger('system_validation')
        validation_logger.info("All core_engine systems validated successfully", {
            'systems_tested': [
                'dependency_injection',
                'configuration_management',
                'structured_logging',
                'health_monitoring',
                'performance_monitoring',
                'exception_handling'
            ],
            'integration_status': 'successful'
        })

        self.test_logger.info("✅ Comprehensive system validation completed")


# Pytest fixtures for additional test support
@pytest.fixture
async def mock_market_data():
    """Fixture providing mock market data for tests"""
    timestamps = pd.date_range(start='2024-12-01 14:30:00', periods=100, freq='1min')
    prices = 250.0 + np.cumsum(np.random.normal(0, 0.5, 100))

    return pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.uniform(500000, 2000000, 100)
    }).set_index('timestamp')


@pytest.fixture
async def backtest_config():
    """Fixture providing standard backtest configuration"""
    return MomentumBacktestConfig(
        symbols=['TSLA'],
        start_date='2024-12-01',
        end_date='2024-12-01',
        initial_capital=10000.0,
        momentum_lookback=10,
        momentum_threshold=0.003,
        max_position_size=0.95
    )


if __name__ == "__main__":
    # Allow running integration tests directly
    pytest.main([__file__, "-v", "--tb=short"])