# Single Source Strategy Template Implementation Plan

## 🎯 Executive Summary

This document outlines the comprehensive re-architecture plan to achieve **single source of truth** for strategy definitions using strategy templates. The goal is to eliminate all duplication of strategy definitions across the 3-layer architecture and centralize all strategy logic in template files.

## 🏗️ Current Architecture Issues

### ❌ Current Problems
1. **Strategy definitions scattered across layers**
   - Test cases contain hardcoded strategy definitions
   - Strategy layer has partial definitions
   - Core engine uses injected parameters from multiple sources

2. **Duplication of strategy logic**
   - Same strategy parameters defined in multiple places
   - Inconsistent strategy configurations across tests
   - Difficult to maintain and update strategies

3. **No single source of truth**
   - Strategy changes require updates in multiple locations
   - Risk of inconsistent strategy behavior
   - Difficult to version control strategy evolution

### ✅ Target Architecture
1. **Single source of truth**: All strategy definitions in template files
2. **Template-based assembly**: Strategy creation through template + customization
3. **Zero duplication**: No strategy definitions outside templates
4. **Easy maintenance**: Update template once, all tests automatically updated

## 📋 Implementation Phases

### Phase 1: Template Infrastructure Foundation (Week 1)

#### 1.1 Create Template Directory Structure
```bash
strategies/
├── templates/
│   ├── momentum_v1.json
│   ├── mean_reversion_v1.json
│   ├── trend_following_v1.json
│   ├── pairs_trading_v1.json
│   └── volatility_strategy_v1.json
├── registry.py
├── assembler.py
├── validator.py
└── __init__.py
```

#### 1.2 Implement Strategy Template Registry
```python
# strategies/registry.py
class StrategyTemplateRegistry:
    """Central registry for all strategy templates"""
    
    def __init__(self, templates_directory: str = "strategies/templates"):
        self.templates_directory = templates_directory
        self.templates = {}
        self._load_all_templates()
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Single access point for strategy definitions"""
        if template_id not in self.templates:
            available_templates = list(self.templates.keys())
            raise ValueError(f"Template {template_id} not found. Available: {available_templates}")
        return self.templates[template_id]
    
    def list_templates(self) -> List[str]:
        """Get all available template IDs"""
        return list(self.templates.keys())
    
    def get_template_metadata(self, template_id: str) -> Dict[str, Any]:
        """Get template metadata for selection"""
        template = self.get_template(template_id)
        return {
            'template_id': template['template_id'],
            'template_name': template['template_name'],
            'template_type': template['template_type'],
            'version': template['version'],
            'description': template.get('description', ''),
            'tags': template.get('metadata', {}).get('tags', []),
            'expected_return': template.get('metadata', {}).get('expected_return'),
            'expected_volatility': template.get('metadata', {}).get('expected_volatility')
        }
```

#### 1.3 Create Sample Strategy Templates
```json
// strategies/templates/momentum_v1.json
{
    "template_id": "momentum_v1",
    "template_name": "Momentum Strategy",
    "template_type": "momentum",
    "version": "1.0.0",
    "description": "Multi-indicator momentum strategy with RSI, MACD, and price momentum",
    
    "base_parameters": {
        "signal_generation": {
            "indicators": {
                "rsi": {
                    "type": "rsi",
                    "period": 14,
                    "oversold": 25,
                    "overbought": 75,
                    "weight": 0.4
                },
                "macd": {
                    "type": "macd",
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "weight": 0.4
                },
                "price_momentum": {
                    "type": "price_momentum",
                    "lookback_period": 50,
                    "weight": 0.2
                }
            },
            "signal_combination": {
                "method": "weighted_average",
                "min_signal_strength": 0.65
            },
            "volume_confirmation": {
                "enabled": true,
                "volume_threshold": 1.2,
                "lookback_period": 20
            }
        },
        
        "risk_management": {
            "position_sizing": {
                "type": "signal_based",
                "max_position_size": 0.25,
                "risk_per_trade": 0.02,
                "volatility_adjustment": {
                    "enabled": true,
                    "lookback_period": 20,
                    "adjustment_factor": 10
                }
            },
            "stop_loss": {
                "type": "percentage",
                "stop_loss_pct": 0.08,
                "trailing_stop": true
            },
            "take_profit": {
                "type": "percentage",
                "take_profit_pct": 0.20
            }
        },
        
        "entry_exit_logic": {
            "entry_conditions": {
                "min_signal_strength": 0.65,
                "confirmation_period": 2,
                "volume_confirmation": true
            },
            "exit_conditions": {
                "signal_reversal_threshold": -0.35,
                "max_holding_period": 60,
                "profit_target": 0.20
            }
        },
        
        "execution": {
            "order_type": "limit",
            "execution_timing": "immediate",
            "market_impact_management": {
                "enabled": true,
                "max_order_size": 0.01
            }
        },
        
        "portfolio_management": {
            "initial_capital": 100000,
            "cash_reserve": 0.05,
            "rebalancing": {
                "frequency": "weekly",
                "threshold": 0.10
            }
        }
    },
    
    "adaptation_framework": {
        "adaptation_enabled": true,
        "adaptation_frequency": "daily",
        "parameter_bounds": {
            "rsi_period": {"min": 7, "max": 28, "default": 14},
            "macd_fast": {"min": 5, "max": 15, "default": 12},
            "macd_slow": {"min": 20, "max": 40, "default": 26},
            "position_size": {"min": 0.1, "max": 0.4, "default": 0.25},
            "stop_loss": {"min": 0.05, "max": 0.15, "default": 0.08}
        },
        "adaptation_triggers": {
            "performance_degradation": 0.1,
            "volatility_change": 0.5,
            "regime_change": true,
            "correlation_breakdown": 0.3
        }
    },
    
    "metadata": {
        "tags": ["momentum", "technical_analysis", "multi_indicator"],
        "expected_return": 0.15,
        "expected_volatility": 0.20,
        "sharpe_ratio": 0.75,
        "max_drawdown": 0.15,
        "suitable_markets": ["equity", "forex", "crypto"],
        "suitable_timeframes": ["5min", "15min", "1hour", "1day"]
    }
}
```

#### 1.4 Implement Strategy Assembler
```python
# strategies/assembler.py
class StrategyAssembler:
    """Assemble strategy from template with customization"""
    
    def __init__(self, template_registry: StrategyTemplateRegistry):
        self.template_registry = template_registry
        self.strategy_parser = StrategyParser()
    
    def assemble_strategy(self, template_id: str, customizations: Dict[str, Any] = None) -> StrategyConfig:
        """Create strategy from template only"""
        
        # Get base template
        template = self.template_registry.get_template(template_id)
        
        # Apply customizations
        if customizations:
            assembled_strategy = self._apply_customizations(template, customizations)
        else:
            assembled_strategy = template.copy()
        
        # Generate unique strategy ID
        assembled_strategy['strategy_id'] = f"{template_id}_{uuid.uuid4().hex[:8]}"
        assembled_strategy['assembled_from_template'] = template_id
        assembled_strategy['customizations'] = customizations or {}
        assembled_strategy['assembly_timestamp'] = datetime.now().isoformat()
        
        # Parse and validate
        parsed_strategy = self.strategy_parser.parse_strategy_data(assembled_strategy, validate=True)
        
        # Convert to StrategyConfig
        strategy_config = StrategyConfig(
            strategy_id=parsed_strategy['strategy_id'],
            name=parsed_strategy['template_name'],
            strategy_type=StrategyType(parsed_strategy['template_type']),
            version=parsed_strategy['version'],
            description=parsed_strategy.get('description'),
            signal_generation=parsed_strategy['base_parameters']['signal_generation'],
            risk_management=parsed_strategy['base_parameters']['risk_management'],
            entry_exit_logic=parsed_strategy['base_parameters']['entry_exit_logic'],
            execution=parsed_strategy['base_parameters']['execution'],
            portfolio_management=parsed_strategy['base_parameters']['portfolio_management'],
            adaptation_framework=parsed_strategy['adaptation_framework'],
            metadata=parsed_strategy.get('metadata', {})
        )
        
        return strategy_config
    
    def _apply_customizations(self, template: Dict[str, Any], customizations: Dict[str, Any]) -> Dict[str, Any]:
        """Apply customizations to template"""
        assembled = template.copy()
        
        # Deep merge customizations
        for key, value in customizations.items():
            if key in assembled and isinstance(assembled[key], dict) and isinstance(value, dict):
                assembled[key] = self._deep_merge(assembled[key], value)
            else:
                assembled[key] = value
        
        return assembled
```

#### 1.5 Deliverables for Phase 1
- [ ] Template directory structure created
- [ ] Strategy template registry implemented
- [ ] Strategy assembler implemented
- [ ] Sample strategy templates created (momentum, mean_reversion, trend_following)
- [ ] Unit tests for template registry and assembler
- [ ] Documentation for template format and usage

### Phase 2: Strategy Layer Re-Architecture (Week 2)

#### 2.1 Re-Architect Strategy Layer
```python
# strategy_layer/base.py - REFACTORED
class StrategyLayer:
    """Template-centric strategy layer"""
    
    def __init__(self):
        self.template_registry = StrategyTemplateRegistry()
        self.strategy_assembler = StrategyAssembler(self.template_registry)
    
    def create_strategy(self, template_id: str, customizations: Dict[str, Any] = None) -> StrategyConfig:
        """Create strategy from template only"""
        return self.strategy_assembler.assemble_strategy(template_id, customizations)
    
    def list_available_strategies(self) -> List[str]:
        """Get all available strategy templates"""
        return self.template_registry.list_templates()
    
    def get_strategy_metadata(self, template_id: str) -> Dict[str, Any]:
        """Get strategy template metadata"""
        return self.template_registry.get_template_metadata(template_id)
    
    def validate_template(self, template_id: str) -> bool:
        """Validate template structure"""
        template = self.template_registry.get_template(template_id)
        return self._validate_template_structure(template)
```

#### 2.2 Remove Hardcoded Strategy Definitions
```python
# ❌ REMOVE: Old hardcoded strategy creation methods
# def create_momentum_strategy_config(self) -> StrategyConfig:
#     strategy_definition = {
#         "strategy_id": "real_momentum_backtest",
#         "strategy_name": "Enhanced Momentum Strategy",
#         # ... 100+ lines of hardcoded strategy definition
#     }
#     # Remove this entire method
```

#### 2.3 Update Strategy Parser
```python
# strategy_layer/parsers/strategy_parser.py - REFACTORED
class StrategyParser:
    """Parser for template-based strategy definitions"""
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
    
    def parse_template_strategy(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse strategy from template data"""
        # Validate template structure
        self.schema_validator.validate_template_structure(template_data)
        
        # Add parsing metadata
        parsed_data = self._add_parsing_metadata(template_data)
        
        return parsed_data
    
    def parse_customizations(self, customizations: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate customizations"""
        # Validate customization structure
        self.schema_validator.validate_customizations(customizations)
        
        return customizations
```

#### 2.4 Deliverables for Phase 2
- [ ] Strategy layer refactored to be template-centric
- [ ] All hardcoded strategy definitions removed
- [ ] Strategy parser updated for template parsing
- [ ] Unit tests updated for template-based strategy creation
- [ ] Integration tests for strategy layer with templates

### Phase 3: Scenario Layer Re-Architecture (Week 3)

#### 3.1 Create Template-Aware Backtesting Engine
```python
# scenario_layer/backtesting/template_backtesting_engine.py - NEW
class TemplateBasedBacktestingEngine(HistoricalBacktestingEngine):
    """Template-aware backtesting engine"""
    
    def __init__(self, config: BacktestConfig, strategy_layer: StrategyLayer):
        super().__init__(config)
        self.strategy_layer = strategy_layer
    
    async def run_backtest_with_template(self, template_id: str, customizations: Dict[str, Any] = None) -> BacktestResult:
        """Run backtest using template"""
        # Create strategy from template
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        
        # Set strategy configuration
        self.strategy_config = strategy_config
        
        # Run backtest
        return await self.run_backtest()
    
    async def run_backtest_with_strategy(self, strategy_config: StrategyConfig) -> BacktestResult:
        """Run backtest with assembled strategy"""
        self.strategy_config = strategy_config
        return await self.run_backtest()
```

#### 3.2 Create Template-Aware Scenario Layer
```python
# scenario_layer/template_scenario_layer.py - NEW
class TemplateAwareScenarioLayer:
    """Template-aware scenario layer"""
    
    def __init__(self):
        self.strategy_layer = StrategyLayer()
        self.backtesting_engine = TemplateBasedBacktestingEngine()
        self.simulation_engine = TemplateBasedSimulationEngine()
        self.paper_trading_engine = TemplateBasedPaperTradingEngine()
    
    async def run_backtest(self, template_id: str, scenario_config: BacktestConfig, customizations: Dict[str, Any] = None) -> BacktestResult:
        """Run backtest using template"""
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        return await self.backtesting_engine.run_backtest_with_strategy(strategy_config, scenario_config)
    
    async def run_simulation(self, template_id: str, scenario_config: SimulationConfig, customizations: Dict[str, Any] = None) -> SimulationResult:
        """Run simulation using template"""
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        return await self.simulation_engine.run_simulation_with_strategy(strategy_config, scenario_config)
    
    async def run_paper_trading(self, template_id: str, scenario_config: PaperTradingConfig, customizations: Dict[str, Any] = None) -> PaperTradingResult:
        """Run paper trading using template"""
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        return await self.paper_trading_engine.run_paper_trading_with_strategy(strategy_config, scenario_config)
```

#### 3.3 Remove Old Scenario Methods
```python
# ❌ REMOVE: Old hardcoded scenario methods
# def create_momentum_strategy_config(self) -> StrategyConfig:
#     # Remove this method from all scenario classes
```

#### 3.4 Deliverables for Phase 3
- [ ] Template-aware backtesting engine implemented
- [ ] Template-aware scenario layer implemented
- [ ] All hardcoded scenario methods removed
- [ ] Unit tests for template-based scenarios
- [ ] Integration tests for template-based backtesting

### Phase 4: Core Engine Re-Architecture (Week 4)

#### 4.1 Create Template-Compatible Core Engine
```python
# core_structure/template_core_engine.py - NEW
class TemplateCompatibleCoreEngine(UnifiedCoreEngine):
    """Template-compatible core engine"""
    
    def __init__(self, config: CoreEngineConfig, strategy_layer: StrategyLayer):
        super().__init__(config)
        self.strategy_layer = strategy_layer
    
    async def process_trading_cycle_with_template(self, data_source: Any, template_id: str, customizations: Dict[str, Any] = None) -> TradingResult:
        """Process trading cycle using template"""
        # Create strategy from template
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        
        # Process trading cycle
        return await self.process_trading_cycle(data_source, strategy_config)
    
    def inject_template_parameters(self, template_id: str, customizations: Dict[str, Any] = None):
        """Inject parameters from template"""
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        self.inject_strategy_parameters(strategy_config)
    
    async def setup_template_strategy(self, template_id: str, customizations: Dict[str, Any] = None):
        """Setup core engine with template strategy"""
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        self.inject_strategy_parameters(strategy_config)
        await self.initialize_components()
```

#### 4.2 Update Unified Core Engine
```python
# core_structure/unified_core_engine.py - REFACTORED
class UnifiedCoreEngine:
    """Unified core engine with template compatibility"""
    
    def __init__(self, config: Optional[CoreEngineConfig] = None):
        super().__init__(config)
        # Add template compatibility
        self.template_mode = False
        self.strategy_layer = None
    
    def enable_template_mode(self, strategy_layer: StrategyLayer):
        """Enable template mode"""
        self.template_mode = True
        self.strategy_layer = strategy_layer
    
    async def process_trading_cycle(self, data_source: Any, strategy_config: StrategyConfig) -> TradingResult:
        """Process trading cycle with strategy config"""
        # Existing implementation
        pass
    
    async def process_trading_cycle_with_template(self, data_source: Any, template_id: str, customizations: Dict[str, Any] = None) -> TradingResult:
        """Process trading cycle with template"""
        if not self.template_mode:
            raise ValueError("Template mode not enabled")
        
        strategy_config = self.strategy_layer.create_strategy(template_id, customizations)
        return await self.process_trading_cycle(data_source, strategy_config)
```

#### 4.3 Deliverables for Phase 4
- [ ] Template-compatible core engine implemented
- [ ] Unified core engine updated for template compatibility
- [ ] Template mode functionality implemented
- [ ] Unit tests for template-based core engine
- [ ] Integration tests for template-based trading cycles

### Phase 5: Test Cases Re-Architecture (Week 5)

#### 5.1 Create Template-Based Test Cases
```python
# tests/test_template_based_backtest.py - NEW
class TemplateBasedBacktestTest(unittest.TestCase):
    """Template-only strategy testing"""
    
    def setUp(self):
        # Initialize template infrastructure
        self.strategy_layer = StrategyLayer()
        self.scenario_layer = TemplateAwareScenarioLayer()
        
        # Test environment parameters only
        self.initial_capital = 100_000.0
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        self.training_start = datetime(2024, 1, 3)
        self.training_end = datetime(2024, 12, 31)
    
    def test_momentum_strategy_basic(self):
        """Test basic momentum strategy from template"""
        # Create backtest configuration
        backtest_config = BacktestConfig(
            symbols=self.symbols,
            time_range=TimeRange(start_date=self.training_start, end_date=self.training_end),
            initial_capital=self.initial_capital
        )
        
        # Run backtest with template
        result = asyncio.run(self.scenario_layer.run_backtest(
            template_id="momentum_v1",
            scenario_config=backtest_config,
            customizations=None
        ))
        
        # Validate results
        self._validate_basic_performance(result)
    
    def test_momentum_strategy_customized(self):
        """Test momentum strategy with customizations"""
        customizations = {
            "base_parameters": {
                "risk_management": {
                    "position_sizing": {"max_position_size": 0.20}
                },
                "signal_generation": {
                    "indicators": {
                        "rsi": {"weight": 0.5},
                        "macd": {"weight": 0.3},
                        "price_momentum": {"weight": 0.2}
                    }
                }
            }
        }
        
        backtest_config = BacktestConfig(
            symbols=self.symbols,
            time_range=TimeRange(start_date=self.training_start, end_date=self.training_end),
            initial_capital=self.initial_capital
        )
        
        result = asyncio.run(self.scenario_layer.run_backtest(
            template_id="momentum_v1",
            scenario_config=backtest_config,
            customizations=customizations
        ))
        
        self._validate_customized_performance(result)
    
    def test_multiple_strategy_comparison(self):
        """Compare multiple strategy templates"""
        template_ids = ["momentum_v1", "mean_reversion_v1", "trend_following_v1"]
        results = {}
        
        backtest_config = BacktestConfig(
            symbols=self.symbols,
            time_range=TimeRange(start_date=self.training_start, end_date=self.training_end),
            initial_capital=self.initial_capital
        )
        
        for template_id in template_ids:
            result = asyncio.run(self.scenario_layer.run_backtest(
                template_id=template_id,
                scenario_config=backtest_config,
                customizations=None
            ))
            results[template_id] = result
        
        # Compare performance across templates
        self._compare_template_performance(results)
    
    def _validate_basic_performance(self, result: BacktestResult):
        """Validate basic performance metrics"""
        self.assertIsNotNone(result)
        self.assertGreater(result.final_portfolio_value, 0)
        self.assertLessEqual(abs(result.metrics.max_drawdown), 50.0)
    
    def _validate_customized_performance(self, result: BacktestResult):
        """Validate customized performance metrics"""
        self.assertIsNotNone(result)
        self.assertGreater(result.final_portfolio_value, 0)
        # Additional validation for customized parameters
    
    def _compare_template_performance(self, results: Dict[str, BacktestResult]):
        """Compare performance across templates"""
        for template_id, result in results.items():
            self.assertIsNotNone(result)
            self.assertGreater(result.final_portfolio_value, 0)
```

#### 5.2 Remove Old Test Cases
```python
# ❌ REMOVE: Old hardcoded test cases
# class RealMomentumBacktestTest(unittest.TestCase):
#     def create_momentum_strategy_config(self) -> StrategyConfig:
#         # Remove this entire method and class
```

#### 5.3 Deliverables for Phase 5
- [ ] Template-based test cases implemented
- [ ] All hardcoded test cases removed
- [ ] Template comparison tests implemented
- [ ] Performance validation tests updated
- [ ] Integration tests for complete template workflow

### Phase 6: Integration and Validation (Week 6)

#### 6.1 End-to-End Integration Testing
```python
# tests/test_template_integration.py - NEW
class TemplateIntegrationTest(unittest.TestCase):
    """End-to-end template integration testing"""
    
    def setUp(self):
        self.strategy_layer = StrategyLayer()
        self.scenario_layer = TemplateAwareScenarioLayer()
        self.core_engine = TemplateCompatibleCoreEngine()
    
    def test_complete_template_workflow(self):
        """Test complete template workflow from template to execution"""
        # 1. Load template
        template_id = "momentum_v1"
        template = self.strategy_layer.template_registry.get_template(template_id)
        self.assertIsNotNone(template)
        
        # 2. Assemble strategy
        strategy_config = self.strategy_layer.create_strategy(template_id)
        self.assertIsNotNone(strategy_config)
        self.assertEqual(strategy_config.strategy_type, StrategyType.MOMENTUM)
        
        # 3. Run backtest
        backtest_config = self._create_backtest_config()
        result = asyncio.run(self.scenario_layer.run_backtest(
            template_id=template_id,
            scenario_config=backtest_config
        ))
        
        # 4. Validate results
        self.assertIsNotNone(result)
        self.assertTrue(result.is_completed)
    
    def test_template_customization_workflow(self):
        """Test template customization workflow"""
        customizations = {
            "base_parameters": {
                "risk_management": {
                    "position_sizing": {"max_position_size": 0.15}
                }
            }
        }
        
        # Assemble customized strategy
        strategy_config = self.strategy_layer.create_strategy("momentum_v1", customizations)
        
        # Verify customization applied
        self.assertEqual(
            strategy_config.risk_management['position_sizing']['max_position_size'],
            0.15
        )
```

#### 6.2 Performance Validation
```python
# tests/test_template_performance.py - NEW
class TemplatePerformanceTest(unittest.TestCase):
    """Template performance validation"""
    
    def test_template_performance_consistency(self):
        """Test that template performance is consistent"""
        # Run same template multiple times
        results = []
        for i in range(5):
            result = self._run_template_backtest("momentum_v1")
            results.append(result)
        
        # Verify consistency
        final_values = [r.final_portfolio_value for r in results]
        self._assert_performance_consistency(final_values)
    
    def test_template_vs_hardcoded_equivalence(self):
        """Test that template produces same results as hardcoded strategy"""
        # This test ensures no regression when migrating to templates
        pass
```

#### 6.3 Deliverables for Phase 6
- [ ] End-to-end integration tests implemented
- [ ] Template workflow validation completed
- [ ] Performance consistency tests implemented
- [ ] Template vs hardcoded equivalence tests
- [ ] Complete system validation

## 🎯 Success Criteria

### Phase 1 Success Criteria
- [ ] Template infrastructure fully functional
- [ ] All sample templates created and validated
- [ ] Template registry and assembler working correctly
- [ ] Unit tests passing for template components

### Phase 2 Success Criteria
- [ ] Strategy layer completely template-centric
- [ ] All hardcoded strategy definitions removed
- [ ] Strategy parser working with templates
- [ ] No strategy definitions outside templates

### Phase 3 Success Criteria
- [ ] Scenario layer template-aware
- [ ] All scenario methods using templates
- [ ] Backtesting working with template strategies
- [ ] No hardcoded scenario methods

### Phase 4 Success Criteria
- [ ] Core engine template-compatible
- [ ] Template mode fully functional
- [ ] Trading cycles working with templates
- [ ] No hardcoded core engine parameters

### Phase 5 Success Criteria
- [ ] All test cases template-based
- [ ] No hardcoded test strategies
- [ ] Template comparison tests working
- [ ] Complete test coverage for templates

### Phase 6 Success Criteria
- [ ] End-to-end integration working
- [ ] Template workflow fully validated
- [ ] Performance consistency verified
- [ ] System ready for production use

## 🚀 Post-Implementation Benefits

### 1. Single Source of Truth
- All strategy definitions in template files
- No duplication across layers
- Easy to maintain and update

### 2. Template Reusability
- Same template used across multiple scenarios
- Consistent strategy behavior
- Easy to version control

### 3. Easy Maintenance
- Update template once, all tests automatically updated
- Clear versioning of strategy evolution
- Reduced maintenance overhead

### 4. Enhanced Testing
- Easy to test multiple strategy variations
- Template comparison testing
- Performance benchmarking across templates

### 5. Scalability
- Easy to add new strategy templates
- Template inheritance and composition
- Dynamic strategy assembly

## 📝 Documentation Requirements

### Template Documentation
- Template format specification
- Template validation rules
- Customization guidelines
- Template versioning strategy

### API Documentation
- Template registry API
- Strategy assembler API
- Template-aware scenario API
- Template-compatible core engine API

### User Guide
- How to create new templates
- How to customize templates
- How to run template-based tests
- Best practices for template design

## 🔧 Migration Strategy

### Gradual Migration
1. **Phase 1-2**: Create template infrastructure alongside existing code
2. **Phase 3-4**: Implement template-aware components
3. **Phase 5-6**: Migrate test cases to templates
4. **Final**: Remove all hardcoded strategy definitions

### Backward Compatibility
- Maintain compatibility with existing tests during migration
- Gradual deprecation of hardcoded methods
- Clear migration path for existing code

### Testing Strategy
- Comprehensive unit tests for each phase
- Integration tests for template workflow
- Performance regression testing
- End-to-end validation

This implementation plan provides a clear roadmap for achieving the single source of truth goal while maintaining system stability and ensuring comprehensive testing throughout the migration process.
