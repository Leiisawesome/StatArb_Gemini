"""
Test Suite for Regime Brick - Phase 3 Validation
================================================

Tests ISystemComponent implementation for 3 key regime classes:
- RegimeManager
- RegimeDetector
- RegimeClassifier

Author: StatArb_Gemini Testing Team
Date: October 21, 2025
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.regime import (
    RegimeManager,
    RegimeDetector,
    RegimeClassifier
)
from core_engine.config.component_config import RegimeConfig


class TestRegimeManagerISystemComponent:
    """Test RegimeManager ISystemComponent implementation"""

    def setup_method(self):
        """Setup for each test"""
        self.config = RegimeConfig()
        self.manager = RegimeManager(self.config)

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method"""
        result = await self.manager.initialize()
        assert result is True
        assert self.manager.is_initialized is True
        assert self.manager.initialization_time is not None

    @pytest.mark.asyncio
    async def test_start(self):
        """Test start method"""
        await self.manager.initialize()
        result = await self.manager.start()
        assert result is True
        assert self.manager.is_operational is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stop method"""
        await self.manager.initialize()
        await self.manager.start()
        result = await self.manager.stop()
        assert result is True
        assert self.manager.is_operational is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method"""
        await self.manager.initialize()
        await self.manager.start()
        health = await self.manager.health_check()
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert 'initialized' in health
        assert 'operational' in health
        assert health['initialized'] is True
        assert health['operational'] is True

    def test_get_status(self):
        """Test get_status method"""
        status = self.manager.get_status()
        assert isinstance(status, dict)
        assert 'component_type' in status
        assert status['component_type'] == 'RegimeManager'
        assert 'initialized' in status
        assert 'operational' in status


class TestRegimeDetectorISystemComponent:
    """Test RegimeDetector ISystemComponent implementation"""

    def setup_method(self):
        """Setup for each test"""
        self.config = RegimeConfig()
        self.detector = RegimeDetector(self.config)

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method"""
        result = await self.detector.initialize()
        assert result is True
        assert self.detector.is_initialized is True

    @pytest.mark.asyncio
    async def test_start(self):
        """Test start method"""
        await self.detector.initialize()
        result = await self.detector.start()
        assert result is True
        assert self.detector.is_operational is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stop method"""
        await self.detector.initialize()
        await self.detector.start()
        result = await self.detector.stop()
        assert result is True
        assert self.detector.is_operational is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method"""
        await self.detector.initialize()
        await self.detector.start()
        health = await self.detector.health_check()
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert health['healthy'] is True

    def test_get_status(self):
        """Test get_status method"""
        status = self.detector.get_status()
        assert isinstance(status, dict)
        assert status['component_type'] == 'RegimeDetector'


class TestRegimeClassifierISystemComponent:
    """Test RegimeClassifier ISystemComponent implementation"""

    def setup_method(self):
        """Setup for each test"""
        self.config = RegimeConfig()
        self.classifier = RegimeClassifier(self.config)

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test initialize method"""
        result = await self.classifier.initialize()
        assert result is True
        assert self.classifier.is_initialized is True

    @pytest.mark.asyncio
    async def test_start(self):
        """Test start method"""
        await self.classifier.initialize()
        result = await self.classifier.start()
        assert result is True
        assert self.classifier.is_operational is True

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stop method"""
        await self.classifier.initialize()
        await self.classifier.start()
        result = await self.classifier.stop()
        assert result is True
        assert self.classifier.is_operational is False

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method"""
        await self.classifier.initialize()
        await self.classifier.start()
        health = await self.classifier.health_check()
        assert isinstance(health, dict)
        assert 'healthy' in health
        assert health['healthy'] is True

    def test_get_status(self):
        """Test get_status method"""
        status = self.classifier.get_status()
        assert isinstance(status, dict)
        assert status['component_type'] == 'RegimeClassifier'


class TestLifecycleSequence:
    """Test full lifecycle sequence for all components"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_regime_manager(self):
        """Test full lifecycle sequence for RegimeManager"""
        config = RegimeConfig()
        manager = RegimeManager(config)

        # Initialize
        assert await manager.initialize() is True
        assert manager.is_initialized is True

        # Start
        assert await manager.start() is True
        assert manager.is_operational is True

        # Health check while running
        health = await manager.health_check()
        assert health['healthy'] is True
        assert health['operational'] is True

        # Stop
        assert await manager.stop() is True
        assert manager.is_operational is False

    @pytest.mark.asyncio
    async def test_full_lifecycle_regime_detector(self):
        """Test full lifecycle sequence for RegimeDetector"""
        config = RegimeConfig()
        detector = RegimeDetector(config)

        # Full sequence
        assert await detector.initialize() is True
        assert await detector.start() is True
        health = await detector.health_check()
        assert health['healthy'] is True
        assert await detector.stop() is True

    @pytest.mark.asyncio
    async def test_full_lifecycle_regime_classifier(self):
        """Test full lifecycle sequence for RegimeClassifier"""
        config = RegimeConfig()
        classifier = RegimeClassifier(config)

        # Full sequence
        assert await classifier.initialize() is True
        assert await classifier.start() is True
        health = await classifier.health_check()
        assert health['healthy'] is True
        assert await classifier.stop() is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])

