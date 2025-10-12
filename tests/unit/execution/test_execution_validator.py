"""
Test suite for execution_validator.py

Phase 5 Week 2 Day 6: execution_validator.py Testing
Target: 48% → 65%+ coverage
Tests: 35 comprehensive tests
Strategy: Pre-read methodology (4th consecutive day)
"""

import pytest
from datetime import datetime, timedelta

from core_engine.trading.execution.execution_validator import (
    # Enums
    ValidationSeverity,
    ValidationCategory,
    ValidationAction,
    # Dataclasses
    ValidationRule,
    ValidationResult,
    ExecutionContext,
    # Validators
    PreTradeValidator,
    RealTimeValidator,
    PostTradeValidator,
    ExecutionValidator
)


# ============================================================================
# 1. ENUM TESTS (3 tests)
# ============================================================================

class TestEnums:
    """Test validation enums"""
    
    def test_validation_severity_values(self):
        """Test ValidationSeverity enum values"""
        assert ValidationSeverity.INFO.value == "info"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.CRITICAL.value == "critical"
        
        # Test all values exist
        assert len(ValidationSeverity) == 4
    
    def test_validation_category_values(self):
        """Test ValidationCategory enum values"""
        assert ValidationCategory.PRE_TRADE.value == "pre_trade"
        assert ValidationCategory.REAL_TIME.value == "real_time"
        assert ValidationCategory.POST_TRADE.value == "post_trade"
        assert ValidationCategory.COMPLIANCE.value == "compliance"
        assert ValidationCategory.RISK.value == "risk"
        assert ValidationCategory.PERFORMANCE.value == "performance"
        
        # Test all values exist
        assert len(ValidationCategory) == 6
    
    def test_validation_action_values(self):
        """Test ValidationAction enum values"""
        assert ValidationAction.LOG_ONLY.value == "log_only"
        assert ValidationAction.WARN.value == "warn"
        assert ValidationAction.BLOCK.value == "block"
        assert ValidationAction.CANCEL.value == "cancel"
        assert ValidationAction.REDUCE_SIZE.value == "reduce_size"
        assert ValidationAction.ALERT.value == "alert"
        
        # Test all values exist
        assert len(ValidationAction) == 6


# ============================================================================
# 2. DATACLASS TESTS (3 tests)
# ============================================================================

class TestDataClasses:
    """Test validation dataclasses"""
    
    def test_validation_rule_initialization(self):
        """Test ValidationRule with defaults"""
        rule = ValidationRule(
            rule_id="test_rule",
            rule_name="Test Rule",
            description="Test description",
            category=ValidationCategory.PRE_TRADE,
            severity=ValidationSeverity.WARNING,
            action=ValidationAction.WARN
        )
        
        # Check required fields
        assert rule.rule_id == "test_rule"
        assert rule.rule_name == "Test Rule"
        assert rule.description == "Test description"
        assert rule.category == ValidationCategory.PRE_TRADE
        assert rule.severity == ValidationSeverity.WARNING
        assert rule.action == ValidationAction.WARN
        
        # Check defaults
        assert rule.enabled is True
        assert rule.priority == 1  # Default is 1, not 0
        assert rule.numeric_threshold is None
        assert rule.percentage_threshold is None
        assert rule.time_threshold is None
        assert rule.symbols is None
        assert rule.strategies is None
        assert rule.venues is None
        assert rule.market_hours_only is False
        assert rule.business_days_only is False
        assert rule.custom_validator is None
        
        # Check auto-generated fields
        assert isinstance(rule.created_at, datetime)
        assert isinstance(rule.last_modified, datetime)
    
    def test_validation_result_with_auto_fields(self):
        """Test ValidationResult with auto-generated fields"""
        result = ValidationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            category=ValidationCategory.PRE_TRADE,
            severity=ValidationSeverity.ERROR,
            action=ValidationAction.BLOCK,
            passed=False,
            message="Validation failed",
            execution_id="exec123",
            order_id="order456",
            symbol="AAPL"
        )
        
        # Check required fields
        assert result.rule_id == "test_rule"
        assert result.rule_name == "Test Rule"
        assert result.category == ValidationCategory.PRE_TRADE
        assert result.severity == ValidationSeverity.ERROR
        assert result.action == ValidationAction.BLOCK
        assert result.passed is False
        assert result.message == "Validation failed"
        assert result.execution_id == "exec123"
        assert result.order_id == "order456"
        assert result.symbol == "AAPL"
        
        # Check defaults
        assert result.details == {}
        assert result.action_taken is None
        assert result.action_details == {}
        
        # Check auto-generated
        assert isinstance(result.check_time, datetime)
    
    def test_execution_context_comprehensive_fields(self):
        """Test ExecutionContext with all fields"""
        now = datetime.now()
        recent_execs = [
            {'symbol': 'AAPL', 'side': 'BUY', 'quantity': 100}
        ]
        
        context = ExecutionContext(
            execution_id="exec123",
            order_id="order456",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0,
            order_type="LIMIT",
            time_in_force="GTC",
            venue="NASDAQ",
            strategy_id="strat1",
            portfolio_id="port1",
            current_price=149.5,
            bid_price=149.4,
            ask_price=149.6,
            spread=0.2,
            volatility=0.25,
            current_position=5000,
            notional_exposure=750000,
            portfolio_value=10000000,
            submission_time=now,
            expected_execution_time=now + timedelta(minutes=5),
            recent_executions=recent_execs
        )
        
        # Core fields
        assert context.execution_id == "exec123"
        assert context.order_id == "order456"
        assert context.symbol == "AAPL"
        assert context.side == "BUY"
        assert context.quantity == 1000
        assert context.price == 150.0
        
        # Order details
        assert context.order_type == "LIMIT"
        assert context.time_in_force == "GTC"
        assert context.venue == "NASDAQ"
        
        # Strategy context
        assert context.strategy_id == "strat1"
        assert context.portfolio_id == "port1"
        
        # Market context
        assert context.current_price == 149.5
        assert context.bid_price == 149.4
        assert context.ask_price == 149.6
        assert context.spread == 0.2
        assert context.volatility == 0.25
        
        # Risk context
        assert context.current_position == 5000
        assert context.notional_exposure == 750000
        assert context.portfolio_value == 10000000
        
        # Timing
        assert context.submission_time == now
        assert context.expected_execution_time == now + timedelta(minutes=5)
        
        # History
        assert len(context.recent_executions) == 1
        assert context.recent_executions[0]['symbol'] == 'AAPL'


# ============================================================================
# 3. PRE-TRADE VALIDATOR TESTS (8 tests)
# ============================================================================

class TestPreTradeValidator:
    """Test pre-trade validation"""
    
    def test_default_rules_loaded(self):
        """Test default pre-trade rules are loaded"""
        validator = PreTradeValidator()
        
        # Check expected rules exist
        expected_rules = [
            'order_size_limit',
            'notional_limit',
            'price_reasonableness',
            'market_hours',
            'position_concentration',
            'duplicate_order'
        ]
        
        for rule_id in expected_rules:
            assert rule_id in validator.rules
            rule = validator.rules[rule_id]
            assert rule.category == ValidationCategory.PRE_TRADE
            assert rule.enabled is True
    
    def test_order_size_validation_pass(self):
        """Test order size validation passes"""
        validator = PreTradeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100000,  # Below 1M limit
            price=150.0
        )
        
        results = validator.validate_execution(context)
        
        # Find order_size_limit result
        size_result = next(r for r in results if r.rule_id == 'order_size_limit')
        assert size_result.passed is True
    
    def test_order_size_validation_fail(self):
        """Test order size validation fails for large orders"""
        validator = PreTradeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=2000000,  # Above 1M limit
            price=150.0
        )
        
        results = validator.validate_execution(context)
        
        # Find order_size_limit result
        size_result = next(r for r in results if r.rule_id == 'order_size_limit')
        assert size_result.passed is False
        assert size_result.severity == ValidationSeverity.ERROR
        assert size_result.action == ValidationAction.BLOCK
        assert 'exceeds limit' in size_result.message
        assert size_result.details['order_quantity'] == 2000000
        assert size_result.details['limit'] == 1000000
        assert size_result.details['excess'] == 1000000
    
    def test_notional_limit_validation(self):
        """Test notional amount validation"""
        validator = PreTradeValidator()
        
        # Large notional (100,000 shares * $1,500 = $150M > $100M limit)
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100000,
            price=1500.0
        )
        
        results = validator.validate_execution(context)
        
        notional_result = next(r for r in results if r.rule_id == 'notional_limit')
        assert notional_result.passed is False
        assert notional_result.severity == ValidationSeverity.ERROR
        assert 'Notional' in notional_result.message
        assert notional_result.details['notional'] == 150000000
        assert notional_result.details['limit'] == 100000000
    
    def test_price_reasonableness_validation(self):
        """Test price reasonableness check"""
        validator = PreTradeValidator()
        
        # Order price 10% above market (>5% threshold)
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=165.0,  # 10% above market
            current_price=150.0
        )
        
        results = validator.validate_execution(context)
        
        price_result = next(r for r in results if r.rule_id == 'price_reasonableness')
        assert price_result.passed is False
        assert price_result.severity == ValidationSeverity.WARNING
        assert 'deviates' in price_result.message
        assert price_result.details['order_price'] == 165.0
        assert price_result.details['market_price'] == 150.0
        assert price_result.details['deviation'] == pytest.approx(0.1, abs=0.01)
    
    def test_position_concentration_validation(self):
        """Test position concentration check"""
        validator = PreTradeValidator()
        
        # Position would be 15% of portfolio (>10% limit)
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=10000,
            price=150.0,
            current_position=0,
            portfolio_value=10000000  # $10M portfolio
        )
        
        results = validator.validate_execution(context)
        
        conc_result = next(r for r in results if r.rule_id == 'position_concentration')
        assert conc_result.passed is False
        assert conc_result.severity == ValidationSeverity.ERROR
        assert conc_result.action == ValidationAction.REDUCE_SIZE
        assert 'concentration' in conc_result.message
        assert conc_result.details['concentration'] == pytest.approx(0.15, abs=0.01)
    
    def test_duplicate_order_detection(self):
        """Test duplicate order detection"""
        validator = PreTradeValidator()
        
        now = datetime.now()
        recent_time = now - timedelta(seconds=10)
        
        # Recent similar order
        context = ExecutionContext(
            execution_id="exec2",
            order_id="order2",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0,
            submission_time=now,
            recent_executions=[
                {
                    'symbol': 'AAPL',
                    'side': 'BUY',
                    'quantity': 1050,  # Within 10% of 1000
                    'submission_time': recent_time
                }
            ]
        )
        
        results = validator.validate_execution(context)
        
        dup_result = next(r for r in results if r.rule_id == 'duplicate_order')
        assert dup_result.passed is False
        assert dup_result.severity == ValidationSeverity.WARNING
        assert 'duplicate' in dup_result.message
        assert dup_result.details['time_difference'] == 10.0
    
    def test_rule_filtering_by_symbol(self):
        """Test rule filtering by symbol constraint"""
        validator = PreTradeValidator()
        
        # Add rule specific to MSFT
        msft_rule = ValidationRule(
            rule_id="msft_only",
            rule_name="MSFT Only Rule",
            description="Test",
            category=ValidationCategory.PRE_TRADE,
            severity=ValidationSeverity.INFO,
            action=ValidationAction.LOG_ONLY,
            symbols=['MSFT']
        )
        validator.rules['msft_only'] = msft_rule
        
        # Test with AAPL - rule should not apply
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        results = validator.validate_execution(context)
        
        # msft_only rule should not be in results
        msft_results = [r for r in results if r.rule_id == 'msft_only']
        assert len(msft_results) == 0


# ============================================================================
# 4. REAL-TIME VALIDATOR TESTS (5 tests)
# ============================================================================

class TestRealTimeValidator:
    """Test real-time validation"""
    
    def test_default_realtime_rules_loaded(self):
        """Test default real-time rules are loaded"""
        validator = RealTimeValidator()
        
        expected_rules = [
            'execution_speed',
            'slippage_monitor',
            'fill_rate_monitor',
            'market_impact_monitor'
        ]
        
        for rule_id in expected_rules:
            assert rule_id in validator.rules
            rule = validator.rules[rule_id]
            assert rule.category == ValidationCategory.REAL_TIME
    
    def test_execution_speed_validation(self):
        """Test execution speed monitoring"""
        validator = RealTimeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        # Slow execution (15 seconds > 10 second threshold)
        metrics = {
            'execution_time_seconds': 15.0
        }
        
        results = validator.validate_ongoing_execution(context, metrics)
        
        speed_result = next(r for r in results if r.rule_id == 'execution_speed')
        assert speed_result.passed is False
        assert speed_result.severity == ValidationSeverity.WARNING
        assert speed_result.action == ValidationAction.ALERT
        assert 'Slow execution' in speed_result.message
        assert speed_result.details['execution_time'] == 15.0
    
    def test_slippage_monitoring(self):
        """Test slippage validation"""
        validator = RealTimeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        # High slippage (2% > 1% threshold)
        metrics = {
            'slippage': 0.02
        }
        
        results = validator.validate_ongoing_execution(context, metrics)
        
        slip_result = next(r for r in results if r.rule_id == 'slippage_monitor')
        assert slip_result.passed is False
        assert 'High slippage' in slip_result.message
        assert slip_result.details['slippage'] == 0.02
        assert slip_result.details['threshold'] == 0.01
    
    def test_fill_rate_monitoring(self):
        """Test fill rate validation"""
        validator = RealTimeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        # Low fill rate (40% < 50% threshold)
        metrics = {
            'fill_rate': 0.40
        }
        
        results = validator.validate_ongoing_execution(context, metrics)
        
        fill_result = next(r for r in results if r.rule_id == 'fill_rate_monitor')
        assert fill_result.passed is False
        assert fill_result.severity == ValidationSeverity.INFO
        assert fill_result.action == ValidationAction.LOG_ONLY
        assert 'Low fill rate' in fill_result.message
    
    def test_market_impact_monitoring(self):
        """Test market impact validation"""
        validator = RealTimeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        # High market impact (1% > 0.5% threshold)
        metrics = {
            'market_impact': 0.01
        }
        
        results = validator.validate_ongoing_execution(context, metrics)
        
        impact_result = next(r for r in results if r.rule_id == 'market_impact_monitor')
        assert impact_result.passed is False
        assert 'High market impact' in impact_result.message
        assert impact_result.details['market_impact'] == 0.01


# ============================================================================
# 5. POST-TRADE VALIDATOR TESTS (5 tests)
# ============================================================================

class TestPostTradeValidator:
    """Test post-trade validation"""
    
    def test_default_post_trade_rules_loaded(self):
        """Test default post-trade rules are loaded"""
        validator = PostTradeValidator()
        
        expected_rules = [
            'best_execution',
            'transaction_cost_analysis',
            'venue_performance',
            'regulatory_reporting'
        ]
        
        for rule_id in expected_rules:
            assert rule_id in validator.rules
    
    def test_best_execution_analysis(self):
        """Test best execution analysis"""
        validator = PostTradeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0,
            current_price=150.0
        )
        
        exec_results = {
            'avg_execution_price': 150.15
        }
        
        results = validator.validate_completed_execution(context, exec_results)
        
        best_exec = next(r for r in results if r.rule_id == 'best_execution')
        assert best_exec.passed is True
        assert 'Best execution analysis' in best_exec.message
        assert 'execution_quality' in best_exec.details
        assert 'assessment' in best_exec.details
    
    def test_transaction_cost_analysis(self):
        """Test transaction cost calculation"""
        validator = PostTradeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0,
            current_price=150.0
        )
        
        exec_results = {
            'total_slippage': 0.001,
            'market_impact': 0.0005,
            'commission': 10.0
        }
        
        results = validator.validate_completed_execution(context, exec_results)
        
        cost_analysis = next(r for r in results if r.rule_id == 'transaction_cost_analysis')
        assert cost_analysis.passed is True
        assert 'Transaction cost analysis' in cost_analysis.message
        assert 'total_cost_bps' in cost_analysis.details
        assert 'slippage_bps' in cost_analysis.details
        assert 'market_impact_bps' in cost_analysis.details
    
    def test_venue_performance_analysis(self):
        """Test venue performance comparison"""
        validator = PostTradeValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        exec_results = {
            'venue_breakdown': {
                'NASDAQ': {'avg_slippage': 0.0005, 'fill_count': 5},
                'NYSE': {'avg_slippage': 0.0010, 'fill_count': 3}
            }
        }
        
        results = validator.validate_completed_execution(context, exec_results)
        
        venue_perf = next(r for r in results if r.rule_id == 'venue_performance')
        assert venue_perf.passed is True
        assert 'Venue performance' in venue_perf.message
        assert venue_perf.details['venues_used'] == ['NASDAQ', 'NYSE']
        assert venue_perf.details['best_venue'] == 'NASDAQ'
        assert venue_perf.details['worst_venue'] == 'NYSE'
    
    def test_regulatory_reporting_check(self):
        """Test regulatory reporting requirements"""
        validator = PostTradeValidator()
        
        # Large trade requiring reporting
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100000,
            price=150.0,
            current_price=150.0
        )
        
        exec_results = {}
        
        results = validator.validate_completed_execution(context, exec_results)
        
        reporting = next(r for r in results if r.rule_id == 'regulatory_reporting')
        assert reporting.passed is True
        assert reporting.details['notional'] == 15000000
        assert reporting.details['requires_reporting'] is True
        assert reporting.details['reporting_type'] == 'large_trade'


# ============================================================================
# 6. EXECUTION VALIDATOR CORE TESTS (6 tests)
# ============================================================================

class TestExecutionValidatorCore:
    """Test main ExecutionValidator class"""
    
    def test_initialization(self):
        """Test ExecutionValidator initialization"""
        validator = ExecutionValidator()
        
        # Check sub-validators created
        assert isinstance(validator.pre_trade_validator, PreTradeValidator)
        assert isinstance(validator.realtime_validator, RealTimeValidator)
        assert isinstance(validator.post_trade_validator, PostTradeValidator)
        
        # Check configuration
        assert validator.block_on_critical is True
        assert validator.alert_on_warnings is True
        
        # Check internal state
        assert validator._validation_history == []
        assert isinstance(validator._failed_validations, dict)
        assert validator._validation_callbacks == []
    
    def test_pre_trade_validation_with_blocking(self):
        """Test pre-trade validation blocks on errors"""
        validator = ExecutionValidator()
        
        # Order that violates size limit (ERROR severity)
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=2000000,  # > 1M limit
            price=150.0
        )
        
        should_proceed, results = validator.validate_pre_trade(context)
        
        # Should be blocked
        assert should_proceed is False
        assert len(results) > 0
        
        # Check history stored
        assert len(validator._validation_history) > 0
        
        # Check failed validations stored
        assert len(validator._failed_validations) > 0
    
    def test_real_time_validation(self):
        """Test real-time validation"""
        validator = ExecutionValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0
        )
        
        metrics = {
            'execution_time_seconds': 5.0,
            'slippage': 0.005,
            'fill_rate': 0.95,
            'market_impact': 0.002
        }
        
        results = validator.validate_real_time(context, metrics)
        
        # Should get results
        assert len(results) > 0
        
        # Check history updated
        assert len(validator._validation_history) > 0
    
    def test_post_trade_validation(self):
        """Test post-trade validation"""
        validator = ExecutionValidator()
        
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=1000,
            price=150.0,
            current_price=150.0
        )
        
        exec_results = {
            'avg_execution_price': 150.10,
            'total_slippage': 0.001,
            'market_impact': 0.0005,
            'commission': 10.0
        }
        
        results = validator.validate_post_trade(context, exec_results)
        
        # Should get results
        assert len(results) > 0
        
        # Check history updated
        assert len(validator._validation_history) > 0
    
    def test_custom_rule_management(self):
        """Test adding and removing custom rules"""
        validator = ExecutionValidator()
        
        # Add custom rule
        custom_rule = ValidationRule(
            rule_id="custom_test",
            rule_name="Custom Test Rule",
            description="Test custom rule",
            category=ValidationCategory.PRE_TRADE,
            severity=ValidationSeverity.INFO,
            action=ValidationAction.LOG_ONLY
        )
        
        validator.add_custom_rule(custom_rule)
        
        # Verify added
        assert 'custom_test' in validator.pre_trade_validator.rules
        
        # Remove rule
        removed = validator.remove_rule('custom_test')
        
        # Verify removed
        assert removed is True
        assert 'custom_test' not in validator.pre_trade_validator.rules
    
    def test_validation_callbacks(self):
        """Test validation callback system"""
        validator = ExecutionValidator()
        
        # Track callback invocations
        callback_results = []
        
        def test_callback(result: ValidationResult):
            callback_results.append(result)
        
        validator.add_validation_callback(test_callback)
        
        # Run validation
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        validator.validate_pre_trade(context)
        
        # Callback should have been invoked
        assert len(callback_results) > 0
        assert all(isinstance(r, ValidationResult) for r in callback_results)


# ============================================================================
# 7. HISTORY & REPORTING TESTS (4 tests)
# ============================================================================

class TestHistoryAndReporting:
    """Test validation history and reporting"""
    
    def test_validation_history_filtering(self):
        """Test validation history with filters"""
        validator = ExecutionValidator()
        
        # Create multiple validations
        context1 = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        context2 = ExecutionContext(
            execution_id="exec2",
            order_id="order2",
            symbol="MSFT",
            side="SELL",
            quantity=200,
            price=250.0
        )
        
        validator.validate_pre_trade(context1)
        validator.validate_pre_trade(context2)
        
        # Test filtering by execution_id
        exec1_history = validator.get_validation_history(execution_id="exec1")
        assert all(r.execution_id == "exec1" for r in exec1_history)
        
        # Test filtering by rule_id
        rule_history = validator.get_validation_history(rule_id="order_size_limit")
        assert all(r.rule_id == "order_size_limit" for r in rule_history)
        
        # Test filtering by category
        pretrade_history = validator.get_validation_history(
            category=ValidationCategory.PRE_TRADE
        )
        assert all(r.category == ValidationCategory.PRE_TRADE for r in pretrade_history)
    
    def test_validation_summary_statistics(self):
        """Test validation summary generation"""
        validator = ExecutionValidator()
        
        # Run some validations
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        validator.validate_pre_trade(context)
        
        # Get summary
        summary = validator.get_validation_summary()
        
        # Check structure
        assert 'total_validations' in summary
        assert 'failed_validations' in summary
        assert 'success_rate' in summary
        assert 'category_breakdown' in summary
        assert 'severity_breakdown' in summary
        assert 'most_failed_rules' in summary
        
        # Check values
        assert summary['total_validations'] > 0
        assert 0 <= summary['success_rate'] <= 1
    
    def test_validation_report_generation(self):
        """Test comprehensive report generation"""
        validator = ExecutionValidator()
        
        # Create validation history
        context = ExecutionContext(
            execution_id="exec1",
            order_id="order1",
            symbol="AAPL",
            side="BUY",
            quantity=100,
            price=150.0
        )
        
        validator.validate_pre_trade(context)
        
        # Generate report
        report = validator.generate_validation_report()
        
        # Check structure
        assert 'report_period' in report
        assert 'total_validations' in report
        assert 'failed_validations' in report
        assert 'overall_success_rate' in report
        assert 'category_breakdown' in report
        assert 'severity_breakdown' in report
        assert 'daily_breakdown' in report
        assert 'most_failed_rules' in report
        assert 'validation_trend' in report
        
        # Check trend structure
        trend = report['validation_trend']
        assert 'trend' in trend
        assert 'description' in trend
    
    def test_validation_trend_calculation(self):
        """Test validation trend calculation"""
        validator = ExecutionValidator()
        
        # Create history with improving trend
        # First half: some failures
        for i in range(5):
            context = ExecutionContext(
                execution_id=f"exec{i}",
                order_id=f"order{i}",
                symbol="AAPL",
                side="BUY",
                quantity=2000000 if i < 2 else 100,  # First 2 fail size check
                price=150.0
            )
            validator.validate_pre_trade(context)
        
        # Generate report
        report = validator.generate_validation_report()
        
        # Check trend
        trend = report['validation_trend']
        assert 'trend' in trend
        assert 'description' in trend
        assert trend['description'] in ['Improving', 'Declining', 'Stable']


# ============================================================================
# 8. THREAD SAFETY TEST (1 test)
# ============================================================================

class TestThreadSafety:
    """Test thread-safe operations"""
    
    def test_concurrent_validation_calls(self):
        """Test concurrent validation calls are thread-safe"""
        import threading
        
        validator = ExecutionValidator()
        results = []
        errors = []
        
        def run_validation(exec_id: str):
            try:
                context = ExecutionContext(
                    execution_id=exec_id,
                    order_id=f"order_{exec_id}",
                    symbol="AAPL",
                    side="BUY",
                    quantity=100,
                    price=150.0
                )
                
                should_proceed, validation_results = validator.validate_pre_trade(context)
                results.append((exec_id, should_proceed))
            except Exception as e:
                errors.append((exec_id, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=run_validation, args=(f"exec{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 10
        assert len(errors) == 0
        
        # Check history integrity
        assert len(validator._validation_history) > 0
        
        # Check all executions recorded
        exec_ids = set(r.execution_id for r in validator._validation_history)
        assert len(exec_ids) == 10
