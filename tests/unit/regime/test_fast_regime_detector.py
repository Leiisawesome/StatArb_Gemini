"""
Unit tests for FastRegimeDetector

Tests fast regime detection using leading indicators:
VIX spikes, market breadth, order book imbalance, volatility spikes.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.regime.fast_regime_detector import (
    FastRegimeDetector,
    RegimeType,
    FastSignalType,
    FastRegimeSignal
)


@pytest.fixture
def mock_market_data_manager():
    """Mock market data manager"""
    return Mock()


@pytest.fixture
def fast_detector(mock_market_data_manager):
    """Create FastRegimeDetector instance"""
    config = {
        'vix_spike_pct': 0.20,  # 20%
        'breadth_collapse_pct': 0.70,  # 70%
        'order_imbalance_pct': 0.80,  # 80%
        'volatility_spike_multiplier': 3.0,  # 3x
        'correlation_window_days': 30
    }
    return FastRegimeDetector(mock_market_data_manager, config)


class TestFastRegimeDetector:
    """Test suite for FastRegimeDetector"""
    
    def test_initialization(self, fast_detector):
        """Test detector initializes correctly"""
        assert fast_detector is not None
        assert fast_detector.vix_spike_threshold == 0.20
        assert fast_detector.breadth_collapse_threshold == 0.70
        assert fast_detector.order_imbalance_threshold == 0.80
        assert fast_detector.volatility_spike_multiplier == 3.0
        assert fast_detector.total_checks == 0
        assert fast_detector.total_signals == 0
    
    @pytest.mark.asyncio
    async def test_vix_spike_detection(self, fast_detector):
        """Test VIX spike detection"""
        # Mock VIX data
        with patch.object(fast_detector, '_get_current_vix', new_callable=AsyncMock) as mock_vix:
            # First reading
            mock_vix.return_value = 15.0
            await fast_detector._check_vix_spike()
            
            # Add to history manually for test
            fast_detector.vix_history.append({
                'timestamp': datetime.now() - timedelta(minutes=5),
                'vix': 15.0
            })
            
            # Second reading - spike
            mock_vix.return_value = 19.0  # +26.7% spike
            signal = await fast_detector._check_vix_spike()
            
            assert signal is not None
            assert signal.signal_type == FastSignalType.VIX_SPIKE
            assert signal.new_regime in [RegimeType.EXTREME_VOLATILITY, RegimeType.CRISIS]
            assert signal.severity >= 8
            assert signal.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_vix_no_spike(self, fast_detector):
        """Test VIX with no significant spike"""
        with patch.object(fast_detector, '_get_current_vix', new_callable=AsyncMock) as mock_vix:
            # First reading
            mock_vix.return_value = 15.0
            await fast_detector._check_vix_spike()
            
            fast_detector.vix_history.append({
                'timestamp': datetime.now() - timedelta(minutes=5),
                'vix': 15.0
            })
            
            # Second reading - minor change
            mock_vix.return_value = 15.5  # +3.3% (below 20% threshold)
            signal = await fast_detector._check_vix_spike()
            
            assert signal is None  # No spike
    
    @pytest.mark.asyncio
    async def test_market_breadth_collapse(self, fast_detector):
        """Test market breadth collapse detection"""
        with patch.object(fast_detector, '_calculate_market_breadth', new_callable=AsyncMock) as mock_breadth:
            # Simulate 75% stocks declining
            mock_breadth.return_value = {
                'declining_pct': 0.75,
                'advancing': 250,
                'declining': 750,
                'unchanged': 0
            }
            
            signal = await fast_detector._check_market_breadth()
            
            assert signal is not None
            assert signal.signal_type == FastSignalType.BREADTH_COLLAPSE
            assert signal.new_regime == RegimeType.HIGH_VOLATILITY
            assert signal.severity >= 8
            assert signal.confidence == 0.85
    
    @pytest.mark.asyncio
    async def test_market_breadth_normal(self, fast_detector):
        """Test market breadth in normal conditions"""
        with patch.object(fast_detector, '_calculate_market_breadth', new_callable=AsyncMock) as mock_breadth:
            # Simulate 45% stocks declining (normal)
            mock_breadth.return_value = {
                'declining_pct': 0.45,
                'advancing': 550,
                'declining': 450,
                'unchanged': 0
            }
            
            signal = await fast_detector._check_market_breadth()
            
            assert signal is None  # No collapse
    
    @pytest.mark.asyncio
    async def test_order_book_imbalance(self, fast_detector):
        """Test order book imbalance detection"""
        with patch.object(fast_detector, '_analyze_order_book_imbalance', new_callable=AsyncMock) as mock_order:
            # Simulate 85% sell pressure
            mock_order.return_value = {
                'sell_pressure_pct': 0.85,
                'sell_volume': 850000,
                'buy_volume': 150000,
                'total_volume': 1000000
            }
            
            signal = await fast_detector._check_order_book_imbalance()
            
            assert signal is not None
            assert signal.signal_type == FastSignalType.ORDER_BOOK_IMBALANCE
            assert signal.new_regime == RegimeType.EXTREME_VOLATILITY
            assert signal.severity >= 7
            assert signal.confidence == 0.80
    
    @pytest.mark.asyncio
    async def test_order_book_balanced(self, fast_detector):
        """Test order book in balanced conditions"""
        with patch.object(fast_detector, '_analyze_order_book_imbalance', new_callable=AsyncMock) as mock_order:
            # Simulate 55% sell pressure (balanced)
            mock_order.return_value = {
                'sell_pressure_pct': 0.55,
                'sell_volume': 550000,
                'buy_volume': 450000,
                'total_volume': 1000000
            }
            
            signal = await fast_detector._check_order_book_imbalance()
            
            assert signal is None  # No imbalance
    
    @pytest.mark.asyncio
    async def test_volatility_spike(self, fast_detector):
        """Test volatility spike detection"""
        with patch.object(fast_detector, '_calculate_intraday_volatility', new_callable=AsyncMock) as mock_vol:
            # Add historical volatility
            for i in range(20):
                fast_detector.volatility_history.append({
                    'timestamp': datetime.now() - timedelta(minutes=15-i),
                    'volatility': 0.15  # Normal volatility
                })
            
            # Current volatility is 4x normal (0.6 vs 0.15)
            mock_vol.return_value = 0.60
            
            signal = await fast_detector._check_volatility_spike()
            
            assert signal is not None
            assert signal.signal_type == FastSignalType.VOLATILITY_SPIKE
            assert signal.new_regime == RegimeType.HIGH_VOLATILITY
            assert signal.severity >= 6
            assert signal.confidence == 0.75
    
    @pytest.mark.asyncio
    async def test_volatility_normal(self, fast_detector):
        """Test volatility in normal conditions"""
        with patch.object(fast_detector, '_calculate_intraday_volatility', new_callable=AsyncMock) as mock_vol:
            # Add historical volatility
            for i in range(20):
                fast_detector.volatility_history.append({
                    'timestamp': datetime.now() - timedelta(minutes=15-i),
                    'volatility': 0.15
                })
            
            # Current volatility is 1.5x normal (below 3x threshold)
            mock_vol.return_value = 0.225
            
            signal = await fast_detector._check_volatility_spike()
            
            assert signal is None  # No spike
    
    @pytest.mark.asyncio
    async def test_check_fast_regime_change_vix_priority(self, fast_detector):
        """Test VIX spike has highest priority"""
        # Mock all indicators
        with patch.object(fast_detector, '_check_vix_spike', new_callable=AsyncMock) as mock_vix, \
             patch.object(fast_detector, '_check_market_breadth', new_callable=AsyncMock) as mock_breadth, \
             patch.object(fast_detector, '_check_order_book_imbalance', new_callable=AsyncMock) as mock_order, \
             patch.object(fast_detector, '_check_volatility_spike', new_callable=AsyncMock) as mock_vol:
            
            # VIX critical signal
            mock_vix.return_value = FastRegimeSignal(
                signal_type=FastSignalType.VIX_SPIKE,
                new_regime=RegimeType.CRISIS,
                severity=10,
                confidence=0.9,
                timestamp=datetime.now(),
                details={}
            )
            
            # Other signals shouldn't matter
            mock_breadth.return_value = None
            mock_order.return_value = None
            mock_vol.return_value = None
            
            signal = await fast_detector.check_fast_regime_change()
            
            assert signal is not None
            assert signal.signal_type == FastSignalType.VIX_SPIKE
            assert signal.severity == 10
    
    @pytest.mark.asyncio
    async def test_check_fast_regime_change_no_signals(self, fast_detector):
        """Test when no fast signals detected"""
        with patch.object(fast_detector, '_check_vix_spike', new_callable=AsyncMock) as mock_vix, \
             patch.object(fast_detector, '_check_market_breadth', new_callable=AsyncMock) as mock_breadth, \
             patch.object(fast_detector, '_check_order_book_imbalance', new_callable=AsyncMock) as mock_order, \
             patch.object(fast_detector, '_check_volatility_spike', new_callable=AsyncMock) as mock_vol:
            
            # All return None
            mock_vix.return_value = None
            mock_breadth.return_value = None
            mock_order.return_value = None
            mock_vol.return_value = None
            
            signal = await fast_detector.check_fast_regime_change()
            
            assert signal is None
    
    def test_record_signal(self, fast_detector):
        """Test signal recording"""
        signal = FastRegimeSignal(
            signal_type=FastSignalType.VIX_SPIKE,
            new_regime=RegimeType.CRISIS,
            severity=10,
            confidence=0.9,
            timestamp=datetime.now(),
            details={}
        )
        
        initial_count = fast_detector.total_signals
        fast_detector._record_signal(signal)
        
        assert fast_detector.total_signals == initial_count + 1
        assert fast_detector.signals_by_type[FastSignalType.VIX_SPIKE] == 1
        assert len(fast_detector.recent_signals) == 1
    
    def test_get_statistics(self, fast_detector):
        """Test getting detection statistics"""
        stats = fast_detector.get_fast_detection_statistics()
        
        assert 'total_checks' in stats
        assert 'total_signals' in stats
        assert 'signals_by_type' in stats
        assert 'recent_signals_count' in stats
        assert stats['total_checks'] == 0
        assert stats['total_signals'] == 0
    
    def test_generate_report(self, fast_detector):
        """Test generating detection report"""
        # Add a signal
        signal = FastRegimeSignal(
            signal_type=FastSignalType.VIX_SPIKE,
            new_regime=RegimeType.CRISIS,
            severity=10,
            confidence=0.9,
            timestamp=datetime.now(),
            details={}
        )
        fast_detector._record_signal(signal)
        
        report = fast_detector.generate_fast_detection_report()
        
        assert 'FAST REGIME DETECTION REPORT' in report
        assert 'Total Checks:' in report
        assert 'Total Signals:' in report
        assert 'DETECTION THRESHOLDS:' in report


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

