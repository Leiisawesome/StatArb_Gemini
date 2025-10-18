"""
Phase 8.4: CLI Test Checkpoint

Comprehensive validation of CLI functionality:
- CLI command parsing
- Configuration validation
- Template generation
- Help system
- Error handling
- Example scripts

This test validates that all CLI components work correctly
before considering Phase 8 complete.
"""

import pytest
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import argparse

# Add backtest to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.cli.main import BacktestCLI
from backtest.cli.interactive import InteractiveBacktestCLI
from backtest.cli.config_builder import ConfigurationBuilder


class TestPhase84CLIValidation:
    """
    Comprehensive CLI validation tests
    
    Validates all CLI functionality before Phase 8 completion:
    - Command parsing
    - Configuration handling
    - Template generation
    - Error handling
    """
    
    @pytest.fixture
    def cli(self):
        """Create CLI instance"""
        return BacktestCLI()
    
    @pytest.fixture
    def config_builder(self):
        """Create configuration builder"""
        return ConfigurationBuilder()
    
    @pytest.mark.asyncio
    async def test_cli_initialization(self, cli):
        """Test CLI initializes correctly"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: CLI Initialization")
        print("=" * 80 + "\n")
        
        # Verify CLI has parser
        assert cli.parser is not None, "CLI parser not initialized"
        print("✅ CLI parser initialized")
        
        # Verify config builder exists
        assert cli.config_builder is not None, "Config builder not initialized"
        print("✅ Config builder initialized")
        
        print("\n✅ CLI initialization test passed")
    
    @pytest.mark.asyncio
    async def test_cli_commands_available(self, cli):
        """Test all CLI commands are available"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: CLI Commands Available")
        print("=" * 80 + "\n")
        
        # Test that parser has all expected commands
        commands = ['run', 'validate', 'list-strategies', 'interactive', 'report', 'config']
        
        # Get available subcommands from parser
        subparsers_actions = [
            action for action in cli.parser._subparsers._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        
        # Should have exactly one subparser action
        assert len(subparsers_actions) == 1, "Expected exactly one subparser action"
        
        subparser_action = subparsers_actions[0]
        available_commands = list(subparser_action.choices.keys())
        
        print(f"Available commands: {', '.join(available_commands)}")
        
        # Verify all expected commands are present
        for command in commands:
            assert command in available_commands, f"Command '{command}' not found"
            print(f"✅ Command '{command}' available")
        
        print(f"\n✅ All {len(commands)} commands available")
    
    @pytest.mark.asyncio
    async def test_config_templates_generation(self, config_builder):
        """Test configuration template generation"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Configuration Template Generation")
        print("=" * 80 + "\n")
        
        templates = ['simple', 'momentum', 'mean_reversion', 'multi_strategy']
        
        for template_name in templates:
            print(f"\n📋 Testing template: {template_name}")
            
            # Generate template
            config = config_builder.create_template(template_name)
            
            # Validate structure
            assert 'backtest_name' in config, f"{template_name}: Missing backtest_name"
            assert 'backtest_mode' in config, f"{template_name}: Missing backtest_mode"
            assert 'data' in config, f"{template_name}: Missing data section"
            assert 'strategies' in config, f"{template_name}: Missing strategies"
            assert 'risk' in config, f"{template_name}: Missing risk section"
            assert 'execution' in config, f"{template_name}: Missing execution section"
            assert 'analytics' in config, f"{template_name}: Missing analytics section"
            
            # Validate data section
            assert 'symbols' in config['data'], f"{template_name}: Missing symbols"
            assert 'start_date' in config['data'], f"{template_name}: Missing start_date"
            assert 'end_date' in config['data'], f"{template_name}: Missing end_date"
            assert len(config['data']['symbols']) > 0, f"{template_name}: No symbols"
            
            # Validate strategies
            assert len(config['strategies']) > 0, f"{template_name}: No strategies"
            
            # Validate allocations sum to 1.0
            total_allocation = sum(s['allocation_pct'] for s in config['strategies'])
            assert abs(total_allocation - 1.0) < 0.01, f"{template_name}: Allocations don't sum to 1.0"
            
            print(f"   ✅ Template structure valid")
            print(f"   ✅ {len(config['data']['symbols'])} symbols")
            print(f"   ✅ {len(config['strategies'])} strategies")
            print(f"   ✅ Allocations: {total_allocation:.1%}")
        
        print(f"\n✅ All {len(templates)} templates generated successfully")
    
    @pytest.mark.asyncio
    async def test_config_validation_logic(self, cli):
        """Test configuration validation logic"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Configuration Validation Logic")
        print("=" * 80 + "\n")
        
        from backtest.config.backtest_config import (
            BacktestConfiguration,
            DataConfig,
            StrategyConfig,
            RiskConfig,
            ExecutionConfig,
            AnalyticsConfig
        )
        
        # Test 1: Valid configuration
        print("\n📋 Test 1: Valid Configuration")
        valid_config = BacktestConfiguration(
            backtest_name="test_config",
            backtest_mode="historical",
            data=DataConfig(
                symbols=['NVDA'],
                start_date='2024-01-01',
                end_date='2024-03-31',
                interval='1min'
            ),
            strategies=[
                StrategyConfig(
                    strategy_type='momentum',
                    strategy_name='test_momentum',
                    allocation_pct=1.0,
                    max_position_size=0.10
                )
            ],
            risk=RiskConfig(
                initial_capital=100_000.0,
                max_position_size=0.10,
                max_daily_var=0.05,
                max_concentration=0.20
            ),
            execution=ExecutionConfig(
                enable_realistic_fills=True,
                enable_cost_modeling=True
            ),
            analytics=AnalyticsConfig(
                enable_regime_attribution=True,
                generate_html_report=True
            )
        )
        
        result = cli._validate_configuration(valid_config)
        assert result['valid'] == True, "Valid config marked as invalid"
        assert len(result['errors']) == 0, f"Valid config has errors: {result['errors']}"
        print("   ✅ Valid configuration accepted")
        
        # Test 2: Invalid configuration (no symbols)
        print("\n📋 Test 2: Invalid Configuration (no symbols)")
        invalid_config = BacktestConfiguration(
            backtest_name="test_invalid",
            backtest_mode="historical",
            data=DataConfig(
                symbols=[],  # Invalid: no symbols
                start_date='2024-01-01',
                end_date='2024-03-31',
                interval='1min'
            ),
            strategies=[
                StrategyConfig(
                    strategy_type='momentum',
                    strategy_name='test',
                    allocation_pct=1.0,
                    max_position_size=0.10
                )
            ],
            risk=RiskConfig(
                initial_capital=100_000.0,
                max_position_size=0.10,
                max_daily_var=0.05,
                max_concentration=0.20
            ),
            execution=ExecutionConfig(),
            analytics=AnalyticsConfig()
        )
        
        result = cli._validate_configuration(invalid_config)
        assert result['valid'] == False, "Invalid config marked as valid"
        assert len(result['errors']) > 0, "Invalid config has no errors"
        print(f"   ✅ Invalid configuration rejected: {result['errors'][0]}")
        
        # Test 3: Invalid configuration (no strategies)
        print("\n📋 Test 3: Invalid Configuration (no strategies)")
        no_strategy_config = BacktestConfiguration(
            backtest_name="test_no_strategy",
            backtest_mode="historical",
            data=DataConfig(
                symbols=['NVDA'],
                start_date='2024-01-01',
                end_date='2024-03-31',
                interval='1min'
            ),
            strategies=[],  # Invalid: no strategies
            risk=RiskConfig(
                initial_capital=100_000.0,
                max_position_size=0.10,
                max_daily_var=0.05,
                max_concentration=0.20
            ),
            execution=ExecutionConfig(),
            analytics=AnalyticsConfig()
        )
        
        result = cli._validate_configuration(no_strategy_config)
        assert result['valid'] == False, "Config with no strategies marked as valid"
        print(f"   ✅ No-strategy configuration rejected: {result['errors'][0]}")
        
        print("\n✅ Configuration validation logic working correctly")
    
    @pytest.mark.asyncio
    async def test_command_argument_parsing(self, cli):
        """Test command-line argument parsing"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Command Argument Parsing")
        print("=" * 80 + "\n")
        
        # Test 1: Run command with required args
        print("\n📋 Test 1: Run command parsing")
        args = cli.parser.parse_args([
            'run',
            '--symbols', 'NVDA,TSLA',
            '--start-date', '2024-01-01',
            '--end-date', '2024-03-31',
            '--strategies', 'momentum',
            '--initial-capital', '100000'
        ])
        
        assert args.command == 'run', "Command not parsed correctly"
        assert args.symbols == 'NVDA,TSLA', "Symbols not parsed"
        assert args.start_date == '2024-01-01', "Start date not parsed"
        assert args.initial_capital == 100000, "Capital not parsed"
        print("   ✅ Run command arguments parsed correctly")
        
        # Test 2: Validate command
        print("\n📋 Test 2: Validate command parsing")
        args = cli.parser.parse_args([
            'validate',
            '--config', 'test_config.json'
        ])
        
        assert args.command == 'validate', "Validate command not parsed"
        assert args.config == 'test_config.json', "Config path not parsed"
        print("   ✅ Validate command arguments parsed correctly")
        
        # Test 3: Config command
        print("\n📋 Test 3: Config command parsing")
        args = cli.parser.parse_args([
            'config',
            '--template', 'momentum',
            '--output', 'my_config.json'
        ])
        
        assert args.command == 'config', "Config command not parsed"
        assert args.template == 'momentum', "Template not parsed"
        assert args.output == 'my_config.json', "Output not parsed"
        print("   ✅ Config command arguments parsed correctly")
        
        print("\n✅ All command arguments parse correctly")
    
    @pytest.mark.asyncio
    async def test_list_strategies_command(self, cli):
        """Test list-strategies command"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: List Strategies Command")
        print("=" * 80 + "\n")
        
        # Parse command
        args = cli.parser.parse_args(['list-strategies'])
        assert args.command == 'list-strategies'
        
        # Run command (captures output)
        result = await cli._list_strategies(args)
        
        # Should return 0 (success)
        assert result == 0, "List strategies failed"
        print("✅ List strategies command executed successfully")
    
    @pytest.mark.asyncio
    async def test_config_builder_from_args(self, cli):
        """Test building configuration from command-line arguments"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Build Config from Arguments")
        print("=" * 80 + "\n")
        
        # Create mock args
        args = argparse.Namespace(
            name='test_backtest',
            symbols='NVDA,TSLA',
            start_date='2024-01-01',
            end_date='2024-03-31',
            interval='1min',
            strategies='momentum,mean_reversion',
            initial_capital=500000.0
        )
        
        # Build config
        config = cli._build_config_from_args(args)
        
        # Validate
        assert config.backtest_name == 'test_backtest'
        assert len(config.data.symbols) == 2
        assert 'NVDA' in config.data.symbols
        assert 'TSLA' in config.data.symbols
        assert config.data.start_date == '2024-01-01'
        assert config.data.end_date == '2024-03-31'
        assert len(config.strategies) == 2
        assert config.risk.initial_capital == 500000.0
        
        print(f"   ✅ Config created from arguments")
        print(f"   ✅ Symbols: {', '.join(config.data.symbols)}")
        print(f"   ✅ Strategies: {len(config.strategies)}")
        print(f"   ✅ Capital: ${config.risk.initial_capital:,.0f}")
        
        print("\n✅ Configuration built successfully from arguments")
    
    @pytest.mark.asyncio
    async def test_example_scripts_importable(self):
        """Test that example scripts are importable"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Example Scripts Importable")
        print("=" * 80 + "\n")
        
        examples_dir = Path('backtest/examples')
        
        example_files = [
            'simple_momentum_backtest.py',
            'multi_strategy_backtest.py',
            'advanced_regime_aware_backtest.py'
        ]
        
        for example_file in example_files:
            example_path = examples_dir / example_file
            
            # Check file exists
            assert example_path.exists(), f"Example file not found: {example_file}"
            print(f"   ✅ Found: {example_file}")
            
            # Check it's a valid Python file
            with open(example_path, 'r') as f:
                content = f.read()
                assert 'import asyncio' in content, f"{example_file}: Missing asyncio import"
                assert 'InstitutionalBacktestEngine' in content, f"{example_file}: Missing engine import"
                assert 'BacktestConfiguration' in content, f"{example_file}: Missing config import"
                assert 'async def' in content, f"{example_file}: Missing async function"
            
            print(f"   ✅ Valid: {example_file}")
        
        print(f"\n✅ All {len(example_files)} example scripts are valid")
    
    @pytest.mark.asyncio
    async def test_documentation_exists(self):
        """Test that documentation files exist"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: Documentation Exists")
        print("=" * 80 + "\n")
        
        docs = [
            ('User Guide', Path('docs/USER_GUIDE.md')),
            ('Examples README', Path('backtest/examples/README.md'))
        ]
        
        for doc_name, doc_path in docs:
            assert doc_path.exists(), f"Documentation not found: {doc_name}"
            
            # Check file is not empty
            content = doc_path.read_text()
            assert len(content) > 1000, f"{doc_name} is too short (< 1000 chars)"
            
            # Check has proper structure
            assert '# ' in content, f"{doc_name}: Missing headers"
            assert '## ' in content, f"{doc_name}: Missing subheaders"
            
            print(f"   ✅ {doc_name}: {len(content):,} characters")
        
        print(f"\n✅ All documentation files exist and are valid")
    
    @pytest.mark.asyncio
    async def test_cli_help_system(self, cli):
        """Test CLI help system"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: CLI Help System")
        print("=" * 80 + "\n")
        
        # Test that help options are configured
        assert cli.parser.add_help == True, "Help option not enabled"
        print("   ✅ Main help enabled")
        
        # Test command helps by checking subparser configuration
        commands = ['run', 'validate', 'list-strategies', 'config']
        
        # Get subparsers
        subparsers_actions = [
            action for action in cli.parser._subparsers._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        
        if subparsers_actions:
            subparser_action = subparsers_actions[0]
            for command in commands:
                if command in subparser_action.choices:
                    parser = subparser_action.choices[command]
                    assert parser.add_help == True, f"{command} help not enabled"
                    print(f"   ✅ {command} help enabled")
        
        print("\n✅ Help system configured correctly")
    
    @pytest.mark.asyncio
    async def test_cli_error_handling(self, cli):
        """Test CLI error handling"""
        
        print("\n" + "=" * 80)
        print("🧪 TEST: CLI Error Handling")
        print("=" * 80 + "\n")
        
        # Test 1: Invalid command
        print("\n📋 Test 1: Invalid command handling")
        with pytest.raises(SystemExit):
            cli.parser.parse_args(['invalid_command'])
        print("   ✅ Invalid command caught")
        
        # Test 2: Missing required arguments
        print("\n📋 Test 2: Missing required arguments")
        with pytest.raises(SystemExit):
            cli.parser.parse_args(['validate'])  # Missing --config
        print("   ✅ Missing argument caught")
        
        # Test 3: Invalid argument values
        print("\n📋 Test 3: Invalid argument values")
        with pytest.raises(SystemExit):
            cli.parser.parse_args(['run', '--interval', 'invalid_interval'])
        print("   ✅ Invalid argument value caught")
        
        print("\n✅ Error handling working correctly")


# ============================================================
# STANDALONE TEST EXECUTION
# ============================================================

if __name__ == '__main__':
    """Run Phase 8.4 CLI validation tests standalone"""
    
    print("\n" + "=" * 80)
    print("🧪 PHASE 8.4 CLI VALIDATION - STANDALONE EXECUTION")
    print("=" * 80)
    print("Testing: Complete CLI functionality validation")
    print("Purpose: Verify all CLI components work correctly")
    print("=" * 80 + "\n")
    
    # Run pytest
    pytest.main([__file__, '-v', '--tb=short', '-s'])

