#!/usr/bin/env python3
"""
Supplemental Validators Test Coverage
=====================================

Addresses missing coverage in signals/validators.py (32% → target 50%+)

Focuses on:
- Async validate_portfolio method
- Portfolio-level validation scenarios
- Advanced validation paths
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import asyncio

from core_engine.processing.signals.validators import (
    SignalValidator,
    PortfolioValidationReport,
    ValidationStatus
)


class TestPortfolioValidation:
    """Test portfolio-level validation"""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return SignalValidator()
    
    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for portfolio validation"""
        signals = []
        base_time = datetime(2024, 1, 1)
        
        for i in range(10):
            signal = Mock()
            signal.symbol = f"AAPL_{i}"
            signal.timestamp = base_time + timedelta(minutes=i)
            signal.confidence = 0.5 + (i * 0.05)
            signal.suggested_position_size = 0.01 * (i + 1)
            signal.signal_type = "BUY" if i % 2 == 0 else "SELL"
            signals.append(signal)
        
        return signals
    
    @pytest.mark.asyncio
    async def test_validate_portfolio_basic(self, validator, mock_signals):
        """Test basic portfolio validation"""
        context = {
            'sectors': {f"AAPL_{i}": "Technology" for i in range(10)},
            'market_data': {}
        }
        
        report = await validator.validate_portfolio(mock_signals, context)
        
        assert isinstance(report, PortfolioValidationReport)
        assert report.total_signals == len(mock_signals)
        assert report.valid_signals >= 0
        assert report.invalid_signals >= 0
    
    @pytest.mark.asyncio
    async def test_validate_portfolio_empty(self, validator):
        """Test portfolio validation with empty signal list"""
        context = {}
        
        report = await validator.validate_portfolio([], context)
        
        assert isinstance(report, PortfolioValidationReport)
        assert report.total_signals == 0
        assert report.valid_signals == 0
        assert report.invalid_signals == 0
    
    @pytest.mark.asyncio
    async def test_validate_portfolio_with_concentration(self, validator, mock_signals):
        """Test portfolio validation with concentration analysis"""
        context = {
            'sectors': {f"AAPL_{i}": "Technology" for i in range(10)},
            'market_data': {}
        }
        
        report = await validator.validate_portfolio(mock_signals, context)
        
        assert isinstance(report, PortfolioValidationReport)
        # Portfolio concentration should be calculated
        assert hasattr(report, 'portfolio_concentration') or hasattr(report, 'symbol_exposures')
    
    @pytest.mark.asyncio
    async def test_validate_portfolio_error_handling(self, validator):
        """Test portfolio validation error handling"""
        # Create signals that will cause validation errors
        bad_signals = [None, Mock(symbol=None), Mock()]
        
        context = {}
        
        # Should handle gracefully
        report = await validator.validate_portfolio(bad_signals, context)
        
        assert isinstance(report, PortfolioValidationReport)


class TestAdvancedValidationPaths:
    """Test advanced validation code paths"""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return SignalValidator()
    
    def test_generate_recommendations_low_score(self, validator):
        """Test recommendation generation for low score"""
        from core_engine.processing.signals.validators import SignalValidationReport, ValidationStatus
        
        report = SignalValidationReport(
            signal_id="test_signal",
            symbol="AAPL",
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.FAILED,
            overall_score=0.2,  # Very low score
            confidence_level=0.3,
            data_quality_score=0.3,
            signal_quality_score=0.4,
            risk_score=0.5,
            consistency_score=0.6,
            validation_results=[]
        )
        
        recommendations = validator._generate_recommendations(report)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should have recommendation for very low score
        assert any("very low" in rec.lower() for rec in recommendations)
    
    def test_generate_recommendations_moderate_score(self, validator):
        """Test recommendation generation for moderate score"""
        from core_engine.processing.signals.validators import SignalValidationReport, ValidationStatus
        
        report = SignalValidationReport(
            signal_id="test_signal",
            symbol="AAPL",
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.WARNING,
            overall_score=0.6,  # Moderate score
            confidence_level=0.6,
            data_quality_score=0.7,
            signal_quality_score=0.6,
            risk_score=0.5,
            consistency_score=0.5,
            validation_results=[]
        )
        
        recommendations = validator._generate_recommendations(report)
        
        assert isinstance(recommendations, list)
        # Should have recommendations for moderate score and below-average categories
        assert len(recommendations) > 0

