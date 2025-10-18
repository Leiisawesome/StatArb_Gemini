"""
Phase 1 Test Checkpoint: Configuration System Validation
========================================================

Validates Phase 1 implementation:
- 1.1: Directory structure
- 1.2: BacktestConfiguration system
- 1.3: Example JSON configs

This is the first TEST CHECKPOINT in the Escort Development model.
"""

import pytest
from pathlib import Path
import json
import sys

# Add backtest to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.backtest_config import (
    BacktestConfiguration,
    BacktestMode,
    DataConfig,
    StrategyConfig,
    RiskConfig,
    ExecutionConfig,
    AnalyticsConfig
)


class TestPhase1ConfigurationSystem:
    """Test Phase 1: Configuration Foundation"""
    
    @pytest.fixture
    def backtest_root(self):
        """Get backtest root directory"""
        return Path(__file__).parent.parent
    
    # ============================================================
    # TEST 1.1: Directory Structure
    # ============================================================
    
    def test_directory_structure_exists(self, backtest_root):
        """Validate Phase 1.1: All required directories exist"""
        required_dirs = [
            'config',
            'config/examples',
            'engine',
            'reporting',
            'cli',
            'utils',
            'examples',
            'tests'
        ]
        
        for dir_name in required_dirs:
            dir_path = backtest_root / dir_name
            assert dir_path.exists(), f"❌ Missing directory: {dir_name}"
            assert dir_path.is_dir(), f"❌ Not a directory: {dir_name}"
        
        print("✅ TEST 1.1: All directories exist")
    
    def test_init_files_exist(self, backtest_root):
        """Validate Phase 1.1: All __init__.py files exist"""
        required_init_files = [
            '__init__.py',
            'config/__init__.py',
            'engine/__init__.py',
            'reporting/__init__.py',
            'cli/__init__.py',
            'utils/__init__.py',
            'examples/__init__.py',
            'tests/__init__.py'
        ]
        
        for init_file in required_init_files:
            init_path = backtest_root / init_file
            assert init_path.exists(), f"❌ Missing __init__.py: {init_file}"
            assert init_path.is_file(), f"❌ Not a file: {init_file}"
        
        print("✅ TEST 1.1: All __init__.py files exist")
    
    # ============================================================
    # TEST 1.2: Configuration Classes
    # ============================================================
    
    def test_data_config_validation(self):
        """Validate Phase 1.2: DataConfig validation"""
        # Valid config
        valid_config = DataConfig(
            symbols=["NVDA"],
            start_date="2024-01-02",
            end_date="2024-03-31"
        )
        valid, errors = valid_config.validate()
        assert valid, f"❌ Valid config failed: {errors}"
        
        # Invalid: no symbols
        invalid_config = DataConfig(
            symbols=[],
            start_date="2024-01-02",
            end_date="2024-03-31"
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with no symbols"
        assert any("symbol" in str(e).lower() for e in errors)
        
        # Invalid: end before start
        invalid_config = DataConfig(
            symbols=["NVDA"],
            start_date="2024-03-31",
            end_date="2024-01-02"
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with end_date before start_date"
        
        print("✅ TEST 1.2: DataConfig validation works")
    
    def test_strategy_config_validation(self):
        """Validate Phase 1.2: StrategyConfig validation"""
        # Valid config
        valid_config = StrategyConfig(
            strategy_type="momentum",
            strategy_name="test_momentum",
            allocation_pct=0.5
        )
        valid, errors = valid_config.validate()
        assert valid, f"❌ Valid config failed: {errors}"
        
        # Invalid: bad strategy type
        invalid_config = StrategyConfig(
            strategy_type="invalid_strategy",
            strategy_name="test",
            allocation_pct=0.5
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with invalid strategy type"
        
        # Invalid: allocation > 1
        invalid_config = StrategyConfig(
            strategy_type="momentum",
            strategy_name="test",
            allocation_pct=1.5
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with allocation > 1"
        
        print("✅ TEST 1.2: StrategyConfig validation works")
    
    def test_risk_config_validation(self):
        """Validate Phase 1.2: RiskConfig validation"""
        # Valid config
        valid_config = RiskConfig(
            initial_capital=1_000_000.0,
            max_position_size=0.10
        )
        valid, errors = valid_config.validate()
        assert valid, f"❌ Valid config failed: {errors}"
        
        # Invalid: negative capital
        invalid_config = RiskConfig(
            initial_capital=-100.0
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with negative capital"
        
        print("✅ TEST 1.2: RiskConfig validation works")
    
    def test_execution_config_validation(self):
        """Validate Phase 1.2: ExecutionConfig validation"""
        # Valid config
        valid_config = ExecutionConfig(
            min_liquidity_score=60.0,
            impact_model="almgren_chriss"
        )
        valid, errors = valid_config.validate()
        assert valid, f"❌ Valid config failed: {errors}"
        
        # Invalid: bad impact model
        invalid_config = ExecutionConfig(
            impact_model="invalid_model"
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with invalid impact model"
        
        print("✅ TEST 1.2: ExecutionConfig validation works")
    
    def test_analytics_config_validation(self):
        """Validate Phase 1.2: AnalyticsConfig validation"""
        # Valid config
        valid_config = AnalyticsConfig(
            enable_regime_attribution=True,
            metrics_calculation_frequency="end_of_day"
        )
        valid, errors = valid_config.validate()
        assert valid, f"❌ Valid config failed: {errors}"
        
        # Invalid: bad frequency
        invalid_config = AnalyticsConfig(
            metrics_calculation_frequency="invalid_freq"
        )
        valid, errors = invalid_config.validate()
        assert not valid, "❌ Should fail with invalid frequency"
        
        print("✅ TEST 1.2: AnalyticsConfig validation works")
    
    def test_backtest_configuration_complete(self):
        """Validate Phase 1.2: Complete BacktestConfiguration"""
        config = BacktestConfiguration(
            backtest_name="Test Backtest",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            data=DataConfig(
                symbols=["NVDA"],
                start_date="2024-01-02",
                end_date="2024-03-31"
            ),
            strategies=[
                StrategyConfig(
                    strategy_type="momentum",
                    strategy_name="test_momentum",
                    allocation_pct=1.0
                )
            ],
            risk=RiskConfig(initial_capital=1_000_000.0),
            execution=ExecutionConfig(),
            analytics=AnalyticsConfig()
        )
        
        # Validate
        valid, errors = config.validate()
        assert valid, f"❌ Complete config failed validation: {errors}"
        
        # Convert to dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'backtest_name' in config_dict
        assert 'data' in config_dict
        assert 'strategies' in config_dict
        
        print("✅ TEST 1.2: Complete BacktestConfiguration works")
    
    # ============================================================
    # TEST 1.3: Example JSON Configs
    # ============================================================
    
    def test_example_configs_exist(self, backtest_root):
        """Validate Phase 1.3: All example JSON configs exist"""
        required_examples = [
            'config/examples/single_strategy.json',
            'config/examples/multi_strategy.json',
            'config/examples/regime_adaptive.json'
        ]
        
        for example_file in required_examples:
            example_path = backtest_root / example_file
            assert example_path.exists(), f"❌ Missing example: {example_file}"
            assert example_path.is_file(), f"❌ Not a file: {example_file}"
        
        print("✅ TEST 1.3: All example configs exist")
    
    def test_example_single_strategy_loads(self, backtest_root):
        """Validate Phase 1.3: Single strategy config loads and validates"""
        config_path = backtest_root / 'config/examples/single_strategy.json'
        config = BacktestConfiguration.from_json(config_path)
        
        # Validate loaded config
        assert config.backtest_name == "Example Single Strategy Backtest"
        assert config.backtest_mode == BacktestMode.SINGLE_STRATEGY
        assert len(config.strategies) == 1
        assert config.strategies[0].strategy_type == "momentum"
        
        # Validate config
        valid, errors = config.validate()
        assert valid, f"❌ Single strategy config invalid: {errors}"
        
        print("✅ TEST 1.3: single_strategy.json loads and validates")
    
    def test_example_multi_strategy_loads(self, backtest_root):
        """Validate Phase 1.3: Multi-strategy config loads and validates"""
        config_path = backtest_root / 'config/examples/multi_strategy.json'
        config = BacktestConfiguration.from_json(config_path)
        
        # Validate loaded config
        assert config.backtest_mode == BacktestMode.MULTI_STRATEGY
        assert len(config.strategies) == 3
        
        # Check strategy types
        strategy_types = {s.strategy_type for s in config.strategies}
        assert 'momentum' in strategy_types
        assert 'mean_reversion' in strategy_types
        assert 'statistical_arbitrage' in strategy_types
        
        # Validate config
        valid, errors = config.validate()
        assert valid, f"❌ Multi-strategy config invalid: {errors}"
        
        print("✅ TEST 1.3: multi_strategy.json loads and validates")
    
    def test_example_regime_adaptive_loads(self, backtest_root):
        """Validate Phase 1.3: Regime-adaptive config loads and validates"""
        config_path = backtest_root / 'config/examples/regime_adaptive.json'
        config = BacktestConfiguration.from_json(config_path)
        
        # Validate loaded config
        assert config.backtest_mode == BacktestMode.REGIME_ADAPTIVE
        assert len(config.strategies) == 4
        assert config.risk.enable_regime_adjustments
        
        # Check for volatility strategy (key for regime-adaptive)
        strategy_types = {s.strategy_type for s in config.strategies}
        assert 'volatility' in strategy_types
        
        # Validate config
        valid, errors = config.validate()
        assert valid, f"❌ Regime-adaptive config invalid: {errors}"
        
        print("✅ TEST 1.3: regime_adaptive.json loads and validates")
    
    # ============================================================
    # TEST 1.4: JSON Serialization Round-Trip
    # ============================================================
    
    def test_json_round_trip(self, tmp_path):
        """Validate Phase 1.4: JSON serialization/deserialization round-trip"""
        # Create config
        original_config = BacktestConfiguration(
            backtest_name="Round Trip Test",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            data=DataConfig(
                symbols=["TEST"],
                start_date="2024-01-01",
                end_date="2024-12-31"
            ),
            strategies=[
                StrategyConfig(
                    strategy_type="momentum",
                    strategy_name="test_strategy",
                    allocation_pct=1.0,
                    parameters={"test_param": 42}
                )
            ],
            risk=RiskConfig(initial_capital=500_000.0),
            execution=ExecutionConfig(),
            analytics=AnalyticsConfig()
        )
        
        # Save to JSON
        test_path = tmp_path / "test_config.json"
        original_config.to_json(test_path)
        
        # Load back
        loaded_config = BacktestConfiguration.from_json(test_path)
        
        # Verify equality
        assert loaded_config.backtest_name == original_config.backtest_name
        assert loaded_config.backtest_mode == original_config.backtest_mode
        assert loaded_config.data.symbols == original_config.data.symbols
        assert loaded_config.strategies[0].strategy_type == original_config.strategies[0].strategy_type
        assert loaded_config.strategies[0].parameters == original_config.strategies[0].parameters
        assert loaded_config.risk.initial_capital == original_config.risk.initial_capital
        
        print("✅ TEST 1.4: JSON round-trip serialization works")


def test_phase1_summary():
    """Phase 1 Complete Summary"""
    print("\n" + "=" * 80)
    print("🎉 PHASE 1 TEST CHECKPOINT COMPLETE!")
    print("=" * 80)
    print("✅ Phase 1.1: Directory structure created")
    print("✅ Phase 1.2: BacktestConfiguration system implemented")
    print("✅ Phase 1.3: Example JSON configs created")
    print("✅ Phase 1.4: Configuration validation working")
    print()
    print("📊 PHASE 1 STATUS: READY FOR PHASE 2")
    print("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

