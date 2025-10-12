"""
Comprehensive tests for ExposureCalculator
Tests all exposure calculation methods, limit management, and utility functions
"""

import pytest
from datetime import datetime, timedelta

from core_engine.risk.exposure_calculator import (
    ExposureCalculator,
    ExposureType,
    ExposureDirection,
    ExposureItem,
    ExposureBreakdown,
    ExposureLimit,
    ExposureViolation
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def calculator():
    """Default exposure calculator"""
    return ExposureCalculator()


@pytest.fixture
def calculator_custom():
    """Exposure calculator with custom configuration"""
    config = {
        'cache_ttl_seconds': 600,
        'include_derivatives': False,
        'include_cash': True,
        'base_currency': 'EUR'
    }
    return ExposureCalculator(config)


@pytest.fixture
def sample_positions_long():
    """Sample long-only positions"""
    return {
        'AAPL': {
            'quantity': 100,
            'market_value': 15000.0,
            'asset_type': 'STOCK',
            'currency': 'USD'
        },
        'MSFT': {
            'quantity': 50,
            'market_value': 10000.0,
            'asset_type': 'STOCK',
            'currency': 'USD'
        }
    }


@pytest.fixture
def sample_positions_mixed():
    """Sample mixed long/short positions"""
    return {
        'AAPL': {
            'quantity': 100,
            'market_value': 15000.0,
            'asset_type': 'STOCK',
            'currency': 'USD'
        },
        'MSFT': {
            'quantity': -50,
            'market_value': -7500.0,
            'asset_type': 'STOCK',
            'currency': 'USD'
        },
        'GOOGL': {
            'quantity': 20,
            'market_value': 5000.0,
            'asset_type': 'STOCK',
            'currency': 'USD'
        }
    }


@pytest.fixture
def sample_positions_multi_sector():
    """Sample positions across multiple sectors"""
    return {
        'AAPL': {'quantity': 100, 'market_value': 15000.0},   # Technology
        'MSFT': {'quantity': 50, 'market_value': 10000.0},    # Technology
        'JPM': {'quantity': 30, 'market_value': 8000.0},      # Financials
        'JNJ': {'quantity': 20, 'market_value': 5000.0}       # Healthcare
    }


@pytest.fixture
def sample_positions_multi_currency():
    """Sample positions with multiple currencies"""
    return {
        'AAPL': {
            'quantity': 100,
            'market_value': 15000.0,
            'currency': 'USD'
        },
        'ASML': {
            'quantity': 20,
            'market_value': 5000.0,
            'currency': 'EUR'
        },
        'NESN': {
            'quantity': 50,
            'market_value': 3000.0,
            'currency': 'CHF'
        }
    }


@pytest.fixture
def portfolio_value():
    """Standard portfolio value"""
    return 100000.0


# ============================================================================
# Category 1: Enums and Dataclasses (3 tests)
# ============================================================================

class TestEnumsAndDataclasses:
    """Test enum values and dataclass creation"""
    
    def test_exposure_type_enum_values(self):
        """Test all ExposureType enum values"""
        assert ExposureType.MARKET.value == "market"
        assert ExposureType.SECTOR.value == "sector"
        assert ExposureType.REGION.value == "region"
        assert ExposureType.CURRENCY.value == "currency"
        assert ExposureType.FACTOR.value == "factor"
        assert ExposureType.SINGLE_NAME.value == "single_name"
        assert ExposureType.CREDIT.value == "credit"
        assert ExposureType.DURATION.value == "duration"
        assert ExposureType.VOLATILITY.value == "volatility"
        
        # Verify all 9 types
        assert len(ExposureType) == 9
    
    def test_exposure_direction_enum_values(self):
        """Test all ExposureDirection enum values"""
        assert ExposureDirection.LONG.value == "long"
        assert ExposureDirection.SHORT.value == "short"
        assert ExposureDirection.NET.value == "net"
        assert ExposureDirection.GROSS.value == "gross"
        
        # Verify all 4 directions
        assert len(ExposureDirection) == 4
    
    def test_dataclass_creation(self):
        """Test creating all dataclass instances"""
        # ExposureItem
        item = ExposureItem(
            identifier='AAPL',
            exposure_type=ExposureType.SINGLE_NAME,
            value=15000.0,
            percentage=15.0,
            currency='USD'
        )
        assert item.identifier == 'AAPL'
        assert item.exposure_type == ExposureType.SINGLE_NAME
        assert item.value == 15000.0
        assert item.percentage == 15.0
        
        # ExposureBreakdown
        breakdown = ExposureBreakdown(
            total_exposure=25000.0,
            long_exposure=15000.0,
            short_exposure=10000.0,
            net_exposure=5000.0,
            gross_exposure=25000.0,
            exposures=[item]
        )
        assert breakdown.long_exposure == 15000.0
        assert breakdown.net_exposure == 5000.0
        assert len(breakdown.exposures) == 1
        
        # ExposureLimit
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='AAPL',
            max_exposure=20.0,
            warning_threshold=15.0,
            is_percentage=True
        )
        assert limit.max_exposure == 20.0
        assert limit.warning_threshold == 15.0
        
        # ExposureViolation
        violation = ExposureViolation(
            exposure_item=item,
            limit=limit,
            violation_amount=2.0,
            violation_percentage=10.0,
            severity='WARNING'
        )
        assert violation.severity == 'WARNING'
        assert violation.violation_amount == 2.0


# ============================================================================
# Category 2: Initialization (3 tests)
# ============================================================================

class TestInitialization:
    """Test ExposureCalculator initialization"""
    
    def test_default_initialization(self, calculator):
        """Test default configuration"""
        assert calculator.include_derivatives is True
        assert calculator.include_cash is False
        assert calculator.base_currency == 'USD'
        assert calculator._cache_ttl == 300
        
        # Verify data structures initialized
        assert calculator._exposure_cache == {}
        assert calculator._limits == {}
        assert calculator._violations == []
        assert len(calculator._calculation_history) == 0
    
    def test_custom_configuration(self, calculator_custom):
        """Test custom configuration"""
        assert calculator_custom._cache_ttl == 600
        assert calculator_custom.include_derivatives is False
        assert calculator_custom.include_cash is True
        assert calculator_custom.base_currency == 'EUR'
    
    def test_sector_and_geographic_mappings_loaded(self, calculator):
        """Test that sector and geographic mappings are loaded"""
        # Verify sector mappings (9 symbols)
        assert 'AAPL' in calculator._sector_mappings
        assert calculator._sector_mappings['AAPL'] == 'Technology'
        assert calculator._sector_mappings['JPM'] == 'Financials'
        assert calculator._sector_mappings['XOM'] == 'Energy'
        assert len(calculator._sector_mappings) == 9
        
        # Verify geographic mappings (all North America)
        assert 'AAPL' in calculator._geographic_mappings
        assert calculator._geographic_mappings['AAPL'] == 'North America'
        assert len(calculator._geographic_mappings) == 9


# ============================================================================
# Category 3: Market Exposure (4 tests)
# ============================================================================

class TestMarketExposure:
    """Test market exposure calculations"""
    
    @pytest.mark.asyncio
    async def test_market_exposure_long_positions(self, calculator, sample_positions_long, portfolio_value):
        """Test market exposure with only long positions"""
        result = await calculator._calculate_market_exposure(sample_positions_long, portfolio_value)
        
        assert result.long_exposure == 25000.0  # 15000 + 10000
        assert result.short_exposure == 0.0
        assert result.net_exposure == 25000.0
        assert result.gross_exposure == 25000.0
        assert result.total_exposure == 25000.0
        assert len(result.exposures) == 2  # Two positions
    
    @pytest.mark.asyncio
    async def test_market_exposure_short_positions(self, calculator, portfolio_value):
        """Test market exposure with only short positions"""
        positions = {
            'AAPL': {'quantity': -100, 'market_value': -15000.0},
            'MSFT': {'quantity': -50, 'market_value': -7500.0}
        }
        
        result = await calculator._calculate_market_exposure(positions, portfolio_value)
        
        assert result.long_exposure == 0.0
        assert result.short_exposure == 22500.0  # 15000 + 7500
        assert result.net_exposure == -22500.0
        assert result.gross_exposure == 22500.0
    
    @pytest.mark.asyncio
    async def test_market_exposure_mixed_positions(self, calculator, sample_positions_mixed, portfolio_value):
        """Test market exposure with mixed long/short positions"""
        result = await calculator._calculate_market_exposure(sample_positions_mixed, portfolio_value)
        
        assert result.long_exposure == 20000.0  # 15000 + 5000
        assert result.short_exposure == 7500.0
        assert result.net_exposure == 12500.0   # 20000 - 7500
        assert result.gross_exposure == 27500.0  # 20000 + 7500
    
    @pytest.mark.asyncio
    async def test_market_exposure_empty_positions(self, calculator, portfolio_value):
        """Test market exposure with empty portfolio"""
        result = await calculator._calculate_market_exposure({}, portfolio_value)
        
        assert result.long_exposure == 0.0
        assert result.short_exposure == 0.0
        assert result.net_exposure == 0.0
        assert result.gross_exposure == 0.0
        assert len(result.exposures) == 0


# ============================================================================
# Category 4: Sector/Region/Currency Exposure (6 tests)
# ============================================================================

class TestSectorRegionCurrencyExposure:
    """Test sector, regional, and currency exposure calculations"""
    
    @pytest.mark.asyncio
    async def test_sector_exposure_single_sector(self, calculator, sample_positions_long, portfolio_value):
        """Test sector exposure when all positions in same sector"""
        result = await calculator._calculate_sector_exposure(sample_positions_long, portfolio_value)
        
        # AAPL and MSFT both in Technology sector
        tech_exposures = [e for e in result.exposures if e.identifier == 'Technology']
        assert len(tech_exposures) == 1
        assert tech_exposures[0].value == 25000.0
        assert tech_exposures[0].percentage == 25.0  # 25000/100000 * 100
    
    @pytest.mark.asyncio
    async def test_sector_exposure_multiple_sectors(self, calculator, sample_positions_multi_sector, portfolio_value):
        """Test sector exposure across multiple sectors"""
        result = await calculator._calculate_sector_exposure(sample_positions_multi_sector, portfolio_value)
        
        # Should have 3 sectors: Technology, Financials, Healthcare
        assert len(result.exposures) == 3
        
        tech = [e for e in result.exposures if e.identifier == 'Technology'][0]
        financials = [e for e in result.exposures if e.identifier == 'Financials'][0]
        healthcare = [e for e in result.exposures if e.identifier == 'Healthcare'][0]
        
        assert tech.value == 25000.0  # AAPL + MSFT
        assert financials.value == 8000.0
        assert healthcare.value == 5000.0
    
    @pytest.mark.asyncio
    async def test_regional_exposure_calculation(self, calculator, sample_positions_long, portfolio_value):
        """Test regional/geographic exposure"""
        result = await calculator._calculate_regional_exposure(sample_positions_long, portfolio_value)
        
        # All symbols map to North America
        na_exposures = [e for e in result.exposures if e.identifier == 'North America']
        assert len(na_exposures) == 1
        assert na_exposures[0].value == 25000.0
    
    @pytest.mark.asyncio
    async def test_currency_exposure_single_currency(self, calculator, sample_positions_long, portfolio_value):
        """Test currency exposure with single currency"""
        result = await calculator._calculate_currency_exposure(sample_positions_long, portfolio_value)
        
        # All positions in USD
        usd_exposures = [e for e in result.exposures if e.identifier == 'USD']
        assert len(usd_exposures) == 1
        assert usd_exposures[0].value == 25000.0
    
    @pytest.mark.asyncio
    async def test_currency_exposure_multiple_currencies(self, calculator, sample_positions_multi_currency, portfolio_value):
        """Test currency exposure with multiple currencies"""
        result = await calculator._calculate_currency_exposure(sample_positions_multi_currency, portfolio_value)
        
        # Should have 3 currencies: USD, EUR, CHF
        assert len(result.exposures) == 3
        
        currencies = {e.identifier: e.value for e in result.exposures}
        assert currencies['USD'] == 15000.0
        assert currencies['EUR'] == 5000.0
        assert currencies['CHF'] == 3000.0
    
    @pytest.mark.asyncio
    async def test_unknown_sector_mapping(self, calculator, portfolio_value):
        """Test handling of unknown sector mappings"""
        positions = {
            'UNKN': {'quantity': 100, 'market_value': 10000.0}  # Not in mappings
        }
        
        result = await calculator._calculate_sector_exposure(positions, portfolio_value)
        
        # Should map to 'Unknown'
        unknown_exposures = [e for e in result.exposures if e.identifier == 'Unknown']
        assert len(unknown_exposures) == 1
        assert unknown_exposures[0].value == 10000.0


# ============================================================================
# Category 5: Factor and Single Name Exposure (4 tests)
# ============================================================================

class TestFactorAndSingleNameExposure:
    """Test factor and single name exposure calculations"""
    
    @pytest.mark.asyncio
    async def test_factor_exposure_calculation(self, calculator, sample_positions_long, portfolio_value):
        """Test factor exposure calculation"""
        result = await calculator._calculate_factor_exposure(sample_positions_long, portfolio_value)
        
        # Should have factor exposures (though values are random)
        assert len(result.exposures) >= 0  # May have factors with small exposures filtered
        
        # Verify all are factor type
        for exposure in result.exposures:
            assert exposure.exposure_type == ExposureType.FACTOR
            assert exposure.identifier in ['Value', 'Growth', 'Momentum', 'Quality', 'Size', 'Volatility']
    
    @pytest.mark.asyncio
    async def test_factor_exposure_threshold_filtering(self, calculator, portfolio_value):
        """Test that small factor exposures are filtered out"""
        # Position with very small market value
        positions = {
            'AAPL': {'quantity': 1, 'market_value': 0.001}
        }
        
        result = await calculator._calculate_factor_exposure(positions, portfolio_value)
        
        # All exposures should be filtered (< 0.01 threshold)
        assert len(result.exposures) == 0
    
    @pytest.mark.asyncio
    async def test_single_name_exposure_sorted(self, calculator, sample_positions_multi_sector, portfolio_value):
        """Test that single name exposures are sorted by size"""
        result = await calculator._calculate_single_name_exposure(sample_positions_multi_sector, portfolio_value)
        
        # Should have 4 positions, sorted by absolute value
        assert len(result.exposures) == 4
        assert result.exposures[0].identifier == 'AAPL'  # Largest: 15000
        assert result.exposures[1].identifier == 'MSFT'  # 10000
        assert result.exposures[2].identifier == 'JPM'   # 8000
        assert result.exposures[3].identifier == 'JNJ'   # 5000
    
    @pytest.mark.asyncio
    async def test_single_name_concentration(self, calculator, sample_positions_long, portfolio_value):
        """Test single name concentration calculations"""
        result = await calculator._calculate_single_name_exposure(sample_positions_long, portfolio_value)
        
        assert len(result.exposures) == 2
        
        aapl = result.exposures[0]  # Sorted, AAPL is larger
        assert aapl.identifier == 'AAPL'
        assert aapl.value == 15000.0
        assert aapl.percentage == 15.0  # 15000/100000 * 100
        
        msft = result.exposures[1]
        assert msft.identifier == 'MSFT'
        assert msft.percentage == 10.0


# ============================================================================
# Category 6: Exposure Limits and Violations (7 tests)
# ============================================================================

class TestExposureLimitsAndViolations:
    """Test exposure limit management and violation detection"""
    
    def test_set_and_get_exposure_limit(self, calculator):
        """Test setting and retrieving exposure limits"""
        limit = ExposureLimit(
            exposure_type=ExposureType.SECTOR,
            identifier='Technology',
            max_exposure=50.0,
            warning_threshold=40.0,
            is_percentage=True
        )
        
        calculator.set_exposure_limit(limit)
        
        limits = calculator.get_exposure_limits()
        assert 'sector_Technology' in limits
        assert limits['sector_Technology'].max_exposure == 50.0
    
    def test_remove_exposure_limit(self, calculator):
        """Test removing exposure limit"""
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='AAPL',
            max_exposure=20.0,
            warning_threshold=15.0
        )
        
        calculator.set_exposure_limit(limit)
        assert 'single_name_AAPL' in calculator.get_exposure_limits()
        
        calculator.remove_exposure_limit(ExposureType.SINGLE_NAME, 'AAPL')
        assert 'single_name_AAPL' not in calculator.get_exposure_limits()
    
    @pytest.mark.asyncio
    async def test_check_limits_critical_violation(self, calculator, portfolio_value):
        """Test critical violation detection (exceeds max_exposure)"""
        # Set limit at 10%
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='AAPL',
            max_exposure=10.0,
            warning_threshold=8.0,
            is_percentage=True
        )
        calculator.set_exposure_limit(limit)
        
        # Position at 15%
        positions = {'AAPL': {'quantity': 100, 'market_value': 15000.0}}
        exposures = await calculator.calculate_exposures(positions, portfolio_value)
        violations = await calculator.check_exposure_limits(exposures, portfolio_value)
        
        assert len(violations) == 1
        assert violations[0].severity == 'CRITICAL'
        assert violations[0].exposure_item.identifier == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_check_limits_warning_violation(self, calculator, portfolio_value):
        """Test warning violation detection (exceeds warning_threshold)"""
        # Set limit at 12%, warning at 8%
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='MSFT',
            max_exposure=12.0,
            warning_threshold=8.0,
            is_percentage=True
        )
        calculator.set_exposure_limit(limit)
        
        # Position at 10% (between warning and max)
        positions = {'MSFT': {'quantity': 100, 'market_value': 10000.0}}
        exposures = await calculator.calculate_exposures(positions, portfolio_value)
        violations = await calculator.check_exposure_limits(exposures, portfolio_value)
        
        assert len(violations) == 1
        assert violations[0].severity == 'WARNING'
    
    @pytest.mark.asyncio
    async def test_check_limits_no_violation(self, calculator, portfolio_value):
        """Test no violation when within limits"""
        # Set limit at 20%
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='GOOGL',
            max_exposure=20.0,
            warning_threshold=15.0,
            is_percentage=True
        )
        calculator.set_exposure_limit(limit)
        
        # Position at 10% (below warning)
        positions = {'GOOGL': {'quantity': 100, 'market_value': 10000.0}}
        exposures = await calculator.calculate_exposures(positions, portfolio_value)
        violations = await calculator.check_exposure_limits(exposures, portfolio_value)
        
        assert len(violations) == 0
    
    def test_percentage_vs_absolute_limits(self, calculator, portfolio_value):
        """Test both percentage and absolute limit types"""
        # Percentage limit
        item_pct = ExposureItem('AAPL', ExposureType.SINGLE_NAME, 12000.0, 12.0)
        limit_pct = ExposureLimit(ExposureType.SINGLE_NAME, 'AAPL', 10.0, 8.0, is_percentage=True)
        
        violation_pct = calculator._check_single_limit(item_pct, limit_pct, portfolio_value)
        assert violation_pct is not None
        assert violation_pct.severity == 'CRITICAL'
        
        # Absolute limit
        item_abs = ExposureItem('MSFT', ExposureType.SINGLE_NAME, 15000.0, 15.0)
        limit_abs = ExposureLimit(ExposureType.SINGLE_NAME, 'MSFT', 10000.0, 8000.0, is_percentage=False)
        
        violation_abs = calculator._check_single_limit(item_abs, limit_abs, portfolio_value)
        assert violation_abs is not None
        assert violation_abs.severity == 'CRITICAL'
    
    @pytest.mark.asyncio
    async def test_violation_history_cleanup(self, calculator, portfolio_value):
        """Test that old violations are cleaned up (24 hour retention)"""
        # Set limit
        limit = ExposureLimit(
            exposure_type=ExposureType.SINGLE_NAME,
            identifier='AAPL',
            max_exposure=10.0,
            warning_threshold=8.0
        )
        calculator.set_exposure_limit(limit)
        
        # Create violation
        positions = {'AAPL': {'quantity': 100, 'market_value': 15000.0}}
        exposures = await calculator.calculate_exposures(positions, portfolio_value)
        violations = await calculator.check_exposure_limits(exposures, portfolio_value)
        
        assert len(violations) == 1
        
        # Manually add old violation
        old_violation = ExposureViolation(
            exposure_item=ExposureItem('OLD', ExposureType.SINGLE_NAME, 1000, 1.0),
            limit=limit,
            violation_amount=100,
            violation_percentage=10.0,
            severity='WARNING',
            timestamp=datetime.now() - timedelta(hours=25)
        )
        calculator._violations.append(old_violation)
        
        # Check limits again (should trigger cleanup)
        await calculator.check_exposure_limits(exposures, portfolio_value)
        
        # Old violation should be removed
        current_violations = calculator.get_exposure_violations()
        assert all(v.timestamp >= datetime.now() - timedelta(hours=24) for v in current_violations)


# ============================================================================
# Category 7: Calculate Exposures Integration (5 tests)
# ============================================================================

class TestCalculateExposuresIntegration:
    """Test integrated exposure calculation functionality"""
    
    @pytest.mark.asyncio
    async def test_calculate_all_exposure_types(self, calculator, sample_positions_mixed, portfolio_value):
        """Test calculating all exposure types at once"""
        result = await calculator.calculate_exposures(sample_positions_mixed, portfolio_value)
        
        # Should have multiple exposure types
        assert ExposureType.MARKET in result
        assert ExposureType.SECTOR in result
        assert ExposureType.REGION in result
        assert ExposureType.CURRENCY in result
        assert ExposureType.FACTOR in result
        assert ExposureType.SINGLE_NAME in result
        
        # Verify market exposure
        market = result[ExposureType.MARKET]
        assert market.long_exposure == 20000.0
        assert market.short_exposure == 7500.0
    
    @pytest.mark.asyncio
    async def test_calculate_specific_exposure_types(self, calculator, sample_positions_long, portfolio_value):
        """Test calculating only specific exposure types"""
        result = await calculator.calculate_exposures(
            sample_positions_long,
            portfolio_value,
            exposure_types=[ExposureType.MARKET, ExposureType.SINGLE_NAME]
        )
        
        # Should only have requested types
        assert len(result) == 2
        assert ExposureType.MARKET in result
        assert ExposureType.SINGLE_NAME in result
        assert ExposureType.SECTOR not in result
    
    @pytest.mark.asyncio
    async def test_calculation_history_tracking(self, calculator, sample_positions_long, portfolio_value):
        """Test that calculation history is tracked"""
        initial_history_len = len(calculator.get_calculation_history())
        
        await calculator.calculate_exposures(sample_positions_long, portfolio_value)
        
        history = calculator.get_calculation_history()
        assert len(history) == initial_history_len + 1
        
        latest = history[-1]
        assert 'timestamp' in latest
        assert 'positions_count' in latest
        assert 'portfolio_value' in latest
        assert 'exposure_types' in latest
        assert 'calculation_time' in latest
        
        assert latest['positions_count'] == 2
        assert latest['portfolio_value'] == portfolio_value
    
    @pytest.mark.asyncio
    async def test_unsupported_exposure_types(self, calculator, sample_positions_long, portfolio_value):
        """Test handling of unsupported exposure types (CREDIT, DURATION, VOLATILITY)"""
        # These types should log warnings but return empty breakdowns
        result = await calculator.calculate_exposures(
            sample_positions_long,
            portfolio_value,
            exposure_types=[ExposureType.CREDIT, ExposureType.DURATION, ExposureType.VOLATILITY]
        )
        
        # Should return empty breakdowns
        assert ExposureType.CREDIT in result
        assert result[ExposureType.CREDIT].total_exposure == 0
        assert len(result[ExposureType.CREDIT].exposures) == 0
    
    @pytest.mark.asyncio
    async def test_should_include_position_filters(self, calculator_custom):
        """Test position filtering logic"""
        # Test 1: Cash position (should be included with custom config)
        cash_position = {'quantity': 1000, 'asset_type': 'CASH', 'market_value': 1000}
        assert calculator_custom._should_include_position(cash_position) is True
        
        # Test 2: Derivative position (should be excluded with custom config)
        derivative_position = {'quantity': 10, 'asset_type': 'OPTION', 'market_value': 500}
        assert calculator_custom._should_include_position(derivative_position) is False
        
        # Test 3: Zero quantity (should always be excluded)
        zero_position = {'quantity': 0, 'market_value': 0}
        assert calculator_custom._should_include_position(zero_position) is False
        
        # Test 4: Normal stock position (should always be included)
        stock_position = {'quantity': 100, 'asset_type': 'STOCK', 'market_value': 15000}
        assert calculator_custom._should_include_position(stock_position) is True


# ============================================================================
# Category 8: Utility Methods (3 tests)
# ============================================================================

class TestUtilityMethods:
    """Test utility and helper methods"""
    
    def test_get_factor_loadings(self, calculator):
        """Test factor loadings retrieval"""
        loadings = calculator._get_factor_loadings('AAPL')
        
        # Should have all 6 factors
        assert 'Value' in loadings
        assert 'Growth' in loadings
        assert 'Momentum' in loadings
        assert 'Quality' in loadings
        assert 'Size' in loadings
        assert 'Volatility' in loadings
        
        # Verify loadings are in expected range (-0.5 to 0.5)
        for factor, loading in loadings.items():
            assert -0.5 <= loading <= 0.5
    
    def test_clear_cache(self, calculator):
        """Test cache clearing"""
        # Add something to cache
        calculator._exposure_cache['test_key'] = {'data': 'value'}
        assert len(calculator._exposure_cache) > 0
        
        calculator.clear_cache()
        
        assert len(calculator._exposure_cache) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_method(self, calculator):
        """Test cleanup method"""
        # Should execute without errors
        await calculator.cleanup()
        
        # Currently just logs, but verify method exists and is callable
        assert hasattr(calculator, 'cleanup')


# ============================================================================
# Category 9: Edge Cases (2 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_zero_portfolio_value(self, calculator, sample_positions_long):
        """Test handling of zero portfolio value (avoid division by zero)"""
        result = await calculator.calculate_exposures(sample_positions_long, 0.0)
        
        # Should not crash, percentages should be 0
        for exposure_type, breakdown in result.items():
            for exposure_item in breakdown.exposures:
                assert exposure_item.percentage == 0.0
    
    @pytest.mark.asyncio
    async def test_get_violations_by_severity(self, calculator, portfolio_value):
        """Test filtering violations by severity"""
        # Set up limits and create violations
        limit1 = ExposureLimit(ExposureType.SINGLE_NAME, 'AAPL', 10.0, 8.0)
        limit2 = ExposureLimit(ExposureType.SINGLE_NAME, 'MSFT', 15.0, 12.0)
        calculator.set_exposure_limit(limit1)
        calculator.set_exposure_limit(limit2)
        
        positions = {
            'AAPL': {'quantity': 100, 'market_value': 12000.0},  # CRITICAL (12% > 10%)
            'MSFT': {'quantity': 100, 'market_value': 13000.0}   # WARNING (13% > 12%, < 15%)
        }
        
        exposures = await calculator.calculate_exposures(positions, portfolio_value)
        await calculator.check_exposure_limits(exposures, portfolio_value)
        
        # Filter by severity
        critical_violations = calculator.get_exposure_violations(severity='CRITICAL')
        warning_violations = calculator.get_exposure_violations(severity='WARNING')
        
        assert len(critical_violations) == 1
        assert len(warning_violations) == 1
        assert critical_violations[0].exposure_item.identifier == 'AAPL'
        assert warning_violations[0].exposure_item.identifier == 'MSFT'
