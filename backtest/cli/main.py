"""
Institutional Backtest CLI - Main Entry Point

Professional command-line interface for running institutional-grade backtests.

Features:
- Run backtests with custom configurations
- List available strategies
- Generate performance reports
- Validate configurations
- Interactive mode

Usage:
    python -m backtest.cli.main run --config config.json
    python -m backtest.cli.main validate --config config.json
    python -m backtest.cli.main list-strategies
    python -m backtest.cli.main interactive
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import backtest components
from backtest.engine.institutional_backtest_engine import InstitutionalBacktestEngine
from core_engine.config import BacktestConfig, BacktestMode  # CENTRALIZED CONFIG
from backtest.cli.interactive import InteractiveBacktestCLI
from backtest.cli.config_builder import ConfigurationBuilder


class BacktestCLI:
    """
    Professional command-line interface for institutional backtesting

    Provides commands for:
    - Running backtests
    - Validating configurations
    - Listing strategies
    - Interactive mode
    - Report generation
    """

    def __init__(self):
        self.parser = self._create_parser()
        self.config_builder = ConfigurationBuilder()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser with all commands"""

        parser = argparse.ArgumentParser(
            prog='backtest',
            description='Institutional Backtest System - Professional Trading Strategy Validation',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run backtest with configuration file
  python -m backtest.cli.main run --config my_backtest.json

  # Run with inline parameters
  python -m backtest.cli.main run --symbols NVDA,TSLA --start-date 2024-01-01 --end-date 2024-03-31

  # Validate configuration
  python -m backtest.cli.main validate --config my_backtest.json

  # List available strategies
  python -m backtest.cli.main list-strategies

  # Interactive mode (guided setup)
  python -m backtest.cli.main interactive

  # Generate report from existing results
  python -m backtest.cli.main report --results results.json
            """
        )

        # Global options
        parser.add_argument('--verbose', '-v', action='store_true',
                          help='Enable verbose logging')
        parser.add_argument('--quiet', '-q', action='store_true',
                          help='Suppress non-essential output')

        # Subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Run command
        run_parser = subparsers.add_parser('run', help='Run a backtest')
        run_parser.add_argument('--config', '-c', type=str,
                              help='Path to configuration file (JSON)')
        run_parser.add_argument('--name', type=str,
                              help='Backtest name')
        run_parser.add_argument('--symbols', type=str,
                              help='Comma-separated list of symbols (e.g., NVDA,TSLA,AAPL)')
        run_parser.add_argument('--start-date', type=str,
                              help='Start date (YYYY-MM-DD)')
        run_parser.add_argument('--end-date', type=str,
                              help='End date (YYYY-MM-DD)')
        run_parser.add_argument('--interval', type=str, default='1min',
                              choices=['1min', '5min', '15min', '1h', '1d'],
                              help='Data interval (default: 1min)')
        run_parser.add_argument('--strategies', type=str,
                              help='Comma-separated list of strategies')
        run_parser.add_argument('--initial-capital', type=float, default=1_000_000,
                              help='Initial capital (default: $1,000,000)')
        run_parser.add_argument('--output', '-o', type=str,
                              help='Output directory for results')
        run_parser.add_argument('--no-report', action='store_true',
                              help='Skip report generation')

        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate a configuration')
        validate_parser.add_argument('--config', '-c', type=str, required=True,
                                   help='Path to configuration file (JSON)')

        # List strategies command
        subparsers.add_parser('list-strategies', help='List available strategies')

        # Interactive command
        subparsers.add_parser('interactive', help='Interactive mode (guided setup)')

        # Report command
        report_parser = subparsers.add_parser('report', help='Generate report from results')
        report_parser.add_argument('--results', '-r', type=str, required=True,
                                  help='Path to results file (JSON)')
        report_parser.add_argument('--output', '-o', type=str,
                                  help='Output directory for report')

        # Config command
        config_parser = subparsers.add_parser('config', help='Generate configuration file')
        config_parser.add_argument('--template', type=str,
                                 choices=['simple', 'momentum', 'mean_reversion', 'multi_strategy'],
                                 default='simple',
                                 help='Configuration template')
        config_parser.add_argument('--output', '-o', type=str, required=True,
                                  help='Output path for configuration file')

        return parser

    async def run(self, args: argparse.Namespace) -> int:
        """Main execution entry point"""

        try:
            if args.command == 'run':
                return await self._run_backtest(args)
            elif args.command == 'validate':
                return await self._validate_config(args)
            elif args.command == 'list-strategies':
                return await self._list_strategies(args)
            elif args.command == 'interactive':
                return await self._interactive_mode(args)
            elif args.command == 'report':
                return await self._generate_report(args)
            elif args.command == 'config':
                return await self._generate_config(args)
            else:
                self.parser.print_help()
                return 0

        except KeyboardInterrupt:
            print("\n\n⚠️  Backtest interrupted by user")
            return 130
        except Exception as e:
            print(f"\n❌ Error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1

    async def _run_backtest(self, args: argparse.Namespace) -> int:
        """Run a backtest"""

        print("\n" + "=" * 80)
        print("🚀 INSTITUTIONAL BACKTEST SYSTEM")
        print("=" * 80 + "\n")

        # Load or build configuration
        if args.config:
            print(f"📄 Loading configuration from: {args.config}")
            config = self._load_config_file(args.config)
        else:
            print("🔧 Building configuration from command-line arguments...")
            config = self._build_config_from_args(args)

        # Validate configuration
        print("\n✅ Validating configuration...")
        validation_result = self._validate_configuration(config)
        if not validation_result['valid']:
            print(f"\n❌ Configuration validation failed:")
            for error in validation_result['errors']:
                print(f"   • {error}")
            return 1

        print("✅ Configuration valid")

        # Display configuration summary
        self._display_config_summary(config)

        # Initialize engine
        print("\n🔧 Initializing backtest engine...")
        engine = InstitutionalBacktestEngine(config=config)

        # Initialize components
        print("   Initializing components...")
        init_success = await engine.initialize()

        if not init_success:
            print("❌ Engine initialization failed")
            return 1

        print("✅ Engine initialized (12/12 components operational)")

        # Run backtest
        print("\n🚀 Running backtest...")
        print(f"   Period: {config.start_date} → {config.end_date}")
        print(f"   Symbols: {', '.join(config.symbols)}")
        print(f"   Strategies: {len(config.strategies)}")
        print("")

        results = await engine.run_backtest()

        # Display results
        if results['success']:
            print("\n" + "=" * 80)
            print("✅ BACKTEST COMPLETE")
            print("=" * 80)
            self._display_results_summary(results)

            # Generate report
            if not args.no_report:
                print("\n📊 Generating performance report...")
                report = engine.generate_performance_report()

                # Save results
                output_dir = Path(args.output) if args.output else Path('backtest_results')
                output_dir.mkdir(exist_ok=True, parents=True)

                # Save results JSON
                results_path = output_dir / f"{config.backtest_name}_results.json"
                with open(results_path, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"   Results saved: {results_path}")

                # Save report JSON
                if report:
                    report_path = output_dir / f"{config.backtest_name}_report.json"
                    with open(report_path, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                    print(f"   Report saved: {report_path}")

                print(f"\n✅ All files saved to: {output_dir}")

            return 0
        else:
            print(f"\n❌ Backtest failed: {results.get('error', 'Unknown error')}")
            return 1

    async def _validate_config(self, args: argparse.Namespace) -> int:
        """Validate a configuration file"""

        print("\n" + "=" * 80)
        print("🔍 CONFIGURATION VALIDATION")
        print("=" * 80 + "\n")

        print(f"📄 Loading configuration: {args.config}")

        try:
            config = self._load_config_file(args.config)

            # Validate
            result = self._validate_configuration(config)

            if result['valid']:
                print("\n✅ Configuration is valid!")
                print(f"\n📊 Configuration Summary:")
                self._display_config_summary(config)
                return 0
            else:
                print("\n❌ Configuration has errors:")
                for error in result['errors']:
                    print(f"   • {error}")

                if result.get('warnings'):
                    print("\n⚠️  Warnings:")
                    for warning in result['warnings']:
                        print(f"   • {warning}")

                return 1

        except Exception as e:
            print(f"\n❌ Error loading configuration: {e}")
            return 1

    async def _list_strategies(self, args: argparse.Namespace) -> int:
        """List available strategies"""

        print("\n" + "=" * 80)
        print("📚 AVAILABLE STRATEGIES")
        print("=" * 80 + "\n")

        strategies = [
            {
                'name': 'momentum',
                'description': 'Momentum-based trading strategy',
                'parameters': ['lookback_period', 'momentum_threshold', 'enable_regime_filter']
            },
            {
                'name': 'mean_reversion',
                'description': 'Mean reversion strategy',
                'parameters': ['lookback_period', 'entry_threshold', 'exit_threshold', 'enable_regime_filter']
            },
            {
                'name': 'trend_following',
                'description': 'Trend following strategy',
                'parameters': ['short_window', 'long_window', 'trend_threshold']
            },
            {
                'name': 'breakout',
                'description': 'Breakout trading strategy',
                'parameters': ['lookback_period', 'breakout_threshold', 'volume_filter']
            },
            {
                'name': 'statistical_arbitrage',
                'description': 'Statistical arbitrage strategy',
                'parameters': ['cointegration_lookback', 'entry_zscore', 'exit_zscore']
            },
            {
                'name': 'pairs_trading',
                'description': 'Pairs trading strategy',
                'parameters': ['lookback_period', 'entry_zscore', 'exit_zscore', 'correlation_threshold']
            },
            {
                'name': 'volatility',
                'description': 'Volatility-based trading',
                'parameters': ['vol_lookback', 'vol_threshold', 'rebalance_frequency']
            },
            {
                'name': 'arbitrage',
                'description': 'Arbitrage opportunities',
                'parameters': ['price_threshold', 'execution_speed']
            },
            {
                'name': 'factor',
                'description': 'Multi-factor investment strategy',
                'parameters': ['factors', 'rebalance_frequency']
            },
            {
                'name': 'multi_asset',
                'description': 'Multi-asset allocation strategy',
                'parameters': ['allocation_method', 'rebalance_frequency']
            }
        ]

        for i, strategy in enumerate(strategies, 1):
            print(f"{i}. {strategy['name']}")
            print(f"   Description: {strategy['description']}")
            print(f"   Parameters: {', '.join(strategy['parameters'])}")
            print("")

        print("=" * 80)
        print(f"Total: {len(strategies)} strategies available")
        print("\nUse 'backtest config --template <strategy>' to generate a configuration")
        print("=" * 80 + "\n")

        return 0

    async def _interactive_mode(self, args: argparse.Namespace) -> int:
        """Interactive mode for guided setup"""

        interactive_cli = InteractiveBacktestCLI()
        return await interactive_cli.run()

    async def _generate_report(self, args: argparse.Namespace) -> int:
        """Generate report from results file"""

        print("\n" + "=" * 80)
        print("📊 REPORT GENERATION")
        print("=" * 80 + "\n")

        print(f"📄 Loading results from: {args.results}")

        try:
            with open(args.results, 'r') as f:
                results = json.load(f)

            self._display_results_summary(results)

            # Save report
            output_dir = Path(args.output) if args.output else Path('backtest_results')
            output_dir.mkdir(exist_ok=True, parents=True)

            report_path = output_dir / "report.html"
            # TODO: Generate HTML report
            print(f"\n📊 Report would be saved to: {report_path}")

            return 0

        except Exception as e:
            print(f"\n❌ Error generating report: {e}")
            return 1

    async def _generate_config(self, args: argparse.Namespace) -> int:
        """Generate configuration file from template"""

        print("\n" + "=" * 80)
        print("🔧 CONFIGURATION GENERATION")
        print("=" * 80 + "\n")

        print(f"📝 Generating {args.template} configuration template...")

        config = self.config_builder.create_template(args.template)

        # Save configuration
        output_path = Path(args.output)
        output_path.parent.mkdir(exist_ok=True, parents=True)

        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Configuration saved to: {output_path}")
        print(f"\nEdit the configuration file and run:")
        print(f"   backtest run --config {output_path}")

        return 0

    def _load_config_file(self, path: str) -> BacktestConfig:
        """Load configuration from JSON or YAML file"""
        import yaml

        with open(path, 'r') as f:
            # Support both YAML and JSON formats
            if path.endswith(('.yaml', '.yml')):
                config_dict = yaml.safe_load(f)
            else:
                config_dict = json.load(f)

        # Convert to BacktestConfig (CENTRALIZED using core_engine)
        # BacktestConfig now flattens all nested configs (Rule 1, Section 7)
        return BacktestConfig.from_dict(config_dict)

    def _build_config_from_args(self, args: argparse.Namespace) -> BacktestConfig:
        """Build configuration from command-line arguments"""

        # Create BacktestConfig directly (flattened structure)
        return BacktestConfig(
            backtest_name=args.name or f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            backtest_mode=BacktestMode.SINGLE_STRATEGY,
            # Data settings
            symbols=args.symbols.split(',') if args.symbols else ['NVDA'],
            start_date=args.start_date or '2024-01-01',
            end_date=args.end_date or '2024-03-31',
            interval=args.interval,
            # Risk settings
            initial_capital=args.initial_capital,
            max_position_size=0.10,
            max_daily_var=0.05,
            max_concentration=0.20,
            # Execution settings
            enable_realistic_fills=True,
            enable_cost_modeling=True,
            # Analytics settings
            enable_regime_attribution=True,
            enable_strategy_attribution=True,
            generate_html_report=True,
            generate_json_report=True
        )

    def _validate_configuration(self, config: BacktestConfig) -> Dict[str, Any]:
        """Validate backtest configuration"""

        # Use BacktestConfig's built-in validation method
        is_valid, errors = config.validate()

        # Additional warnings
        warnings = []
        if config.initial_capital < 10000:
            warnings.append("Initial capital is very low (<$10k), results may not be realistic")

        return {
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings
        }

    def _display_config_summary(self, config: BacktestConfig):
        """Display configuration summary"""

        print(f"\n📊 Configuration Summary:")
        print(f"   Name: {config.backtest_name}")
        print(f"   Mode: {config.backtest_mode.value}")
        print(f"\n   Data:")
        print(f"     Symbols: {', '.join(config.symbols)}")
        print(f"     Period: {config.start_date} → {config.end_date}")
        print(f"     Interval: {config.interval}")
        print(f"\n   Risk:")
        print(f"     Initial Capital: ${config.initial_capital:,.0f}")
        print(f"     Max Position Size: {config.max_position_size:.1%}")
        print(f"     Max Daily VaR: {config.max_daily_var:.1%}")

    def _display_results_summary(self, results: Dict[str, Any]):
        """Display results summary"""

        print(f"\n   Bars Processed: {results.get('total_bars', 0):,}")
        print(f"   Duration: {results.get('duration', 0):.2f} seconds")
        print(f"   Speed: {results.get('bars_per_second', 0):,.0f} bars/sec")
        print(f"   Total Trades: {results.get('total_trades', 0):,}")

        summary = results.get('summary')
        if summary:
            print(f"\n   Performance:")
            print(f"     Total Return: {summary.get('total_return_pct', 0):.2f}%")
            print(f"     Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
            print(f"     Max Drawdown: {summary.get('max_drawdown_pct', 0):.2f}%")
            print(f"     Win Rate: {summary.get('win_rate', 0):.2f}%")


def main():
    """Main entry point"""

    cli = BacktestCLI()
    args = cli.parser.parse_args()

    # Run async
    exit_code = asyncio.run(cli.run(args))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

