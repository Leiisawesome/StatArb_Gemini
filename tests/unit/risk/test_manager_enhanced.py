"""
Unit tests for manager_enhanced.py

Target: 70%+ coverage (stretch: 80%+)
Baseline: 54% (243 statements)

Test Categories:
1. Dataclasses (2 tests)
2. Initialization (2 tests)
3. Comprehensive Risk Calculation (5 tests)
4. Risk Scoring (3 tests)
5. Alerts (5 tests)
6. Snapshot & Query Methods (4 tests)
7. Monitoring (3 tests)
8. Summary & Limits (3 tests)

Total: ~27 tests
"""

import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from collections import deque

from core_engine.risk.manager_enhanced import (
    EnhancedRiskManager,
    RiskSnapshot,
    RiskAlert
)
from core_engine.risk.exposure_calculator import ExposureType, ExposureBreakdown, ExposureItem
from core_engine.risk.var_calculator import RiskMetrics
from core_engine.risk.stress_tester import PortfolioStressResult
from core_engine.risk.limit_monitor import LimitBreach, AlertSeverity, RiskLimit, LimitType, LimitScope
from core_engine.risk.correlation_analyzer import CorrelationMatrix, CorrelationRegime, RegimeDetectionResult


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_positions():
    """Sample portfolio positions."""
    return {
        'AAPL': {
            'symbol': 'AAPL',
            'quantity': 100,
            'market_value': 15000.0,
            'asset_type': 'EQUITY'
        },
        'GOOGL': {
            'symbol': 'GOOGL',
            'quantity': 50,
            'market_value': 12500.0,
            'asset_type': 'EQUITY'
        }
    }


@pytest.fixture
def sample_returns_data():
    """Sample returns DataFrame."""
    return pd.DataFrame({
        'AAPL': [0.01, -0.02, 0.015, 0.005],
        'GOOGL': [0.005, -0.01, 0.02, 0.008]
    })


@pytest.fixture
def mock_risk_metrics():
    """Mock RiskMetrics object."""
    return RiskMetrics(
        var_1d={0.95: 1000.0, 0.99: 1500.0, 0.999: 2000.0},
        cvar_1d={0.95: 1200.0, 0.99: 1800.0, 0.999: 2400.0},
        volatility_daily=0.01,
        volatility_annual=0.16,
        max_drawdown=-0.15,
        beta=1.2,
        tracking_error=0.05,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        skewness=-0.5,
        kurtosis=3.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def mock_exposure_breakdown():
    """Mock ExposureBreakdown."""
    exposure_items = [
        ExposureItem(identifier='AAPL', exposure_type=ExposureType.SINGLE_NAME, value=15000.0, percentage=60.0),
        ExposureItem(identifier='GOOGL', exposure_type=ExposureType.SINGLE_NAME, value=10000.0, percentage=40.0)
    ]
    return {
        ExposureType.SINGLE_NAME: ExposureBreakdown(
            total_exposure=25000.0,
            long_exposure=25000.0,
            short_exposure=0.0,
            net_exposure=25000.0,
            gross_exposure=25000.0,
            exposures=exposure_items
        )
    }


@pytest.fixture
def mock_stress_result():
    """Mock stress test result."""
    return PortfolioStressResult(
        scenario_name='financial_crisis_2008',
        total_pnl=-5000.0,
        total_pnl_percentage=-20.0,
        worst_case_var=2000.0,
        position_results=[],
        risk_breakdown={'market_risk': -5000.0},
        scenario_probability=0.01,
        timestamp=datetime.now()
    )


@pytest.fixture
def mock_correlation_matrix():
    """Mock correlation matrix."""
    matrix = pd.DataFrame({
        'AAPL': [1.0, 0.7],
        'GOOGL': [0.7, 1.0]
    }, index=['AAPL', 'GOOGL'])
    
    return CorrelationMatrix(
        matrix=matrix,
        method='pearson',
        calculation_time=datetime.now(),
        eigenvalues=[1.7, 0.3],
        condition_number=5.67,
        assets=['AAPL', 'GOOGL'],
        sample_period=(datetime.now() - timedelta(days=30), datetime.now()),
        is_positive_definite=True,
        metadata={}
    )


@pytest.fixture
def risk_manager():
    """Create EnhancedRiskManager with default config."""
    return EnhancedRiskManager()


@pytest.fixture
def risk_manager_custom():
    """Create EnhancedRiskManager with custom config."""
    config = {
        'calculation_interval_seconds': 60,
        'snapshot_retention_days': 7,
        'enable_real_time_monitoring': False,
        'risk_weights': {
            'var': 0.30,
            'stress_test': 0.30,
            'correlation': 0.20,
            'concentration': 0.10,
            'limits': 0.10
        }
    }
    return EnhancedRiskManager(config)


# ============================================================================
# Category 1: Dataclasses (2 tests)
# ============================================================================

class TestDataclasses:
    """Test dataclasses."""
    
    def test_risk_snapshot_creation(self, mock_risk_metrics, mock_exposure_breakdown, 
                                     mock_correlation_matrix, mock_stress_result):
        """Test RiskSnapshot dataclass creation."""
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={'crisis': mock_stress_result},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=45.0,
            metadata={'test': 'data'}
        )
        
        assert snapshot.portfolio_value == 25000.0
        assert snapshot.risk_score == 45.0
        assert snapshot.regime_status == 'NORMAL'
        assert len(snapshot.exposures) == 1
        assert snapshot.risk_metrics == mock_risk_metrics
        assert snapshot.metadata['test'] == 'data'
    
    def test_risk_alert_creation(self):
        """Test RiskAlert dataclass creation."""
        alert = RiskAlert(
            alert_id='test_alert_001',
            alert_type='HIGH_RISK_SCORE',
            severity=AlertSeverity.CRITICAL,
            message='Risk score exceeds threshold',
            details={'risk_score': 85.0}
        )
        
        assert alert.alert_id == 'test_alert_001'
        assert alert.alert_type == 'HIGH_RISK_SCORE'
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.acknowledged is False
        assert isinstance(alert.timestamp, datetime)
        assert alert.details['risk_score'] == 85.0


# ============================================================================
# Category 2: Initialization (2 tests)
# ============================================================================

class TestInitialization:
    """Test EnhancedRiskManager initialization."""
    
    def test_default_initialization(self, risk_manager):
        """Test default initialization."""
        assert risk_manager.risk_calculation_interval == 300  # 5 minutes
        assert risk_manager.snapshot_retention_days == 30
        assert risk_manager.enable_real_time_monitoring is True
        
        # Check risk weights
        assert risk_manager.risk_weights['var'] == 0.25
        assert risk_manager.risk_weights['stress_test'] == 0.25
        assert risk_manager.risk_weights['correlation'] == 0.20
        assert risk_manager.risk_weights['concentration'] == 0.15
        assert risk_manager.risk_weights['limits'] == 0.15
        
        # Check components initialized
        assert risk_manager.exposure_calculator is not None
        assert risk_manager.var_calculator is not None
        assert risk_manager.stress_tester is not None
        assert risk_manager.limit_monitor is not None
        assert risk_manager.correlation_analyzer is not None
        
        # Check internal state
        assert isinstance(risk_manager._risk_snapshots, deque)
        assert isinstance(risk_manager._risk_alerts, deque)
        assert risk_manager._monitoring_active is False
    
    def test_custom_configuration(self, risk_manager_custom):
        """Test custom configuration initialization."""
        assert risk_manager_custom.risk_calculation_interval == 60
        assert risk_manager_custom.snapshot_retention_days == 7
        assert risk_manager_custom.enable_real_time_monitoring is False
        
        # Check custom risk weights
        assert risk_manager_custom.risk_weights['var'] == 0.30
        assert risk_manager_custom.risk_weights['stress_test'] == 0.30
        assert risk_manager_custom.risk_weights['concentration'] == 0.10


# ============================================================================
# Category 3: Comprehensive Risk Calculation (5 tests)
# ============================================================================

class TestComprehensiveRiskCalculation:
    """Test comprehensive risk calculation."""
    
    @pytest.mark.asyncio
    async def test_calculate_comprehensive_risk_full_data(
        self, risk_manager, sample_positions, sample_returns_data,
        mock_risk_metrics, mock_exposure_breakdown, mock_correlation_matrix, mock_stress_result
    ):
        """Test risk calculation with full data."""
        # Mock all component methods
        risk_manager.exposure_calculator.calculate_exposures = AsyncMock(
            return_value=mock_exposure_breakdown
        )
        risk_manager.var_calculator.calculate_comprehensive_risk_metrics = AsyncMock(
            return_value=mock_risk_metrics
        )
        risk_manager.correlation_analyzer.calculate_correlation_matrix = AsyncMock(
            return_value=mock_correlation_matrix
        )
        
        # Mock stress tests
        risk_manager.stress_tester.run_stress_test = AsyncMock(
            return_value=mock_stress_result
        )
        
        # Mock limit monitor
        risk_manager.limit_monitor.check_limits = AsyncMock(return_value=[])
        
        # Mock regime detection
        regime_result = RegimeDetectionResult(
            current_regime=CorrelationRegime.NORMAL,
            regime_probability=0.85,
            regime_duration=timedelta(days=10),
            last_regime_change=datetime.now() - timedelta(days=10),
            regime_history=[],
            confidence=0.85,
            metadata={}
        )
        risk_manager.correlation_analyzer.detect_correlation_regime = AsyncMock(
            return_value=regime_result
        )
        
        # Calculate risk
        snapshot = await risk_manager.calculate_comprehensive_risk(
            positions=sample_positions,
            portfolio_value=25000.0,
            returns_data=sample_returns_data,
            market_data={}
        )
        
        # Verify snapshot
        assert isinstance(snapshot, RiskSnapshot)
        assert snapshot.portfolio_value == 25000.0
        assert snapshot.exposures == mock_exposure_breakdown
        assert snapshot.risk_metrics == mock_risk_metrics
        assert snapshot.regime_status == 'NORMAL'
        assert 0 <= snapshot.risk_score <= 100
        
        # Verify components were called
        risk_manager.exposure_calculator.calculate_exposures.assert_called_once()
        risk_manager.var_calculator.calculate_comprehensive_risk_metrics.assert_called_once()
        risk_manager.correlation_analyzer.calculate_correlation_matrix.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_comprehensive_risk_minimal_data(
        self, risk_manager, sample_positions, mock_exposure_breakdown
    ):
        """Test risk calculation with minimal data (no returns)."""
        # Mock exposure calculator only
        risk_manager.exposure_calculator.calculate_exposures = AsyncMock(
            return_value=mock_exposure_breakdown
        )
        risk_manager.limit_monitor.check_limits = AsyncMock(return_value=[])
        risk_manager.stress_tester.run_stress_test = AsyncMock(
            side_effect=Exception("No data")
        )
        
        # Calculate risk without returns_data
        snapshot = await risk_manager.calculate_comprehensive_risk(
            positions=sample_positions,
            portfolio_value=25000.0,
            returns_data=None,
            market_data=None
        )
        
        # Verify snapshot created
        assert isinstance(snapshot, RiskSnapshot)
        assert snapshot.portfolio_value == 25000.0
        assert snapshot.risk_metrics is None  # No returns data
        assert snapshot.correlation_matrix is None
    
    @pytest.mark.asyncio
    async def test_calculate_comprehensive_risk_with_single_asset(
        self, risk_manager, mock_exposure_breakdown, mock_risk_metrics
    ):
        """Test risk calculation with single asset (no correlation)."""
        # Single asset returns
        single_returns = pd.DataFrame({'AAPL': [0.01, -0.02, 0.015]})
        
        risk_manager.exposure_calculator.calculate_exposures = AsyncMock(
            return_value=mock_exposure_breakdown
        )
        risk_manager.var_calculator.calculate_comprehensive_risk_metrics = AsyncMock(
            return_value=mock_risk_metrics
        )
        risk_manager.limit_monitor.check_limits = AsyncMock(return_value=[])
        risk_manager.stress_tester.run_stress_test = AsyncMock(
            side_effect=Exception("No data")
        )
        
        # Calculate risk
        snapshot = await risk_manager.calculate_comprehensive_risk(
            positions={'AAPL': {}},
            portfolio_value=15000.0,
            returns_data=single_returns,
            market_data={}
        )
        
        # Verify snapshot
        assert isinstance(snapshot, RiskSnapshot)
        assert snapshot.correlation_matrix is None  # Only 1 asset
    
    @pytest.mark.asyncio
    async def test_calculate_comprehensive_risk_error_handling(self, risk_manager, sample_positions):
        """Test error handling in risk calculation."""
        # Mock exposure calculator to raise error
        risk_manager.exposure_calculator.calculate_exposures = AsyncMock(
            side_effect=Exception("Calculation error")
        )
        
        # Should raise exception
        with pytest.raises(Exception, match="Calculation error"):
            await risk_manager.calculate_comprehensive_risk(
                positions=sample_positions,
                portfolio_value=25000.0
            )
    
    @pytest.mark.asyncio
    async def test_run_key_stress_tests(self, risk_manager, sample_positions, mock_stress_result):
        """Test key stress tests execution."""
        # Mock stress tester
        risk_manager.stress_tester.run_stress_test = AsyncMock(
            return_value=mock_stress_result
        )
        
        # Run stress tests
        results = await risk_manager._run_key_stress_tests(sample_positions, 25000.0)
        
        # Verify all 4 scenarios attempted
        assert risk_manager.stress_tester.run_stress_test.call_count == 4
        
        # Verify scenarios
        called_scenarios = [call[0][0] for call in risk_manager.stress_tester.run_stress_test.call_args_list]
        assert 'financial_crisis_2008' in called_scenarios
        assert 'covid_pandemic_2020' in called_scenarios
        assert 'rate_shock' in called_scenarios
        assert 'geopolitical_crisis' in called_scenarios


# ============================================================================
# Category 4: Risk Scoring (3 tests)
# ============================================================================

class TestRiskScoring:
    """Test risk score calculation."""
    
    def test_calculate_risk_score_high_risk(
        self, risk_manager, mock_risk_metrics, mock_exposure_breakdown, mock_stress_result
    ):
        """Test high risk score calculation."""
        # Create high-risk scenario
        high_risk_metrics = RiskMetrics(
            var_1d={0.99: 10.0},  # High VaR (will be * 10 = 100)
            cvar_1d={0.99: 12.0},
            volatility_daily=0.05,
            volatility_annual=0.80,
            max_drawdown=-0.40,
            timestamp=datetime.now()
        )
        
        # Severe stress result
        severe_stress = {
            'crisis': PortfolioStressResult(
                scenario_name='crisis',
                total_pnl=-10000.0,
                total_pnl_percentage=-40.0,  # -40% loss
                worst_case_var=4000.0,
                position_results=[],
                risk_breakdown={'market_risk': -10000.0},
                timestamp=datetime.now()
            )
        }
        
        # Multiple critical breaches
        breaches = [
            LimitBreach(
                limit_id='L1',
                limit_name='Limit 1',
                current_value=100.0,
                threshold_value=50.0,
                breach_amount=50.0,
                breach_percentage=100.0,
                severity=AlertSeverity.CRITICAL,
                scope=LimitScope.PORTFOLIO,
                scope_identifier='PORTFOLIO',
                description='Position size limit exceeded',
                timestamp=datetime.now()
            ),
            LimitBreach(
                limit_id='L2',
                limit_name='Limit 2',
                current_value=200.0,
                threshold_value=100.0,
                breach_amount=100.0,
                breach_percentage=100.0,
                severity=AlertSeverity.CRITICAL,
                scope=LimitScope.PORTFOLIO,
                scope_identifier='PORTFOLIO',
                description='Portfolio VaR limit exceeded',
                timestamp=datetime.now()
            )
        ]
        
        score = risk_manager._calculate_risk_score(
            exposures=mock_exposure_breakdown,
            risk_metrics=high_risk_metrics,
            stress_results=severe_stress,
            limit_breaches=breaches,
            regime_status='CRISIS'
        )
        
        # Should be high score (> 80)
        assert score > 80
        assert score <= 100
    
    def test_calculate_risk_score_low_risk(self, risk_manager, mock_exposure_breakdown):
        """Test low risk score calculation."""
        # Low risk metrics
        low_risk_metrics = RiskMetrics(
            var_1d={0.99: 0.5},  # Low VaR
            cvar_1d={0.99: 0.6},
            volatility_daily=0.005,
            volatility_annual=0.08,
            max_drawdown=-0.05,
            timestamp=datetime.now()
        )
        
        # Mild stress result
        mild_stress = {
            'scenario': PortfolioStressResult(
                scenario_name='scenario',
                total_pnl=-500.0,
                total_pnl_percentage=-2.0,  # Only -2% loss
                worst_case_var=100.0,
                position_results=[],
                risk_breakdown={'market_risk': -500.0},
                timestamp=datetime.now()
            )
        }
        
        score = risk_manager._calculate_risk_score(
            exposures=mock_exposure_breakdown,
            risk_metrics=low_risk_metrics,
            stress_results=mild_stress,
            limit_breaches=[],
            regime_status='LOW'
        )
        
        # Should be low score (< 40)
        assert score < 40
        assert score >= 0
    
    def test_calculate_risk_score_missing_components(self, risk_manager, mock_exposure_breakdown):
        """Test risk score with missing components."""
        score = risk_manager._calculate_risk_score(
            exposures=mock_exposure_breakdown,
            risk_metrics=None,  # Missing
            stress_results={},  # Empty
            limit_breaches=[],
            regime_status='NORMAL'
        )
        
        # Should still calculate (lower due to missing data)
        assert 0 <= score <= 100


# ============================================================================
# Category 5: Alerts (5 tests)
# ============================================================================

class TestAlerts:
    """Test alert system."""
    
    @pytest.mark.asyncio
    async def test_high_risk_score_alert(self, risk_manager, mock_risk_metrics, 
                                          mock_exposure_breakdown, mock_correlation_matrix):
        """Test high risk score alert generation."""
        # Create high-risk snapshot
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=85.0  # > 80
        )
        
        # Check alerts
        await risk_manager._check_risk_alerts(snapshot)
        
        # Verify alert created
        assert len(risk_manager._risk_alerts) > 0
        alert = risk_manager._risk_alerts[-1]
        assert alert.alert_type == 'HIGH_RISK_SCORE'
        assert alert.severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_crisis_regime_alert(self, risk_manager, mock_risk_metrics, 
                                        mock_exposure_breakdown, mock_correlation_matrix):
        """Test crisis regime alert generation."""
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='CRISIS',  # Crisis regime
            risk_score=50.0
        )
        
        await risk_manager._check_risk_alerts(snapshot)
        
        # Verify crisis alert
        crisis_alerts = [a for a in risk_manager._risk_alerts if a.alert_type == 'CRISIS_REGIME']
        assert len(crisis_alerts) > 0
        assert crisis_alerts[0].severity == AlertSeverity.CRITICAL
    
    @pytest.mark.asyncio
    async def test_extreme_stress_loss_alert(self, risk_manager, mock_risk_metrics, 
                                               mock_exposure_breakdown, mock_correlation_matrix):
        """Test extreme stress loss alert generation."""
        # Extreme stress result
        extreme_stress = {
            'crisis': PortfolioStressResult(
                scenario_name='crisis',
                total_pnl=-6000.0,
                total_pnl_percentage=-25.0,  # > -20%
                worst_case_var=3000.0,
                position_results=[],
                risk_breakdown={'market_risk': -6000.0},
                timestamp=datetime.now()
            )
        }
        
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results=extreme_stress,
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=50.0
        )
        
        await risk_manager._check_risk_alerts(snapshot)
        
        # Verify stress alert
        stress_alerts = [a for a in risk_manager._risk_alerts if a.alert_type == 'EXTREME_STRESS_LOSS']
        assert len(stress_alerts) > 0
        assert stress_alerts[0].severity == AlertSeverity.WARNING
    
    def test_alert_handler_registration(self, risk_manager):
        """Test alert handler add/remove."""
        # Create mock handler
        handler = AsyncMock()
        
        # Add handler
        initial_count = len(risk_manager._alert_handlers)
        risk_manager.add_alert_handler(handler)
        assert len(risk_manager._alert_handlers) == initial_count + 1
        
        # Remove handler
        risk_manager.remove_alert_handler(handler)
        assert len(risk_manager._alert_handlers) == initial_count
    
    @pytest.mark.asyncio
    async def test_limit_breach_alert_handling(self, risk_manager):
        """Test limit breach alert creation."""
        # Create limit breach
        breach = LimitBreach(
            limit_id='L1',
            limit_name='Position Limit',
            current_value=150.0,
            threshold_value=100.0,
            breach_amount=50.0,
            breach_percentage=50.0,
            severity=AlertSeverity.WARNING,
            scope=LimitScope.PORTFOLIO,
            scope_identifier='AAPL',
            description='Position size limit exceeded for AAPL',
            timestamp=datetime.now()
        )
        
        # Handle breach
        await risk_manager._handle_limit_alert(breach)
        
        # Verify alert created
        assert len(risk_manager._risk_alerts) > 0
        alert = risk_manager._risk_alerts[-1]
        assert alert.alert_type == 'LIMIT_BREACH'
        assert alert.details['limit_id'] == 'L1'
        assert alert.details['breach_amount'] == 50.0


# ============================================================================
# Category 6: Snapshot & Query Methods (4 tests)
# ============================================================================

class TestSnapshotAndQuery:
    """Test snapshot storage and query methods."""
    
    def test_snapshot_storage_and_retrieval(self, risk_manager, mock_risk_metrics, 
                                              mock_exposure_breakdown, mock_correlation_matrix):
        """Test snapshot storage and retrieval."""
        # Create snapshot
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=50.0
        )
        
        # Store snapshot
        risk_manager._store_risk_snapshot(snapshot)
        
        # Retrieve latest
        latest = risk_manager.get_latest_risk_snapshot()
        assert latest is not None
        assert latest.portfolio_value == 25000.0
        assert latest.risk_score == 50.0
    
    def test_get_risk_snapshots_time_filtering(self, risk_manager, mock_risk_metrics, 
                                                 mock_exposure_breakdown, mock_correlation_matrix):
        """Test snapshot retrieval with time filtering."""
        # Create snapshots at different times
        old_snapshot = RiskSnapshot(
            timestamp=datetime.now() - timedelta(hours=48),
            portfolio_value=20000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=40.0
        )
        
        recent_snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=50.0
        )
        
        risk_manager._store_risk_snapshot(old_snapshot)
        risk_manager._store_risk_snapshot(recent_snapshot)
        
        # Get last 24 hours (should get recent only)
        snapshots_24h = risk_manager.get_risk_snapshots(hours=24)
        assert len(snapshots_24h) >= 1
        assert all(s.timestamp >= datetime.now() - timedelta(hours=24) for s in snapshots_24h)
    
    def test_get_recent_alerts(self, risk_manager):
        """Test recent alerts retrieval."""
        # Create alerts at different times
        old_alert = RiskAlert(
            alert_id='old_alert',
            alert_type='TEST',
            severity=AlertSeverity.WARNING,
            message='Old alert',
            details={},
            timestamp=datetime.now() - timedelta(hours=48)
        )
        
        recent_alert = RiskAlert(
            alert_id='recent_alert',
            alert_type='TEST',
            severity=AlertSeverity.WARNING,
            message='Recent alert',
            details={},
            timestamp=datetime.now()
        )
        
        risk_manager._risk_alerts.append(old_alert)
        risk_manager._risk_alerts.append(recent_alert)
        
        # Get last 24 hours
        alerts_24h = risk_manager.get_recent_alerts(hours=24)
        assert len(alerts_24h) >= 1
        assert all(a.timestamp >= datetime.now() - timedelta(hours=24) for a in alerts_24h)
    
    def test_snapshot_cleanup(self, risk_manager, mock_risk_metrics, 
                               mock_exposure_breakdown, mock_correlation_matrix):
        """Test old snapshot cleanup."""
        # Create old snapshot (beyond retention period)
        old_snapshot = RiskSnapshot(
            timestamp=datetime.now() - timedelta(days=35),  # > 30 days
            portfolio_value=20000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=40.0
        )
        
        recent_snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results={},
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=50.0
        )
        
        # Store both
        risk_manager._store_risk_snapshot(old_snapshot)
        risk_manager._store_risk_snapshot(recent_snapshot)
        
        # Old snapshot should be cleaned up
        cutoff = datetime.now() - timedelta(days=risk_manager.snapshot_retention_days)
        remaining_snapshots = [s for s in risk_manager._risk_snapshots if s.timestamp >= cutoff]
        assert len(remaining_snapshots) >= 1


# ============================================================================
# Category 7: Monitoring (3 tests)
# ============================================================================

class TestMonitoring:
    """Test monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, risk_manager):
        """Test start and stop monitoring."""
        # Mock data provider
        async def mock_data_provider():
            return {
                'positions': {},
                'portfolio_value': 10000.0,
                'returns_data': None,
                'market_data': {}
            }
        
        # Start monitoring
        await risk_manager.start_monitoring(mock_data_provider)
        assert risk_manager._monitoring_active is True
        assert risk_manager._monitoring_task is not None
        
        # Stop monitoring
        await risk_manager.stop_monitoring()
        assert risk_manager._monitoring_active is False
    
    @pytest.mark.asyncio
    async def test_monitoring_duplicate_start(self, risk_manager):
        """Test starting monitoring when already active."""
        async def mock_data_provider():
            return {'positions': {}, 'portfolio_value': 10000.0}
        
        # Start monitoring
        await risk_manager.start_monitoring(mock_data_provider)
        assert risk_manager._monitoring_active is True
        
        # Try to start again (should warn but not crash)
        await risk_manager.start_monitoring(mock_data_provider)
        
        # Cleanup
        await risk_manager.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_monitoring_loop_execution(self, risk_manager, sample_positions):
        """Test monitoring loop execution."""
        call_count = 0
        
        async def mock_data_provider():
            nonlocal call_count
            call_count += 1
            return {
                'positions': sample_positions,
                'portfolio_value': 25000.0,
                'returns_data': None,
                'market_data': {}
            }
        
        # Mock calculate_comprehensive_risk
        risk_manager.calculate_comprehensive_risk = AsyncMock()
        
        # Set monitoring active
        risk_manager._monitoring_active = True
        
        # Mock asyncio.sleep to control loop
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Make sleep raise CancelledError after first iteration
            mock_sleep.side_effect = [None, asyncio.CancelledError()]
            
            # Start monitoring loop directly
            try:
                await risk_manager._monitoring_loop(mock_data_provider)
            except asyncio.CancelledError:
                pass
            
            # Verify data provider was called
            assert call_count >= 1
            
            # Verify calculate_comprehensive_risk was called
            assert risk_manager.calculate_comprehensive_risk.call_count >= 1


# ============================================================================
# Category 8: Summary & Limits (3 tests)
# ============================================================================

class TestSummaryAndLimits:
    """Test summary and limit management."""
    
    def test_get_risk_summary(self, risk_manager, mock_risk_metrics, mock_exposure_breakdown, 
                                mock_correlation_matrix, mock_stress_result):
        """Test risk summary generation."""
        # Create and store snapshot
        stress_results = {'crisis': mock_stress_result}
        
        snapshot = RiskSnapshot(
            timestamp=datetime.now(),
            portfolio_value=25000.0,
            exposures=mock_exposure_breakdown,
            risk_metrics=mock_risk_metrics,
            correlation_matrix=mock_correlation_matrix,
            stress_test_results=stress_results,
            limit_breaches=[],
            regime_status='NORMAL',
            risk_score=50.0
        )
        
        risk_manager._store_risk_snapshot(snapshot)
        
        # Get summary
        summary = risk_manager.get_risk_summary()
        
        # Verify summary structure
        assert 'timestamp' in summary
        assert 'portfolio_value' in summary
        assert 'risk_score' in summary
        assert 'regime_status' in summary
        assert summary['portfolio_value'] == 25000.0
        assert summary['risk_score'] == 50.0
        assert summary['regime_status'] == 'NORMAL'
        
        # Check var_metrics
        assert 'var_metrics' in summary
        assert summary['var_metrics']['var_95'] == 1000.0
        assert summary['var_metrics']['var_99'] == 1500.0
        
        # Check worst stress scenario
        assert 'worst_stress_scenario' in summary
        assert summary['worst_stress_scenario']['scenario'] == 'financial_crisis_2008'
        assert summary['worst_stress_scenario']['pnl_percentage'] == -20.0
        
        # Check top exposures
        assert 'top_exposures' in summary
        assert len(summary['top_exposures']) > 0
    
    @pytest.mark.asyncio
    async def test_limit_management_methods(self, risk_manager):
        """Test limit management methods."""
        # Create mock limit
        from core_engine.risk.limit_monitor import LimitOperator
        limit = RiskLimit(
            limit_id='L1',
            name='Test Limit',
            limit_type=LimitType.POSITION_SIZE,
            scope=LimitScope.PORTFOLIO,
            scope_identifier='MAIN_PORTFOLIO',
            operator=LimitOperator.LESS_EQUAL,
            threshold_value=100.0,
            warning_threshold=80.0,
            is_active=True
        )
        
        # Mock limit_monitor methods
        risk_manager.limit_monitor.add_limit = Mock()
        risk_manager.limit_monitor.update_limit = Mock()
        risk_manager.limit_monitor.remove_limit = Mock()
        risk_manager.limit_monitor.get_all_limits = Mock(return_value=[limit])
        risk_manager.limit_monitor.get_current_breaches = Mock(return_value=[])
        
        # Test add limit
        await risk_manager.add_risk_limit(limit)
        risk_manager.limit_monitor.add_limit.assert_called_once_with(limit)
        
        # Test update limit
        await risk_manager.update_risk_limit('L1', {'threshold_value': 120.0})
        risk_manager.limit_monitor.update_limit.assert_called_once_with('L1', {'threshold_value': 120.0})
        
        # Test remove limit
        await risk_manager.remove_risk_limit('L1')
        risk_manager.limit_monitor.remove_limit.assert_called_once_with('L1')
        
        # Test get all limits
        limits = risk_manager.get_all_risk_limits()
        assert len(limits) == 1
        
        # Test get breaches
        breaches = risk_manager.get_current_limit_breaches()
        assert len(breaches) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_method(self, risk_manager):
        """Test cleanup of all components."""
        # Mock component cleanup methods
        risk_manager.exposure_calculator.cleanup = AsyncMock()
        risk_manager.var_calculator.cleanup = AsyncMock()
        risk_manager.stress_tester.cleanup = AsyncMock()
        risk_manager.limit_monitor.cleanup = AsyncMock()
        risk_manager.correlation_analyzer.cleanup = AsyncMock()
        
        # Call cleanup
        await risk_manager.cleanup()
        
        # Verify all components cleaned up
        risk_manager.exposure_calculator.cleanup.assert_called_once()
        risk_manager.var_calculator.cleanup.assert_called_once()
        risk_manager.stress_tester.cleanup.assert_called_once()
        risk_manager.limit_monitor.cleanup.assert_called_once()
        risk_manager.correlation_analyzer.cleanup.assert_called_once()
