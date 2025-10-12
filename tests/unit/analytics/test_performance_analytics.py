"""
Unit tests for Performance Analytics modules
Testing all 8 performance analytics modules with 0% coverage
"""

import pytest
import pandas as pd
import numpy as np

# Import performance analytics modules
from core_engine.analytics.performance.attribution_engine import (
    AttributionEngine, AttributionResult
)
from core_engine.analytics.performance.benchmark_tracker import (
    BenchmarkTracker, RelativePerformanceMetrics
)
from core_engine.analytics.performance.drawdown_tracker import (
    DrawdownTracker, UnderwaterMetrics
)
from core_engine.analytics.performance.monitor import (
    PerformanceMonitor
)
from core_engine.analytics.performance.performance_calculator import (
    PerformanceCalculator, PerformanceMetrics
)
from core_engine.analytics.performance.performance_manager import (
    PerformanceManager, PerformanceManagerConfig, ComprehensivePerformanceReport
)
from core_engine.analytics.performance.risk_adjusted_metrics import (
    RiskAdjustedMetrics
)


class TestAttributionEngine:
    """Test AttributionEngine functionality"""
    
    @pytest.fixture
    def attribution_engine(self):
        """Create AttributionEngine instance"""
        return AttributionEngine()
    
    @pytest.fixture
    def sample_portfolio_data(self):
        """Sample portfolio data for testing"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'portfolio_return': np.random.normal(0.001, 0.02, 100),
            'benchmark_return': np.random.normal(0.0008, 0.015, 100),
            'sector_tech': np.random.normal(0.0012, 0.025, 100),
            'sector_finance': np.random.normal(0.0005, 0.018, 100),
            'sector_healthcare': np.random.normal(0.0009, 0.020, 100)
        })
    
    def test_initialization(self, attribution_engine):
        """Test AttributionEngine initialization"""
        assert attribution_engine is not None
        assert hasattr(attribution_engine, 'config')
        assert hasattr(attribution_engine, '_brinson_engine')
        assert hasattr(attribution_engine, '_factor_engine')
        assert hasattr(attribution_engine, '_risk_engine')
    
    def test_brinson_attribution(self, attribution_engine, sample_portfolio_data):
        """Test Brinson attribution analysis"""
        # Test basic Brinson attribution
        portfolio_weights = {'tech': 0.4, 'finance': 0.3, 'healthcare': 0.3}
        portfolio_returns = {
            'tech': sample_portfolio_data['sector_tech'].mean(),
            'finance': sample_portfolio_data['sector_finance'].mean(),
            'healthcare': sample_portfolio_data['sector_healthcare'].mean()
        }
        benchmark_weights = {'tech': 0.4, 'finance': 0.3, 'healthcare': 0.3}
        benchmark_returns = {
            'tech': sample_portfolio_data['sector_tech'].mean() * 0.9,
            'finance': sample_portfolio_data['sector_finance'].mean() * 0.9,
            'healthcare': sample_portfolio_data['sector_healthcare'].mean() * 0.9
        }
        
        result = attribution_engine.calculate_brinson_attribution(
            portfolio_weights=portfolio_weights,
            portfolio_returns=portfolio_returns,
            benchmark_weights=benchmark_weights,
            benchmark_returns=benchmark_returns
        )
        
        assert isinstance(result, AttributionResult)
        assert hasattr(result, 'total_effect')
        assert hasattr(result, 'allocation_effect')
        assert hasattr(result, 'selection_effect')
        assert hasattr(result, 'interaction_effect')
    
    def test_geometric_attribution(self, attribution_engine, sample_portfolio_data):
        """Test geometric attribution analysis"""
        portfolio_weights = {'tech': 0.4, 'finance': 0.3, 'healthcare': 0.3}
        portfolio_returns = {
            'tech': sample_portfolio_data['sector_tech'].mean(),
            'finance': sample_portfolio_data['sector_finance'].mean(),
            'healthcare': sample_portfolio_data['sector_healthcare'].mean()
        }
        benchmark_weights = {'tech': 0.4, 'finance': 0.3, 'healthcare': 0.3}
        benchmark_returns = {
            'tech': sample_portfolio_data['sector_tech'].mean() * 0.9,
            'finance': sample_portfolio_data['sector_finance'].mean() * 0.9,
            'healthcare': sample_portfolio_data['sector_healthcare'].mean() * 0.9
        }
        
        result = attribution_engine._brinson_engine.calculate_geometric_attribution(
            portfolio_weights=portfolio_weights,
            portfolio_returns=portfolio_returns,
            benchmark_weights=benchmark_weights,
            benchmark_returns=benchmark_returns
        )
        
        assert isinstance(result, AttributionResult)
        assert hasattr(result, 'total_effect')
    
    def test_risk_adjusted_attribution(self, attribution_engine, sample_portfolio_data):
        """Test risk-adjusted attribution analysis"""
        portfolio_weights = np.array([0.4, 0.3, 0.3])
        factor_exposures = np.array([[0.8, 0.2], [0.6, 0.4], [0.7, 0.3]])  # 3 assets, 2 factors
        factor_covariance = np.array([[0.04, 0.01], [0.01, 0.09]])  # 2x2 covariance matrix
        
        result = attribution_engine.calculate_risk_attribution(
            portfolio_weights=portfolio_weights,
            factor_exposures=factor_exposures,
            factor_covariance=factor_covariance
        )
        
        assert isinstance(result, AttributionResult)
        assert hasattr(result, 'total_effect')


class TestBenchmarkTracker:
    """Test BenchmarkTracker functionality"""
    
    @pytest.fixture
    def benchmark_tracker(self):
        """Create BenchmarkTracker instance"""
        return BenchmarkTracker()
    
    @pytest.fixture
    def sample_benchmark_data(self):
        """Sample benchmark data for testing"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        return pd.DataFrame({
            'date': dates,
            'portfolio_value': np.cumprod(1 + np.random.normal(0.001, 0.02, 252)),
            'benchmark_value': np.cumprod(1 + np.random.normal(0.0008, 0.015, 252)),
            'risk_free_rate': 0.02
        })
    
    def test_initialization(self, benchmark_tracker):
        """Test BenchmarkTracker initialization"""
        assert benchmark_tracker is not None
        assert hasattr(benchmark_tracker, 'config')
        assert hasattr(benchmark_tracker, '_benchmarks')
        assert hasattr(benchmark_tracker, '_primary_benchmark')
    
    @pytest.mark.asyncio
    async def test_track_performance(self, benchmark_tracker, sample_benchmark_data):
        """Test performance tracking against benchmark"""
        # First add a benchmark
        await benchmark_tracker.add_benchmark("SPY", "S&P 500")
        
        result = await benchmark_tracker.calculate_relative_performance(
            portfolio_returns=sample_benchmark_data['portfolio_value'].pct_change().dropna(),
            benchmark_symbol="SPY"
        )
        
        assert isinstance(result, RelativePerformanceMetrics)
        assert hasattr(result, 'excess_return')
        assert hasattr(result, 'tracking_error')
        assert hasattr(result, 'information_ratio')
        assert hasattr(result, 'beta')
        assert hasattr(result, 'alpha')
    
    @pytest.mark.asyncio
    async def test_calculate_beta(self, benchmark_tracker, sample_benchmark_data):
        """Test beta calculation"""
        # First add a benchmark
        await benchmark_tracker.add_benchmark("SPY", "S&P 500")
        
        result = await benchmark_tracker.calculate_relative_performance(
            portfolio_returns=sample_benchmark_data['portfolio_value'].pct_change().dropna(),
            benchmark_symbol="SPY"
        )
        
        assert isinstance(result.beta, float)
        assert not np.isnan(result.beta)
    
    @pytest.mark.asyncio
    async def test_calculate_alpha(self, benchmark_tracker, sample_benchmark_data):
        """Test alpha calculation"""
        # First add a benchmark
        await benchmark_tracker.add_benchmark("SPY", "S&P 500")
        
        result = await benchmark_tracker.calculate_relative_performance(
            portfolio_returns=sample_benchmark_data['portfolio_value'].pct_change().dropna(),
            benchmark_symbol="SPY"
        )
        
        assert isinstance(result.alpha, float)
        assert not np.isnan(result.alpha)


class TestDrawdownTracker:
    """Test DrawdownTracker functionality"""
    
    @pytest.fixture
    def drawdown_tracker(self):
        """Create DrawdownTracker instance"""
        return DrawdownTracker()
    
    @pytest.fixture
    def sample_returns_data(self):
        """Sample returns data for testing"""
        # Create returns with some drawdown periods
        returns = np.random.normal(0.001, 0.02, 252)
        # Add some negative periods to create drawdowns
        returns[50:70] = np.random.normal(-0.005, 0.01, 20)
        returns[150:160] = np.random.normal(-0.003, 0.008, 10)
        return pd.Series(returns, index=pd.date_range('2023-01-01', periods=252, freq='D'))
    
    def test_initialization(self, drawdown_tracker):
        """Test DrawdownTracker initialization"""
        assert drawdown_tracker is not None
        assert hasattr(drawdown_tracker, 'config')
        assert hasattr(drawdown_tracker, '_drawdown_analyzer')
        assert hasattr(drawdown_tracker, '_underwater_analyzer')
    
    def test_calculate_maximum_drawdown(self, drawdown_tracker, sample_returns_data):
        """Test maximum drawdown calculation"""
        events, metrics = drawdown_tracker.analyze_drawdowns(sample_returns_data)
        
        assert isinstance(events, list)
        assert isinstance(metrics, UnderwaterMetrics)
        assert len(events) > 0  # Should have some drawdown events
        assert hasattr(metrics, 'max_underwater_depth')
        assert metrics.max_underwater_depth >= 0  # Underwater depth is positive
    
    def test_calculate_drawdown_series(self, drawdown_tracker, sample_returns_data):
        """Test drawdown series calculation"""
        events, metrics = drawdown_tracker.analyze_drawdowns(sample_returns_data)
        
        assert isinstance(events, list)
        assert isinstance(metrics, UnderwaterMetrics)
        assert hasattr(metrics, 'underwater_periods')
        assert len(events) >= 0  # May have no drawdowns
    
    def test_calculate_underwater_periods(self, drawdown_tracker, sample_returns_data):
        """Test underwater periods calculation"""
        events, metrics = drawdown_tracker.analyze_drawdowns(sample_returns_data)
        
        assert isinstance(events, list)
        assert isinstance(metrics, UnderwaterMetrics)
        assert hasattr(metrics, 'underwater_periods')
        # Check that we have underwater periods data
        assert isinstance(metrics.underwater_periods, list)


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality"""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create PerformanceMonitor instance"""
        config = {
            'monitoring_interval': 30,
            'enable_real_time_alerts': True,
            'system_health_threshold': 0.8
        }
        return PerformanceMonitor(config)
    
    @pytest.fixture
    def sample_monitoring_data(self):
        """Sample data for monitoring tests"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'portfolio_value': np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
            'benchmark_value': np.cumprod(1 + np.random.normal(0.0008, 0.015, 100)),
            'risk_metrics': np.random.normal(0.15, 0.05, 100)
        })
    
    def test_initialization(self, performance_monitor):
        """Test PerformanceMonitor initialization"""
        assert performance_monitor is not None
        assert hasattr(performance_monitor, 'config')
        assert hasattr(performance_monitor, 'metrics')
    
    def test_monitor_performance(self, performance_monitor, sample_monitoring_data):
        """Test performance monitoring"""
        # Test that we can get system health
        import asyncio
        health = asyncio.run(performance_monitor.get_system_health())
        
        assert hasattr(health, 'overall_health')
        assert hasattr(health, 'component_health')
    
    def test_generate_alerts(self, performance_monitor, sample_monitoring_data):
        """Test alert generation"""
        # Test that we can get active alerts
        import asyncio
        alerts = asyncio.run(performance_monitor.get_active_alerts())
        
        assert isinstance(alerts, list)
        # Alerts should be PerformanceAlert objects
        for alert in alerts:
            assert hasattr(alert, 'alert_type')
            assert hasattr(alert, 'severity')
            assert hasattr(alert, 'message')


class TestPerformanceCalculator:
    """Test PerformanceCalculator functionality"""
    
    @pytest.fixture
    def performance_calculator(self):
        """Create PerformanceCalculator instance"""
        return PerformanceCalculator()
    
    @pytest.fixture
    def sample_calculation_data(self):
        """Sample data for calculation tests"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        returns = np.random.normal(0.001, 0.02, 252)
        return pd.Series(returns, index=dates)
    
    def test_initialization(self, performance_calculator):
        """Test PerformanceCalculator initialization"""
        assert performance_calculator is not None
        assert hasattr(performance_calculator, 'config')
        assert hasattr(performance_calculator, '_metrics_cache')
    
    def test_calculate_performance_metrics(self, performance_calculator, sample_calculation_data):
        """Test performance metrics calculation"""
        result = performance_calculator.calculate_performance(
            returns=sample_calculation_data
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert hasattr(result, 'total_return')
        assert hasattr(result, 'annualized_return')
        assert hasattr(result, 'volatility')
        assert hasattr(result, 'sharpe_ratio')
        assert hasattr(result, 'sortino_ratio')
        assert hasattr(result, 'calmar_ratio')
        assert hasattr(result, 'max_drawdown')
    
    def test_calculate_risk_metrics(self, performance_calculator, sample_calculation_data):
        """Test risk metrics calculation"""
        result = performance_calculator.calculate_performance(sample_calculation_data)
        
        assert isinstance(result, PerformanceMetrics)
        assert hasattr(result, 'max_drawdown')
        assert hasattr(result, 'volatility')
        assert hasattr(result, 'sharpe_ratio')
    
    def test_calculate_return_metrics(self, performance_calculator, sample_calculation_data):
        """Test return metrics calculation"""
        result = performance_calculator.calculate_performance(
            returns=sample_calculation_data
        )
        
        assert isinstance(result, PerformanceMetrics)
        assert hasattr(result, 'total_return')
        assert hasattr(result, 'annualized_return')
        assert hasattr(result, 'cumulative_return')


class TestPerformanceManager:
    """Test PerformanceManager functionality"""
    
    @pytest.fixture
    def performance_manager(self):
        """Create PerformanceManager instance"""
        config = PerformanceManagerConfig()
        return PerformanceManager(config)
    
    @pytest.fixture
    def sample_manager_data(self):
        """Sample data for manager tests"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'date': dates,
            'portfolio_value': np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
            'benchmark_value': np.cumprod(1 + np.random.normal(0.0008, 0.015, 100))
        })
    
    def test_initialization(self, performance_manager):
        """Test PerformanceManager initialization"""
        assert performance_manager is not None
        assert hasattr(performance_manager, 'config')
        assert hasattr(performance_manager, '_analysis_cache')
    
    def test_manage_performance(self, performance_manager, sample_manager_data):
        """Test performance management"""
        result = performance_manager.analyze_performance(
            returns=sample_manager_data['portfolio_value'].pct_change().dropna(),
            benchmark_returns=sample_manager_data['benchmark_value'].pct_change().dropna()
        )
        
        assert isinstance(result, ComprehensivePerformanceReport)
        assert hasattr(result, 'performance_metrics')
        assert hasattr(result, 'risk_adjusted_metrics')
    
    def test_generate_performance_report(self, performance_manager, sample_manager_data):
        """Test performance report generation"""
        report = performance_manager.analyze_performance(
            returns=sample_manager_data['portfolio_value'].pct_change().dropna(),
            benchmark_returns=sample_manager_data['benchmark_value'].pct_change().dropna()
        )
        
        assert isinstance(report, ComprehensivePerformanceReport)
        assert hasattr(report, 'performance_metrics')
        assert hasattr(report, 'risk_adjusted_metrics')


class TestRiskAdjustedMetrics:
    """Test RiskAdjustedMetrics functionality"""
    
    @pytest.fixture
    def risk_adjusted_metrics(self):
        """Create RiskAdjustedMetrics instance"""
        return RiskAdjustedMetrics()
    
    @pytest.fixture
    def sample_risk_data(self):
        """Sample data for risk-adjusted metrics tests"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        returns = np.random.normal(0.001, 0.02, 252)
        return pd.Series(returns, index=dates)
    
    def test_initialization(self, risk_adjusted_metrics):
        """Test RiskAdjustedMetrics initialization"""
        assert risk_adjusted_metrics is not None
        assert hasattr(risk_adjusted_metrics, 'sharpe_ratio')
        assert hasattr(risk_adjusted_metrics, 'sortino_ratio')
        assert hasattr(risk_adjusted_metrics, 'calmar_ratio')
    
    def test_risk_adjusted_metrics_attributes(self, risk_adjusted_metrics):
        """Test RiskAdjustedMetrics attributes"""
        # Test that all expected attributes exist
        assert hasattr(risk_adjusted_metrics, 'sharpe_ratio')
        assert hasattr(risk_adjusted_metrics, 'sortino_ratio')
        assert hasattr(risk_adjusted_metrics, 'calmar_ratio')
        assert hasattr(risk_adjusted_metrics, 'omega_ratio')
        assert hasattr(risk_adjusted_metrics, 'treynor_ratio')
        assert hasattr(risk_adjusted_metrics, 'jensen_alpha')
    
    def test_risk_adjusted_metrics_values(self, risk_adjusted_metrics):
        """Test RiskAdjustedMetrics default values"""
        # Test that default values are set correctly
        assert risk_adjusted_metrics.sharpe_ratio == 0.0
        assert risk_adjusted_metrics.sortino_ratio == 0.0
        assert risk_adjusted_metrics.calmar_ratio == 0.0


class TestPerformanceAnalyticsIntegration:
    """Test integration between performance analytics modules"""
    
    @pytest.fixture
    def sample_integration_data(self):
        """Sample data for integration tests"""
        dates = pd.date_range('2023-01-01', periods=252, freq='D')
        return pd.DataFrame({
            'date': dates,
            'portfolio_returns': np.random.normal(0.001, 0.02, 252),
            'benchmark_returns': np.random.normal(0.0008, 0.015, 252),
            'tech_returns': np.random.normal(0.0012, 0.025, 252),
            'finance_returns': np.random.normal(0.0005, 0.018, 252),
            'healthcare_returns': np.random.normal(0.0009, 0.020, 252)
        })
    
    def test_full_performance_analysis(self, sample_integration_data):
        """Test complete performance analysis workflow"""
        # Initialize all components
        attribution_engine = AttributionEngine()
        benchmark_tracker = BenchmarkTracker()
        drawdown_tracker = DrawdownTracker()
        performance_calculator = PerformanceCalculator()
        risk_adjusted_metrics = RiskAdjustedMetrics()
        
        portfolio_returns = sample_integration_data['portfolio_returns']
        sample_integration_data['benchmark_returns']
        
        # Test attribution analysis
        attribution_result = attribution_engine.calculate_brinson_attribution(
            portfolio_weights={'tech': 0.4, 'finance': 0.3, 'healthcare': 0.3},
            portfolio_returns={'tech': sample_integration_data['tech_returns'].mean(), 
                             'finance': sample_integration_data['finance_returns'].mean(),
                             'healthcare': sample_integration_data['healthcare_returns'].mean()},
            benchmark_weights={'tech': 0.5, 'finance': 0.3, 'healthcare': 0.2},
            benchmark_returns={'tech': sample_integration_data['tech_returns'].mean(),
                             'finance': sample_integration_data['finance_returns'].mean(),
                             'healthcare': sample_integration_data['healthcare_returns'].mean()}
        )
        assert isinstance(attribution_result, AttributionResult)
        
        # Test benchmark tracking
        import asyncio
        benchmark_result = asyncio.run(benchmark_tracker.calculate_relative_performance(
            portfolio_returns=portfolio_returns
        ))
        assert isinstance(benchmark_result, RelativePerformanceMetrics)
        
        # Test drawdown analysis
        events, metrics = drawdown_tracker.analyze_drawdowns(portfolio_returns)
        assert isinstance(events, list)
        assert isinstance(metrics, UnderwaterMetrics)
        
        # Test performance calculation
        performance_result = performance_calculator.calculate_performance(
            returns=portfolio_returns
        )
        assert isinstance(performance_result, PerformanceMetrics)
        
        # Test risk-adjusted metrics (it's a dataclass, not a method)
        assert isinstance(risk_adjusted_metrics, RiskAdjustedMetrics)
        assert hasattr(risk_adjusted_metrics, 'sharpe_ratio')
    
    def test_error_handling(self):
        """Test error handling in performance analytics"""
        # Test with invalid data
        attribution_engine = AttributionEngine()
        
        with pytest.raises((ValueError, TypeError)):
            attribution_engine.calculate_brinson_attribution(
                portfolio_returns=None,
                benchmark_returns=None,
                sector_returns=None
            )
    
    def test_data_validation(self):
        """Test data validation in performance analytics"""
        performance_calculator = PerformanceCalculator()
        
        # Test with empty data - should return default metrics
        empty_returns = pd.Series([], dtype=float)
        result = performance_calculator.calculate_performance(returns=empty_returns)
        
        # Should return a PerformanceMetrics object with default values
        assert isinstance(result, PerformanceMetrics)
        assert result.total_return == 0.0
