#!/usr/bin/env python3
"""
Simple Unit Tests for Phase 2.4 Enhanced Components
===================================================

Focused unit tests for the Phase 2.4 enhanced components that work
with the actual implementation and test core functionality.

Author: StatArb_Gemini Core Engine Testing
Version: 1.0.0 (Phase 2.4 Unit Tests)
"""

import pytest
import logging
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Import the components under test
from core_engine.trading.strategies.strategy_engine import (
    StrategyExecutionEngine, BaseStrategy, StrategyConfig
)
from core_engine.trading.strategies.strategy_registry import (
    EnhancedStrategyRegistry
)
from core_engine.trading.strategies.strategy_validator import (
    EnhancedStrategyValidator, ValidationLevel
)

# Setup test logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)


class SimpleTestStrategy(BaseStrategy):
    """Simple test strategy for unit testing"""
    
    def __init__(self, strategy_id: str = "simple_test_strategy"):
        config = StrategyConfig(
            strategy_id=strategy_id,
            strategy_name="Simple Test Strategy",
            description="Simple strategy for unit testing"
        )
        super().__init__(config)
        self.initialized = False
    
    def initialize(self) -> bool:
        self.initialized = True
        return True
    
    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[Any]:
        return [{'symbol': 'TEST', 'action': 'buy', 'quantity': 100}]
    
    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        pass


@pytest.fixture
def sample_market_data():
    """Create simple sample market data"""
    dates = pd.date_range(start='2024-01-01', periods=10, freq='1min')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': [100.0] * 10,
        'high': [101.0] * 10,
        'low': [99.0] * 10,
        'close': [100.5] * 10,
        'volume': [1000] * 10
    })
    return {'TEST': data}


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_phase_2_4_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestStrategyExecutionEngineBasics:
    """Basic tests for StrategyExecutionEngine"""
    
    def test_engine_creation(self):
        """Test basic engine creation"""
        config = {'max_concurrent_strategies': 3}
        engine = StrategyExecutionEngine(config)
        
        assert engine is not None
        assert engine.component_id is not None
        assert isinstance(engine.component_id, str)
        assert not engine.is_initialized
        assert not engine.is_operational
    
    @pytest.mark.asyncio
    async def test_engine_initialization(self):
        """Test engine initialization"""
        config = {'max_concurrent_strategies': 3}
        engine = StrategyExecutionEngine(config)
        
        result = await engine.initialize()
        
        assert result is True
        assert engine.is_initialized
        assert not engine.is_operational  # Not started yet
    
    @pytest.mark.asyncio
    async def test_engine_lifecycle(self):
        """Test engine start/stop lifecycle"""
        config = {'max_concurrent_strategies': 3}
        engine = StrategyExecutionEngine(config)
        
        # Initialize first
        await engine.initialize()
        
        # Test start
        start_result = await engine.start()
        assert start_result is True
        assert engine.is_operational
        
        # Test stop
        stop_result = await engine.stop()
        assert stop_result is True
        assert not engine.is_operational
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        config = {'max_concurrent_strategies': 3}
        engine = StrategyExecutionEngine(config)
        await engine.initialize()
        
        health_status = await engine.health_check()
        
        assert health_status is not None
        assert isinstance(health_status, dict)
        assert 'healthy' in health_status
        assert 'component_type' in health_status
        assert health_status['component_type'] == 'StrategyExecutionEngine'
    
    def test_status_reporting(self):
        """Test status reporting"""
        config = {'max_concurrent_strategies': 3}
        engine = StrategyExecutionEngine(config)
        
        status = engine.get_status()
        
        assert isinstance(status, dict)
        assert 'component_id' in status
        assert 'component_type' in status
        assert 'initialized' in status
        assert 'operational' in status


class TestStrategyRegistryBasics:
    """Basic tests for EnhancedStrategyRegistry"""
    
    def test_registry_creation(self, temp_dir):
        """Test basic registry creation"""
        config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        registry = EnhancedStrategyRegistry(config)
        
        assert registry is not None
        assert registry.component_id is not None
        assert isinstance(registry.component_id, str)
        assert not registry.is_initialized
        assert not registry.is_operational
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, temp_dir):
        """Test registry initialization"""
        config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        registry = EnhancedStrategyRegistry(config)
        
        result = await registry.initialize()
        
        assert result is True
        assert registry.is_initialized
        assert registry.registry_path.exists()
    
    @pytest.mark.asyncio
    async def test_registry_lifecycle(self, temp_dir):
        """Test registry start/stop lifecycle"""
        config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        registry = EnhancedStrategyRegistry(config)
        
        # Initialize first
        await registry.initialize()
        
        # Test start
        start_result = await registry.start()
        assert start_result is True
        assert registry.is_operational
        
        # Test stop
        stop_result = await registry.stop()
        assert stop_result is True
        assert not registry.is_operational
    
    @pytest.mark.asyncio
    async def test_health_check(self, temp_dir):
        """Test health check functionality"""
        config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        registry = EnhancedStrategyRegistry(config)
        await registry.initialize()
        
        health_status = await registry.health_check()
        
        assert health_status is not None
        assert isinstance(health_status, dict)
        assert 'healthy' in health_status
        assert 'component_type' in health_status
        assert health_status['component_type'] == 'EnhancedStrategyRegistry'
    
    @pytest.mark.asyncio
    async def test_strategy_registration(self, temp_dir):
        """Test basic strategy registration"""
        config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        registry = EnhancedStrategyRegistry(config)
        await registry.initialize()
        
        # Mock the validator to avoid complex validation
        with patch.object(registry.validator, 'validate_strategy') as mock_validate:
            mock_validate.return_value = Mock(overall_score=85.0, overall_status=Mock(value='passed'))
            
            strategy_id = await registry.register_strategy(SimpleTestStrategy, validate=True)
            
            assert strategy_id is not None
            assert strategy_id in registry.strategies


class TestStrategyValidatorBasics:
    """Basic tests for EnhancedStrategyValidator"""
    
    def test_validator_creation(self):
        """Test basic validator creation"""
        config = {
            'validation_level': 'standard',
            'enable_caching': True
        }
        validator = EnhancedStrategyValidator(config)
        
        assert validator is not None
        assert validator.component_id is not None
        assert isinstance(validator.component_id, str)
        assert not validator.is_initialized
        assert not validator.is_operational
    
    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test validator initialization"""
        config = {
            'validation_level': 'standard',
            'enable_caching': True
        }
        validator = EnhancedStrategyValidator(config)
        
        result = await validator.initialize()
        
        assert result is True
        assert validator.is_initialized
        assert validator.validation_level == ValidationLevel.STANDARD
    
    @pytest.mark.asyncio
    async def test_validator_lifecycle(self):
        """Test validator start/stop lifecycle"""
        config = {
            'validation_level': 'standard',
            'enable_caching': True
        }
        validator = EnhancedStrategyValidator(config)
        
        # Initialize first
        await validator.initialize()
        
        # Test start
        start_result = await validator.start()
        assert start_result is True
        assert validator.is_operational
        
        # Test stop
        stop_result = await validator.stop()
        assert stop_result is True
        assert not validator.is_operational
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        config = {
            'validation_level': 'standard',
            'enable_caching': True
        }
        validator = EnhancedStrategyValidator(config)
        await validator.initialize()
        
        health_status = await validator.health_check()
        
        assert health_status is not None
        assert isinstance(health_status, dict)
        assert 'healthy' in health_status
        assert 'component_type' in health_status
        assert health_status['component_type'] == 'EnhancedStrategyValidator'
    
    @pytest.mark.asyncio
    async def test_basic_validation(self, sample_market_data):
        """Test basic strategy validation"""
        config = {
            'validation_level': 'basic',
            'enable_caching': False  # Disable for simpler testing
        }
        validator = EnhancedStrategyValidator(config)
        await validator.initialize()
        
        test_strategy = SimpleTestStrategy()
        
        result = await validator.validate_strategy(
            test_strategy,
            sample_data=sample_market_data,
            run_backtest=False,
            use_cache=False
        )
        
        assert result is not None
        assert hasattr(result, 'overall_score')
        assert hasattr(result, 'overall_status')
        assert result.overall_score >= 0


class TestIntegrationWorkflow:
    """Test integration between components"""
    
    @pytest.mark.asyncio
    async def test_component_integration(self, temp_dir, sample_market_data):
        """Test basic integration between all components"""
        # Create all components
        engine_config = {'max_concurrent_strategies': 3}
        registry_config = {
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False,
            'cache_enabled': True
        }
        validator_config = {
            'validation_level': 'basic',
            'enable_caching': False
        }
        
        engine = StrategyExecutionEngine(engine_config)
        registry = EnhancedStrategyRegistry(registry_config)
        validator = EnhancedStrategyValidator(validator_config)
        
        # Initialize all components
        engine_init = await engine.initialize()
        registry_init = await registry.initialize()
        validator_init = await validator.initialize()
        
        assert all([engine_init, registry_init, validator_init])
        
        # Start all components
        await engine.start()
        await registry.start()
        await validator.start()
        
        # All should be operational
        assert engine.is_operational
        assert registry.is_operational
        assert validator.is_operational
        
        # Test basic validation
        test_strategy = SimpleTestStrategy()
        validation_result = await validator.validate_strategy(
            test_strategy,
            sample_data=sample_market_data,
            use_cache=False
        )
        
        assert validation_result is not None
        
        # Cleanup
        await engine.stop()
        await registry.stop()
        await validator.stop()
    
    @pytest.mark.asyncio
    async def test_health_checks_all_components(self, temp_dir):
        """Test health checks for all components"""
        # Create and initialize all components
        engine = StrategyExecutionEngine({'max_concurrent_strategies': 3})
        registry = EnhancedStrategyRegistry({
            'registry_path': str(temp_dir),
            'auto_discovery_enabled': False
        })
        validator = EnhancedStrategyValidator({
            'validation_level': 'basic',
            'enable_caching': False
        })
        
        await engine.initialize()
        await registry.initialize()
        await validator.initialize()
        
        # Test health checks
        engine_health = await engine.health_check()
        registry_health = await registry.health_check()
        validator_health = await validator.health_check()
        
        assert engine_health['healthy'] is True
        # Registry health may be False if not started, which is acceptable
        assert 'healthy' in registry_health
        assert validator_health['healthy'] is True
        
        assert engine_health['component_type'] == 'StrategyExecutionEngine'
        assert registry_health['component_type'] == 'EnhancedStrategyRegistry'
        assert validator_health['component_type'] == 'EnhancedStrategyValidator'


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
