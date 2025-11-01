"""
Unit Tests for PositionReconciliation
Tests position reconciliation, discrepancy detection, and auto-correction

Test Coverage:
1. Broker position fetching
2. Position comparison
3. Discrepancy classification
4. Auto-correction logic
5. Alert generation
6. Reconciliation loop
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from core_engine.system.position_reconciliation import (
    PositionReconciliation,
    DiscrepancySeverity,
    ReconciliationAction
)


class TestPositionReconciliation:
    """Test suite for PositionReconciliation"""
    
    @pytest.fixture
    def mock_risk_manager(self):
        """Create mock risk manager"""
        risk_manager = Mock()
        risk_manager.current_positions = {
            'AAPL': 100.0,
            'TSLA': 50.0,
            'MSFT': 200.0
        }
        return risk_manager
    
    @pytest.fixture
    def mock_broker_api(self):
        """Create mock broker API"""
        broker_api = Mock()
        
        async def get_positions():
            return [
                {'symbol': 'AAPL', 'quantity': 100.0},
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        broker_api.get_positions = AsyncMock(side_effect=get_positions)
        return broker_api
    
    @pytest.fixture
    def reconciliation(self, mock_risk_manager, mock_broker_api):
        """Create reconciliation instance"""
        config = {
            'normal_interval_seconds': 300,
            'fast_interval_seconds': 60,
            'minor_threshold': 1000,
            'moderate_threshold': 10000,
            'auto_correct_enabled': True,
            'auto_correct_threshold': 10000
        }
        return PositionReconciliation(mock_risk_manager, mock_broker_api, config)
    
    @pytest.mark.asyncio
    async def test_no_discrepancies(self, reconciliation):
        """Test reconciliation when positions match"""
        # Positions already match in fixtures
        report = await reconciliation.reconcile_positions()
        
        assert report.discrepancies_found == 0
        assert len(report.discrepancies) == 0
        assert report.reconciliation_status == "success"
    
    @pytest.mark.asyncio
    async def test_minor_discrepancy_detected(self, reconciliation, mock_broker_api):
        """Test minor discrepancy detection"""
        # Modify broker to return slightly different position
        async def get_positions_with_discrepancy():
            return [
                {'symbol': 'AAPL', 'quantity': 105.0},  # +5 shares difference
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_with_discrepancy)
        
        report = await reconciliation.reconcile_positions()
        
        assert report.discrepancies_found == 1
        assert report.discrepancies[0].symbol == 'AAPL'
        assert report.discrepancies[0].quantity_diff == 5.0
        assert report.discrepancies[0].severity == DiscrepancySeverity.MINOR
        assert report.discrepancies[0].action_taken == ReconciliationAction.LOG_ONLY
    
    @pytest.mark.asyncio
    async def test_moderate_discrepancy_alerts(self, reconciliation, mock_broker_api):
        """Test moderate discrepancy triggers alert"""
        # Create moderate discrepancy (~$5K at $100/share)
        async def get_positions_with_moderate_discrepancy():
            return [
                {'symbol': 'AAPL', 'quantity': 150.0},  # +50 shares = $5K
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_with_moderate_discrepancy)
        
        report = await reconciliation.reconcile_positions()
        
        assert report.discrepancies_found == 1
        discrepancy = report.discrepancies[0]
        assert discrepancy.severity == DiscrepancySeverity.MODERATE
        assert discrepancy.action_taken == ReconciliationAction.ALERT_TEAM
    
    @pytest.mark.asyncio
    async def test_severe_discrepancy_auto_corrects(self, reconciliation, mock_broker_api, mock_risk_manager):
        """Test severe discrepancy triggers auto-correction"""
        # Create severe discrepancy (~$15K at $100/share)
        async def get_positions_with_severe_discrepancy():
            return [
                {'symbol': 'AAPL', 'quantity': 250.0},  # +150 shares = $15K
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_with_severe_discrepancy)
        
        mock_risk_manager.current_positions['AAPL']
        
        report = await reconciliation.reconcile_positions()
        
        assert report.discrepancies_found == 1
        discrepancy = report.discrepancies[0]
        assert discrepancy.severity == DiscrepancySeverity.SEVERE
        assert discrepancy.action_taken == ReconciliationAction.AUTO_CORRECT
        
        # Verify position was auto-corrected
        assert mock_risk_manager.current_positions['AAPL'] == 250.0
        assert reconciliation.total_auto_corrections == 1
    
    @pytest.mark.asyncio
    async def test_missing_broker_position(self, reconciliation, mock_broker_api):
        """Test when position exists internally but not at broker"""
        async def get_positions_missing_symbol():
            return [
                {'symbol': 'AAPL', 'quantity': 100.0},
                {'symbol': 'TSLA', 'quantity': 50.0}
                # MSFT missing from broker
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_missing_symbol)
        
        report = await reconciliation.reconcile_positions()
        
        # Should detect MSFT discrepancy (200 internal, 0 broker)
        assert report.discrepancies_found == 1
        discrepancy = report.discrepancies[0]
        assert discrepancy.symbol == 'MSFT'
        assert discrepancy.internal_position == 200.0
        assert discrepancy.broker_position == 0.0
    
    @pytest.mark.asyncio
    async def test_extra_broker_position(self, reconciliation, mock_broker_api, mock_risk_manager):
        """Test when position exists at broker but not internally"""
        async def get_positions_with_extra():
            return [
                {'symbol': 'AAPL', 'quantity': 100.0},
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0},
                {'symbol': 'NVDA', 'quantity': 75.0}  # Not in internal
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_with_extra)
        
        report = await reconciliation.reconcile_positions()
        
        # Should detect NVDA discrepancy (0 internal, 75 broker)
        assert report.discrepancies_found == 1
        discrepancy = report.discrepancies[0]
        assert discrepancy.symbol == 'NVDA'
        assert discrepancy.internal_position == 0.0
        assert discrepancy.broker_position == 75.0
    
    def test_severity_classification(self, reconciliation):
        """Test discrepancy severity classification"""
        assert reconciliation._classify_severity(500) == DiscrepancySeverity.MINOR
        assert reconciliation._classify_severity(5000) == DiscrepancySeverity.MODERATE
        assert reconciliation._classify_severity(50000) == DiscrepancySeverity.SEVERE
        assert reconciliation._classify_severity(150000) == DiscrepancySeverity.CRITICAL
    
    def test_action_determination(self, reconciliation):
        """Test action determination based on severity"""
        assert reconciliation._determine_action(
            DiscrepancySeverity.MINOR, 500
        ) == ReconciliationAction.LOG_ONLY
        
        assert reconciliation._determine_action(
            DiscrepancySeverity.MODERATE, 5000
        ) == ReconciliationAction.ALERT_TEAM
        
        assert reconciliation._determine_action(
            DiscrepancySeverity.SEVERE, 50000
        ) == ReconciliationAction.AUTO_CORRECT
    
    @pytest.mark.asyncio
    async def test_reconciliation_interval_adjustment(self, reconciliation, mock_broker_api):
        """Test that interval adjusts based on discrepancies"""
        # Initial interval should be normal
        assert reconciliation.current_interval == 300
        
        # Create discrepancy
        async def get_positions_with_discrepancy():
            return [
                {'symbol': 'AAPL', 'quantity': 105.0},
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_with_discrepancy)
        
        await reconciliation.reconcile_positions()
        
        # Interval should switch to fast after discrepancy
        assert reconciliation.current_interval == 60
        assert reconciliation.consecutive_discrepancies == 1
    
    @pytest.mark.asyncio
    async def test_reconciliation_statistics(self, reconciliation):
        """Test statistics tracking"""
        await reconciliation.reconcile_positions()
        await reconciliation.reconcile_positions()
        
        stats = reconciliation.get_reconciliation_statistics()
        
        assert stats['total_reconciliations'] == 2
        assert stats['last_reconciliation'] is not None
        assert 'discrepancies_by_severity' in stats
        assert stats['is_running'] is False  # Loop not started
    
    def test_report_generation(self, reconciliation):
        """Test reconciliation report generation"""
        report_text = reconciliation.generate_reconciliation_report()
        
        assert 'POSITION RECONCILIATION REPORT' in report_text
        assert 'Total Reconciliations' in report_text
        assert 'Discrepancies Found' in report_text
    
    @pytest.mark.asyncio
    async def test_negligible_difference_ignored(self, reconciliation, mock_broker_api):
        """Test that very small differences are ignored"""
        # Difference < 0.01 shares
        async def get_positions_negligible_diff():
            return [
                {'symbol': 'AAPL', 'quantity': 100.005},  # Tiny difference
                {'symbol': 'TSLA', 'quantity': 50.0},
                {'symbol': 'MSFT', 'quantity': 200.0}
            ]
        
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions_negligible_diff)
        
        report = await reconciliation.reconcile_positions()
        
        # Should ignore negligible difference
        assert report.discrepancies_found == 0
    
    @pytest.mark.asyncio
    async def test_broker_api_failure_handling(self, reconciliation, mock_broker_api):
        """Test graceful handling of broker API failure"""
        # Simulate broker API failure
        mock_broker_api.get_positions = AsyncMock(side_effect=Exception("API Error"))
        
        report = await reconciliation.reconcile_positions()
        
        # Should return error status
        assert report.reconciliation_status == "error"
        assert report.total_symbols_checked == 0


# Integration Test
class TestReconciliationIntegration:
    """Integration tests for position reconciliation"""
    
    @pytest.mark.asyncio
    async def test_full_reconciliation_workflow(self):
        """Test complete reconciliation workflow"""
        # Setup
        mock_risk_manager = Mock()
        mock_risk_manager.current_positions = {
            'AAPL': 100.0,
            'TSLA': 50.0,
            'MSFT': 200.0
        }
        
        async def get_positions():
            return [
                {'symbol': 'AAPL', 'quantity': 150.0},  # Severe discrepancy
                {'symbol': 'TSLA', 'quantity': 55.0},   # Minor discrepancy
                {'symbol': 'MSFT', 'quantity': 200.0},  # No discrepancy
                {'symbol': 'NVDA', 'quantity': 100.0}   # New position
            ]
        
        mock_broker_api = Mock()
        mock_broker_api.get_positions = AsyncMock(side_effect=get_positions)
        
        reconciliation = PositionReconciliation(mock_risk_manager, mock_broker_api, {
            'auto_correct_enabled': True,
            'auto_correct_threshold': 1000
        })
        
        # Execute
        report = await reconciliation.reconcile_positions()
        
        # Verify
        assert report.total_symbols_checked == 4
        assert report.discrepancies_found == 3  # AAPL, TSLA, NVDA
        
        # Check AAPL was auto-corrected (severe)
        assert mock_risk_manager.current_positions['AAPL'] == 150.0
        
        # Check TSLA discrepancy logged (minor)
        tsla_disc = next(d for d in report.discrepancies if d.symbol == 'TSLA')
        assert tsla_disc.action_taken == ReconciliationAction.LOG_ONLY
        
        # Check NVDA discrepancy detected (new position)
        nvda_disc = next(d for d in report.discrepancies if d.symbol == 'NVDA')
        assert nvda_disc.internal_position == 0.0
        assert nvda_disc.broker_position == 100.0
    
    @pytest.mark.asyncio
    async def test_reconciliation_loop_startup_shutdown(self):
        """Test reconciliation loop can start and stop"""
        mock_risk_manager = Mock()
        mock_risk_manager.current_positions = {}
        
        mock_broker_api = Mock()
        mock_broker_api.get_positions = AsyncMock(return_value=[])
        
        reconciliation = PositionReconciliation(
            mock_risk_manager, 
            mock_broker_api,
            {'normal_interval_seconds': 1}  # Fast for testing
        )
        
        # Start loop
        asyncio.create_task(reconciliation.start_reconciliation_loop())
        
        # Let it run for a bit
        await asyncio.sleep(0.5)
        
        # Stop loop
        reconciliation.stop_reconciliation_loop()
        
        # Wait for task to complete
        await asyncio.sleep(0.5)
        
        assert reconciliation.total_reconciliations >= 1


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])

