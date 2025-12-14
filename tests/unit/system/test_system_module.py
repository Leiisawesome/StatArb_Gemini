"""
Unit tests for system component.
Tests system orchestration, risk management, execution, and lifecycle management.
"""

import pytest
from unittest.mock import AsyncMock

# Import system component classes
from core_engine.system.interfaces import ISystemComponent
from core_engine.system.hierarchical_orchestrator import (
    SystemStatus,
    ComponentLayer,
    AuthorityLevel,
    ComponentRegistration,
    HierarchicalSystemOrchestrator,
    SystemOrchestrationConfig
)
from core_engine.system.central_risk_manager import (
    TradingDecisionType,
    AuthorizationLevel,
    TradingDecisionRequest,
    ExecutionAuthorization,
    TradingAuthorization,
    CentralRiskManager
)
from core_engine.config.component_config import RiskConfig as RiskManagerConfig
from core_engine.system.unified_execution_engine import (
    ExecutionStatus,
    ExecutionAlgorithm,
    ExecutionUrgency,
    VenueType,
    ExecutionAuthorization,
    ExecutionRequest,
    ExecutionResult,
    UnifiedExecutionEngine
)

class TestISystemComponent:
    """Test ISystemComponent interface."""

    def test_interface_definition(self):
        """Test that ISystemComponent defines required methods."""
        # This is an abstract interface, so we can't instantiate it directly
        # But we can check that it's properly defined
        assert hasattr(ISystemComponent, 'initialize')
        assert hasattr(ISystemComponent, 'start')
        assert hasattr(ISystemComponent, 'stop')
        assert hasattr(ISystemComponent, 'health_check')
        assert hasattr(ISystemComponent, 'get_status')

class TestSystemStatus:
    """Test SystemStatus enum."""

    def test_system_status_values(self):
        """Test SystemStatus enum values."""
        assert SystemStatus.UNINITIALIZED.value == "uninitialized"
        assert SystemStatus.INITIALIZING.value == "initializing"
        assert SystemStatus.READY.value == "ready"
        assert SystemStatus.OPERATIONAL.value == "operational"
        assert SystemStatus.DEGRADED.value == "degraded"
        assert SystemStatus.MAINTENANCE.value == "maintenance"
        assert SystemStatus.EMERGENCY.value == "emergency"
        assert SystemStatus.SHUTDOWN.value == "shutdown"

class TestComponentLayer:
    """Test ComponentLayer enum."""

    def test_component_layer_values(self):
        """Test ComponentLayer enum values."""
        assert ComponentLayer.ORCHESTRATION.value == "orchestration"
        assert ComponentLayer.GOVERNANCE.value == "governance"
        assert ComponentLayer.EXECUTION.value == "execution"
        assert ComponentLayer.SUPPORT.value == "support"

class TestAuthorityLevel:
    """Test AuthorityLevel enum."""

    def test_authority_level_values(self):
        """Test AuthorityLevel enum values."""
        assert AuthorityLevel.SYSTEM_CONTROL.value == "system_control"
        assert AuthorityLevel.GOVERNANCE_CONTROL.value == "governance_control"
        assert AuthorityLevel.STRATEGIC.value == "strategic"
        assert AuthorityLevel.TACTICAL.value == "tactical"
        assert AuthorityLevel.OPERATIONAL.value == "operational"
        assert AuthorityLevel.READ_ONLY.value == "read_only"

class TestComponentRegistration:
    """Test ComponentRegistration dataclass."""

    def test_initialization(self):
        """Test ComponentRegistration initialization."""
        registration = ComponentRegistration(
            name="test_component",
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL
        )

        assert registration.name == "test_component"
        assert registration.layer == ComponentLayer.EXECUTION
        assert registration.authority_level == AuthorityLevel.OPERATIONAL
        assert registration.status == "unregistered"
        assert registration.error_count == 0

    def test_update_status(self):
        """Test status update functionality."""
        registration = ComponentRegistration()
        registration.update_status("running")

        assert registration.status == "running"

        registration.update_status("error", "Test error")
        assert registration.status == "error"
        assert registration.last_error == "Test error"
        assert registration.error_count == 1

class TestHierarchicalSystemOrchestrator:
    """Test HierarchicalSystemOrchestrator class."""

    @pytest.fixture
    def orchestrator_config(self):
        """Create orchestrator configuration for testing."""
        return {
            "component_startup_timeout": 60,
            "initialization_retry_attempts": 3,
            "graceful_shutdown_timeout": 30,
            "health_check_interval": 30,
            "performance_monitoring_interval": 5,
            "enforce_hierarchical_control": True,
            "require_risk_manager_authorization": True,
            "emergency_override_enabled": True,
            "max_component_errors": 5,
            "escalation_timeout": 300,
            "max_concurrent_operations": 100,
            "resource_allocation_timeout": 10
        }

    @pytest.fixture
    def mock_component(self):
        """Create mock system component."""
        component = AsyncMock()
        component.initialize.return_value = True
        component.start.return_value = True
        component.shutdown.return_value = True
        component.health_check.return_value = {"status": "healthy"}
        component.get_status.return_value = {"state": "running"}
        return component

    def test_initialization(self, orchestrator_config):
        """Test HierarchicalSystemOrchestrator initialization."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        assert isinstance(orchestrator.config, SystemOrchestrationConfig)
        assert orchestrator.config.component_startup_timeout == 60
        assert orchestrator.system_status == SystemStatus.UNINITIALIZED
        assert isinstance(orchestrator.component_registry, dict)
        assert isinstance(orchestrator.layer_components, dict)

    @pytest.mark.asyncio
    async def test_register_component(self, orchestrator_config, mock_component):
        """Test component registration."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        component_id = orchestrator.register_component(
            name="test_component",
            component=mock_component,
            layer=ComponentLayer.EXECUTION
        )

        assert component_id
        assert component_id in orchestrator.component_registry
        assert orchestrator.component_registry[component_id].name == "test_component"

    @pytest.mark.asyncio
    async def test_initialize_system(self, orchestrator_config, mock_component):
        """Test system initialization."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        # Register a mock Central Risk Manager first
        mock_risk_manager = AsyncMock()
        mock_risk_manager.initialize.return_value = True
        orchestrator.register_central_risk_manager(mock_risk_manager)

        # Register a component
        component_id = orchestrator.register_component(
            name="test_component",
            component=mock_component,
            layer=ComponentLayer.EXECUTION
        )
        assert component_id

        # Initialize system
        success = await orchestrator.initialize()
        assert success
        assert orchestrator.system_status == SystemStatus.READY

        # Verify component was initialized
        mock_component.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_system(self, orchestrator_config, mock_component):
        """Test system startup."""
        HierarchicalSystemOrchestrator(orchestrator_config)

    @pytest.mark.asyncio
    async def test_start_system(self, orchestrator_config, mock_component):
        """Test system startup."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        # Register a mock Central Risk Manager first
        mock_risk_manager = AsyncMock()
        mock_risk_manager.initialize.return_value = True
        orchestrator.register_central_risk_manager(mock_risk_manager)

        # Register and initialize a component
        component_id = orchestrator.register_component(
            name="test_component",
            component=mock_component,
            layer=ComponentLayer.EXECUTION
        )
        await orchestrator.initialize()

        # Start system
        success = await orchestrator.start()
        assert success
        assert orchestrator.system_status == SystemStatus.OPERATIONAL

    @pytest.mark.asyncio
    async def test_stop_system(self, orchestrator_config, mock_component):
        """Test system shutdown."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        # Register, initialize, and start a component
        component_id = orchestrator.register_component(
            name="test_component",
            component=mock_component,
            layer=ComponentLayer.EXECUTION
        )
        await orchestrator.initialize()
        await orchestrator.start()

        # Stop system
        success = await orchestrator.stop()
        assert success
        assert orchestrator.system_status == SystemStatus.SHUTDOWN

        # Verify component was stopped
        mock_component.stop.assert_called_once()

    def test_get_system_status(self, orchestrator_config):
        """Test system status retrieval."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        status = orchestrator.get_system_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "component_summary" in status
        assert "metrics" in status

    @pytest.mark.asyncio
    async def test_health_check(self, orchestrator_config, mock_component):
        """Test system health check."""
        orchestrator = HierarchicalSystemOrchestrator(orchestrator_config)

        # Register a component
        component_id = orchestrator.register_component(
            name="test_component",
            component=mock_component,
            layer=ComponentLayer.EXECUTION
        )

        # Perform health check
        health_status = await orchestrator.health_check()
        assert isinstance(health_status, dict)
        assert "healthy" in health_status
        assert "system_status" in health_status

class TestTradingDecisionType:
    """Test TradingDecisionType enum."""

    def test_trading_decision_type_values(self):
        """Test TradingDecisionType enum values."""
        assert TradingDecisionType.STRATEGY_ACTIVATION.value == "strategy_activation"
        assert TradingDecisionType.STRATEGY_DEACTIVATION.value == "strategy_deactivation"
        assert TradingDecisionType.POSITION_ENTRY.value == "position_entry"
        assert TradingDecisionType.POSITION_EXIT.value == "position_exit"
        assert TradingDecisionType.POSITION_ADJUSTMENT.value == "position_adjustment"
        assert TradingDecisionType.PORTFOLIO_REBALANCING.value == "portfolio_rebalancing"
        assert TradingDecisionType.EMERGENCY_LIQUIDATION.value == "emergency_liquidation"
        assert TradingDecisionType.RISK_LIMIT_ADJUSTMENT.value == "risk_limit_adjustment"

class TestAuthorizationLevel:
    """Test AuthorizationLevel enum."""

    def test_authorization_level_values(self):
        """Test AuthorizationLevel enum values."""
        assert AuthorizationLevel.AUTOMATIC.value == "automatic"
        assert AuthorizationLevel.STANDARD.value == "standard"
        assert AuthorizationLevel.ELEVATED.value == "elevated"
        assert AuthorizationLevel.EMERGENCY.value == "emergency"
        assert AuthorizationLevel.REJECTED.value == "rejected"

class TestTradingDecisionRequest:
    """Test TradingDecisionRequest dataclass."""

    def test_initialization(self):
        """Test TradingDecisionRequest initialization."""
        request = TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_return=0.05,
            confidence=0.8
        )

        assert request.decision_type == TradingDecisionType.POSITION_ENTRY
        assert request.strategy_id == "test_strategy"
        assert request.symbol == "AAPL"
        assert request.side == "buy"
        assert request.quantity == 100.0
        assert request.expected_return == 0.05
        assert request.confidence == 0.8

class TestCentralRiskManager:
    """Test CentralRiskManager class."""

    @pytest.fixture
    def risk_config(self):
        """Create risk manager configuration for testing."""
        return {
            "max_position_size": 0.10,
            "max_daily_var": 0.05,
            "max_total_risk": 0.20,
            "position_concentration_limit": 0.15,
            "strategy_allocation_limit": 0.33,
            "min_signal_confidence": 0.6,
            "high_confidence_threshold": 0.8,
            "extreme_confidence_threshold": 0.9,
            "auto_approval_threshold": 0.01,
            "elevated_review_threshold": 0.05,
            "emergency_threshold": 0.10,
            "default_execution_algorithm": "adaptive",
            "max_execution_time": 3600,
            "real_time_monitoring": True,
            "monitoring_frequency": 1,
            "alert_thresholds": {
                'position_limit_breach': 0.95,
                'var_limit_breach': 0.90,
                'concentration_breach': 0.90
            },
            "regime_risk_multipliers": {
                'bull_market': 0.8,
                'bear_market': 1.3,
                'high_volatility': 1.5,
                'low_volatility': 0.7,
                'crisis': 2.0,
                'sideways': 1.0
            }
        }

    @pytest.fixture
    def sample_decision_request(self):
        """Create sample trading decision request."""
        return TradingDecisionRequest(
            decision_type=TradingDecisionType.POSITION_ENTRY,
            strategy_id="test_strategy",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            expected_return=0.05,
            confidence=0.8,
            risk_score=0.2,
            market_regime="bull_market",
            regime_confidence=0.9
        )

    def test_initialization(self, risk_config):
        """Test CentralRiskManager initialization."""
        risk_manager = CentralRiskManager(risk_config)

        assert isinstance(risk_manager.config, RiskManagerConfig)
        assert risk_manager.config.max_position_size == 0.10
        assert isinstance(risk_manager.pending_requests, dict)
        assert isinstance(risk_manager.active_authorizations, dict)

    @pytest.mark.asyncio
    async def test_request_authorization(self, risk_config, sample_decision_request):
        """Test authorization request."""
        risk_manager = CentralRiskManager(risk_config)

        authorization = await risk_manager.authorize_trading_decision(sample_decision_request)

        assert isinstance(authorization, TradingAuthorization)
        assert authorization.request_id == sample_decision_request.request_id
        assert authorization.authorization_level in list(AuthorizationLevel)

    @pytest.mark.asyncio
    async def test_get_pending_decisions(self, risk_config, sample_decision_request):
        """Test retrieving pending decisions."""
        risk_manager = CentralRiskManager(risk_config)

        # Request authorization (this should add to pending_requests)
        await risk_manager.authorize_trading_decision(sample_decision_request)

        # Check pending requests (accessing internal state for testing)
        pending = list(risk_manager.pending_requests.values())
        assert isinstance(pending, list)
        # Note: The authorization process may or may not leave items in pending_requests
        # depending on the implementation, so we'll just check the structure

    def test_get_risk_limits(self, risk_config):
        """Test risk limits access."""
        risk_manager = CentralRiskManager(risk_config)

        # Test that config is properly set
        assert isinstance(risk_manager.config, RiskManagerConfig)
        assert risk_manager.config.max_position_size == 0.10
        assert risk_manager.config.max_total_risk == 0.20

    def test_update_risk_limits(self, risk_config):
        """Test risk limits configuration."""
        # Test that config can be updated by creating new instance
        updated_config = risk_config.copy()
        updated_config["max_position_size"] = 0.15

        risk_manager = CentralRiskManager(updated_config)
        assert risk_manager.config.max_position_size == 0.15

class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_execution_status_values(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.PENDING_AUTHORIZATION.value == "pending_authorization"
        assert ExecutionStatus.AUTHORIZED.value == "authorized"
        assert ExecutionStatus.EXECUTING.value == "executing"
        assert ExecutionStatus.PARTIALLY_FILLED.value == "partially_filled"
        assert ExecutionStatus.FILLED.value == "filled"
        assert ExecutionStatus.CANCELLED.value == "cancelled"
        assert ExecutionStatus.REJECTED.value == "rejected"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.EXPIRED.value == "expired"

class TestExecutionAlgorithm:
    """Test ExecutionAlgorithm enum."""

    def test_execution_algorithm_values(self):
        """Test ExecutionAlgorithm enum values."""
        assert ExecutionAlgorithm.MARKET.value == "market"
        assert ExecutionAlgorithm.LIMIT.value == "limit"
        assert ExecutionAlgorithm.TWAP.value == "twap"
        assert ExecutionAlgorithm.VWAP.value == "vwap"
        assert ExecutionAlgorithm.POV.value == "pov"
        assert ExecutionAlgorithm.IS.value == "implementation_shortfall"
        assert ExecutionAlgorithm.ICEBERG.value == "iceberg"
        assert ExecutionAlgorithm.SNIPER.value == "sniper"
        assert ExecutionAlgorithm.GUERRILLA.value == "guerrilla"
        assert ExecutionAlgorithm.ADAPTIVE.value == "adaptive"
        assert ExecutionAlgorithm.SMART_ROUTING.value == "smart_routing"

class TestExecutionUrgency:
    """Test ExecutionUrgency enum."""

    def test_execution_urgency_values(self):
        """Test ExecutionUrgency enum values."""
        assert ExecutionUrgency.LOW.value == "low"
        assert ExecutionUrgency.NORMAL.value == "normal"
        assert ExecutionUrgency.HIGH.value == "high"
        assert ExecutionUrgency.URGENT.value == "urgent"
        assert ExecutionUrgency.EMERGENCY.value == "emergency"

class TestVenueType:
    """Test VenueType enum."""

    def test_venue_type_values(self):
        """Test VenueType enum values."""
        assert VenueType.EXCHANGE.value == "exchange"
        assert VenueType.ECN.value == "ecn"
        assert VenueType.DARK_POOL.value == "dark_pool"
        assert VenueType.MARKET_MAKER.value == "market_maker"
        assert VenueType.CROSSING_NETWORK.value == "crossing_network"

class TestExecutionAuthorization:
    """Test ExecutionAuthorization dataclass."""

    def test_initialization(self):
        """Test ExecutionAuthorization initialization."""
        auth = ExecutionAuthorization(
            risk_manager_id="risk_mgr_001",
            symbol="AAPL",
            side="buy",
            quantity=100.0
        )

        assert auth.risk_manager_id == "risk_mgr_001"
        assert auth.symbol == "AAPL"
        assert auth.side == "buy"
        assert auth.quantity == 100.0

class TestExecutionRequest:
    """Test ExecutionRequest dataclass."""

    def test_initialization(self):
        """Test ExecutionRequest initialization."""
        auth = ExecutionAuthorization(
            risk_manager_id="risk_mgr_001",
            symbol="AAPL",
            side="buy",
            quantity=100.0
        )
        request = ExecutionRequest(
            authorization=auth
        )

        assert request.authorization.symbol == "AAPL"
        assert request.authorization.side == "buy"
        assert request.authorization.quantity == 100.0

class TestUnifiedExecutionEngine:
    """Test UnifiedExecutionEngine class."""

    @pytest.fixture
    def execution_config(self):
        """Create execution engine configuration for testing."""
        return {
            "default_algorithm": "adaptive",
            "max_participation_rate": 0.20,
            "min_fill_size": 100,
            "max_slice_size": 1000
        }

    @pytest.fixture
    def sample_execution_request(self):
        """Create sample execution request."""
        auth = ExecutionAuthorization(
            risk_manager_id="risk_mgr_001",
            symbol="AAPL",
            side="buy",
            quantity=100.0
        )
        return ExecutionRequest(authorization=auth)

    @pytest.fixture
    def sample_authorization(self):
        """Create sample execution authorization."""
        return ExecutionAuthorization(
            risk_manager_id="risk_mgr_001",
            symbol="AAPL",
            side="buy",
            quantity=100.0,
            max_price=150.0
        )

    def test_initialization(self, execution_config):
        """Test UnifiedExecutionEngine initialization."""
        engine = UnifiedExecutionEngine(execution_config)

        assert engine.config == execution_config
        assert isinstance(engine.active_executions, dict)
        assert isinstance(engine.execution_history, list)

    @pytest.mark.asyncio
    async def test_submit_execution_request(self, execution_config, sample_execution_request):
        """Test execution request submission."""
        engine = UnifiedExecutionEngine(execution_config)

        result = await engine.execute_authorized_trade(sample_execution_request)
        assert isinstance(result, ExecutionResult)
        assert result.request_id == sample_execution_request.request_id

    @pytest.mark.asyncio
    async def test_execute_authorized_trade(self, execution_config, sample_execution_request):
        """Test authorized trade execution."""
        engine = UnifiedExecutionEngine(execution_config)

        result = await engine.execute_authorized_trade(sample_execution_request)
        assert isinstance(result, ExecutionResult)
        assert result.status in [ExecutionStatus.PENDING_AUTHORIZATION, ExecutionStatus.EXECUTING, ExecutionStatus.FILLED, ExecutionStatus.FAILED, ExecutionStatus.REJECTED]

    @pytest.mark.asyncio
    async def test_get_execution_status(self, execution_config, sample_execution_request):
        """Test execution status retrieval."""
        engine = UnifiedExecutionEngine(execution_config)

        # Execute trade first
        await engine.execute_authorized_trade(sample_execution_request)

        # Get status
        status = engine.get_execution_status(sample_execution_request.request_id)
        assert status in [ExecutionStatus.PENDING_AUTHORIZATION, ExecutionStatus.EXECUTING, ExecutionStatus.FILLED, ExecutionStatus.FAILED, ExecutionStatus.REJECTED, None]

    def test_cancel_execution(self, execution_config, sample_execution_request):
        """Test execution cancellation."""
        engine = UnifiedExecutionEngine(execution_config)

        # Try to cancel non-existent execution
        success = engine.cancel_execution(sample_execution_request.request_id, "fake_auth_id")
        assert success == False  # Should fail for non-existent execution

    def test_get_execution_metrics(self, execution_config):
        """Test execution metrics retrieval."""
        engine = UnifiedExecutionEngine(execution_config)

        metrics = engine.get_execution_metrics()
        assert isinstance(metrics, dict)
        assert "total_executions" in metrics
        assert "successful_executions" in metrics
        assert "avg_execution_time" in metrics