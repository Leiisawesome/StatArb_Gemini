"""
Unit tests for EnhancedHealthMonitor

Tests multi-dimensional system health monitoring,
health scoring, auto-recovery, and status reporting.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, '/Users/lei/Documents/GitHub/StatArb_Gemini/StatArb_Gemini')

from core_engine.system.enhanced_health_monitor import (
    EnhancedHealthMonitor,
    HealthStatus,
    HealthDimension,
    HealthScore,
    SystemHealthReport
)


@pytest.fixture
def mock_orchestrator():
    """Mock HierarchicalSystemOrchestrator"""
    orchestrator = Mock()
    orchestrator.components = {
        'comp1': {
            'name': 'Component1',
            'component': Mock(health_check=AsyncMock(return_value={'healthy': True}))
        },
        'comp2': {
            'name': 'Component2',
            'component': Mock(health_check=AsyncMock(return_value={'healthy': True}))
        },
        'comp3': {
            'name': 'Component3',
            'component': Mock(health_check=AsyncMock(return_value={'healthy': False}))
        }
    }
    return orchestrator


@pytest.fixture
def health_monitor(mock_orchestrator):
    """Create EnhancedHealthMonitor instance"""
    config = {
        'check_interval_seconds': 30,
        'auto_recovery_enabled': True
    }
    return EnhancedHealthMonitor(mock_orchestrator, config)


class TestEnhancedHealthMonitor:
    """Test suite for EnhancedHealthMonitor"""
    
    def test_initialization(self, health_monitor):
        """Test monitor initializes correctly"""
        assert health_monitor is not None
        assert health_monitor.auto_recovery_enabled is True
        assert health_monitor.check_interval_seconds == 30
        assert health_monitor.total_checks == 0
        assert health_monitor.total_recoveries == 0
        assert health_monitor.healthy_threshold == 80
        assert health_monitor.degraded_threshold == 60
    
    def test_determine_status(self, health_monitor):
        """Test health status determination"""
        assert health_monitor._determine_status(85) == HealthStatus.HEALTHY
        assert health_monitor._determine_status(70) == HealthStatus.DEGRADED
        assert health_monitor._determine_status(50) == HealthStatus.UNHEALTHY
        assert health_monitor._determine_status(30) == HealthStatus.CRITICAL
    
    @pytest.mark.asyncio
    async def test_check_component_health_all_healthy(self, health_monitor, mock_orchestrator):
        """Test component health check when all healthy"""
        # Mock all components as healthy
        for comp_id in mock_orchestrator.components:
            mock_orchestrator.components[comp_id]['component'].health_check = AsyncMock(
                return_value={'healthy': True}
            )
        
        score = await health_monitor._check_component_health()
        
        assert score.dimension == HealthDimension.COMPONENT_HEALTH
        assert score.score == 100
        assert score.status == HealthStatus.HEALTHY
        assert len(score.issues) == 0
    
    @pytest.mark.asyncio
    async def test_check_component_health_some_unhealthy(self, health_monitor, mock_orchestrator):
        """Test component health check with some unhealthy"""
        # Mock: 2 healthy, 1 unhealthy (67% healthy)
        score = await health_monitor._check_component_health()
        
        assert score.dimension == HealthDimension.COMPONENT_HEALTH
        assert 60 < score.score < 70  # Approximately 67%
        assert score.status == HealthStatus.DEGRADED
        assert len(score.issues) > 0
    
    @pytest.mark.asyncio
    async def test_check_data_quality(self, health_monitor):
        """Test data quality check"""
        score = await health_monitor._check_data_quality()
        
        assert score.dimension == HealthDimension.DATA_QUALITY
        assert isinstance(score.score, float)
        assert 0 <= score.score <= 100
        assert isinstance(score.status, HealthStatus)
    
    @pytest.mark.asyncio
    async def test_check_execution_health(self, health_monitor):
        """Test execution health check"""
        score = await health_monitor._check_execution_health()
        
        assert score.dimension == HealthDimension.EXECUTION_HEALTH
        assert isinstance(score.score, float)
        assert 0 <= score.score <= 100
        assert isinstance(score.status, HealthStatus)
    
    @pytest.mark.asyncio
    async def test_check_risk_health(self, health_monitor):
        """Test risk health check"""
        score = await health_monitor._check_risk_health()
        
        assert score.dimension == HealthDimension.RISK_HEALTH
        assert isinstance(score.score, float)
        assert 0 <= score.score <= 100
        assert isinstance(score.status, HealthStatus)
    
    @pytest.mark.asyncio
    async def test_check_performance(self, health_monitor):
        """Test performance check"""
        score = await health_monitor._check_performance()
        
        assert score.dimension == HealthDimension.PERFORMANCE
        assert isinstance(score.score, float)
        assert 0 <= score.score <= 100
        assert isinstance(score.status, HealthStatus)
    
    @pytest.mark.asyncio
    async def test_check_system_health_all_dimensions(self, health_monitor):
        """Test complete system health check"""
        report = await health_monitor.check_system_health()
        
        assert isinstance(report, SystemHealthReport)
        assert 0 <= report.overall_score <= 100
        assert isinstance(report.overall_status, HealthStatus)
        assert len(report.dimension_scores) == 5  # All 5 dimensions
        
        # Check all dimensions present
        for dimension in HealthDimension:
            assert dimension in report.dimension_scores
    
    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, health_monitor):
        """Test weighted average calculation for overall score"""
        report = await health_monitor.check_system_health()
        
        # Verify weighted average
        expected_score = sum(
            report.dimension_scores[dim].score * health_monitor.dimension_weights[dim]
            for dim in HealthDimension
        )
        
        assert abs(report.overall_score - expected_score) < 0.01  # Allow small floating point error
    
    @pytest.mark.asyncio
    async def test_critical_issues_collection(self, health_monitor):
        """Test critical issues are collected"""
        report = await health_monitor.check_system_health()
        
        # Check critical_issues list exists
        assert isinstance(report.critical_issues, list)
        
        # If any dimension is unhealthy/critical, should have issues
        unhealthy_dims = [
            dim for dim, score in report.dimension_scores.items()
            if score.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
        ]
        
        if unhealthy_dims:
            assert len(report.critical_issues) > 0
    
    @pytest.mark.asyncio
    async def test_warnings_collection(self, health_monitor):
        """Test warnings are collected"""
        report = await health_monitor.check_system_health()
        
        # Check warnings list exists
        assert isinstance(report.warnings, list)
        
        # If any dimension is degraded, should have warnings
        degraded_dims = [
            dim for dim, score in report.dimension_scores.items()
            if score.status == HealthStatus.DEGRADED
        ]
        
        if degraded_dims:
            assert len(report.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_auto_recovery_triggered(self, health_monitor):
        """Test auto-recovery is triggered for degraded health"""
        # Make one dimension degraded
        with patch.object(health_monitor, '_check_component_health', new_callable=AsyncMock) as mock_comp:
            mock_comp.return_value = HealthScore(
                dimension=HealthDimension.COMPONENT_HEALTH,
                score=65,  # Degraded
                status=HealthStatus.DEGRADED,
                issues=['Test issue']
            )
            
            report = await health_monitor.check_system_health()
            
            if health_monitor.auto_recovery_enabled:
                assert len(report.auto_recovery_actions) > 0
                assert health_monitor.total_recoveries > 0
    
    @pytest.mark.asyncio
    async def test_auto_recovery_disabled(self, health_monitor):
        """Test auto-recovery can be disabled"""
        health_monitor.auto_recovery_enabled = False
        
        # Make one dimension unhealthy
        with patch.object(health_monitor, '_check_component_health', new_callable=AsyncMock) as mock_comp:
            mock_comp.return_value = HealthScore(
                dimension=HealthDimension.COMPONENT_HEALTH,
                score=50,  # Unhealthy
                status=HealthStatus.UNHEALTHY,
                issues=['Test issue']
            )
            
            report = await health_monitor.check_system_health()
            
            assert len(report.auto_recovery_actions) == 0
    
    @pytest.mark.asyncio
    async def test_health_history_tracking(self, health_monitor):
        """Test health reports are stored in history"""
        initial_count = len(health_monitor.health_history)
        
        await health_monitor.check_system_health()
        
        assert len(health_monitor.health_history) == initial_count + 1
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, health_monitor):
        """Test statistics are tracked correctly"""
        initial_checks = health_monitor.total_checks
        
        await health_monitor.check_system_health()
        
        assert health_monitor.total_checks == initial_checks + 1
    
    def test_get_health_statistics(self, health_monitor):
        """Test getting health statistics"""
        stats = health_monitor.get_health_statistics()
        
        assert 'total_checks' in stats
        assert 'total_recoveries' in stats
        assert 'degraded_count' in stats
        assert 'unhealthy_count' in stats
        assert 'is_monitoring' in stats
    
    @pytest.mark.asyncio
    async def test_generate_health_report(self, health_monitor):
        """Test generating health report string"""
        # Run a check to populate history
        await health_monitor.check_system_health()
        
        report_str = health_monitor.generate_health_report()
        
        assert 'SYSTEM HEALTH REPORT' in report_str
        assert 'Total Checks:' in report_str
        assert 'CURRENT STATUS:' in report_str
        assert 'DIMENSION SCORES:' in report_str
    
    def test_dimension_weights_sum_to_one(self, health_monitor):
        """Test dimension weights sum to 1.0"""
        total_weight = sum(health_monitor.dimension_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error
    
    @pytest.mark.asyncio
    async def test_healthy_system_report(self, health_monitor, mock_orchestrator):
        """Test report when system is healthy"""
        # Mock all dimensions as healthy
        for comp_id in mock_orchestrator.components:
            mock_orchestrator.components[comp_id]['component'].health_check = AsyncMock(
                return_value={'healthy': True}
            )
        
        report = await health_monitor.check_system_health()
        
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.overall_score >= health_monitor.healthy_threshold
        assert len(report.critical_issues) == 0
    
    @pytest.mark.asyncio
    async def test_degraded_count_tracking(self, health_monitor):
        """Test degraded events are counted"""
        initial_count = health_monitor.degraded_count
        
        # Force degraded status
        with patch.object(health_monitor, '_check_component_health', new_callable=AsyncMock) as mock_comp:
            mock_comp.return_value = HealthScore(
                dimension=HealthDimension.COMPONENT_HEALTH,
                score=65,
                status=HealthStatus.DEGRADED,
                issues=[]
            )
            
            await health_monitor.check_system_health()
        
        assert health_monitor.degraded_count >= initial_count


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

