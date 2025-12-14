"""
Interactive Backtest CLI - Guided Setup

Provides an interactive, user-friendly interface for configuring and running backtests
without requiring knowledge of configuration files or command-line arguments.
"""

from datetime import datetime, timedelta
from typing import List, Optional

class InteractiveBacktestCLI:
    """
    Interactive command-line interface with guided setup

    Walks user through backtest configuration step-by-step with
    sensible defaults and validation.
    """

    def __init__(self):
        self.config = {}

    async def run(self) -> int:
        """Run interactive mode"""

        print("\n" + "=" * 80)
        print("🎯 INTERACTIVE BACKTEST CONFIGURATION")
        print("=" * 80)
        print("\nWelcome! I'll help you configure your backtest.")
        print("Press Ctrl+C at any time to cancel.\n")

        try:
            # Step 1: Basic information
            await self._configure_basic_info()

            # Step 2: Data configuration
            await self._configure_data()

            # Step 3: Strategy configuration
            await self._configure_strategies()

            # Step 4: Risk configuration
            await self._configure_risk()

            # Step 5: Execution configuration
            await self._configure_execution()

            # Step 6: Analytics configuration
            await self._configure_analytics()

            # Step 7: Review and confirm
            confirmed = await self._review_and_confirm()

            if confirmed:
                # Save configuration
                config_path = await self._save_configuration()

                # Ask to run now
                run_now = self._prompt_yes_no("\nRun backtest now?", default=True)

                if run_now:
                    print("\n🚀 Starting backtest...")
                    # TODO: Actually run the backtest
                    return 0
                else:
                    print(f"\n✅ Configuration saved to: {config_path}")
                    print(f"Run backtest with: backtest run --config {config_path}")
                    return 0
            else:
                print("\n❌ Configuration cancelled")
                return 1

        except KeyboardInterrupt:
            print("\n\n⚠️  Configuration cancelled by user")
            return 130
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return 1

    async def _configure_basic_info(self):
        """Configure basic backtest information"""

        print("\n" + "-" * 80)
        print("📋 BASIC INFORMATION")
        print("-" * 80 + "\n")

        # Backtest name
        default_name = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = self._prompt_string(
            "Backtest name",
            default=default_name,
            help_text="A unique identifier for this backtest"
        )

        self.config['backtest_name'] = name
        self.config['backtest_mode'] = 'historical'

    async def _configure_data(self):
        """Configure data sources"""

        print("\n" + "-" * 80)
        print("📊 DATA CONFIGURATION")
        print("-" * 80 + "\n")

        # Symbols
        symbols_str = self._prompt_string(
            "Symbols (comma-separated)",
            default="NVDA,TSLA,AAPL",
            help_text="Trading symbols to include in backtest"
        )
        symbols = [s.strip().upper() for s in symbols_str.split(',')]

        # Date range
        print("\n📅 Date Range:")

        # Suggest some common ranges
        today = datetime.now()
        suggestions = {
            '1': ('Last month', today - timedelta(days=30), today),
            '2': ('Last 3 months', today - timedelta(days=90), today),
            '3': ('Last 6 months', today - timedelta(days=180), today),
            '4': ('Last year', today - timedelta(days=365), today),
            '5': ('Custom range', None, None)
        }

        print("\nQuick options:")
        for key, (label, _, _) in suggestions.items():
            print(f"   {key}. {label}")

        choice = self._prompt_choice("\nSelect date range", list(suggestions.keys()), default='2')

        if choice == '5':
            start_date = self._prompt_date("Start date (YYYY-MM-DD)", default="2024-01-01")
            end_date = self._prompt_date("End date (YYYY-MM-DD)", default="2024-03-31")
        else:
            _, start_date, end_date = suggestions[choice]
            start_date = start_date.strftime('%Y-%m-%d')
            end_date = end_date.strftime('%Y-%m-%d')
            print(f"   Selected: {start_date} → {end_date}")

        # Interval
        interval = self._prompt_choice(
            "Data interval",
            ['1min', '5min', '15min', '1h', '1d'],
            default='1min',
            help_text="Time interval for each bar"
        )

        self.config['data'] = {
            'symbols': symbols,
            'start_date': start_date,
            'end_date': end_date,
            'interval': interval
        }

    async def _configure_strategies(self):
        """Configure trading strategies"""

        print("\n" + "-" * 80)
        print("🎯 STRATEGY CONFIGURATION")
        print("-" * 80 + "\n")

        strategies = []

        # Available strategies
        available_strategies = {
            '1': 'momentum',
            '2': 'mean_reversion',
            '3': 'trend_following',
            '4': 'breakout',
            '5': 'statistical_arbitrage',
            '6': 'pairs_trading'
        }

        print("Available strategies:")
        for key, name in available_strategies.items():
            print(f"   {key}. {name.replace('_', ' ').title()}")

        # How many strategies?
        num_strategies = self._prompt_integer(
            "\nHow many strategies?",
            min_val=1,
            max_val=5,
            default=2,
            help_text="Number of strategies to combine"
        )

        # Configure each strategy
        for i in range(num_strategies):
            print(f"\n📌 Strategy {i+1}:")

            strategy_choice = self._prompt_choice(
                "  Strategy type",
                list(available_strategies.keys()),
                default='1' if i == 0 else '2'
            )

            strategy_type = available_strategies[strategy_choice]
            strategy_name = f"{strategy_type}_{i+1}"

            allocation = self._prompt_float(
                "  Allocation %",
                min_val=0.0,
                max_val=100.0,
                default=100.0 / num_strategies,
                help_text=f"Percentage of capital allocated (remaining: {100 - sum(s['allocation_pct']*100 for s in strategies):.0f}%)"
            )

            strategies.append({
                'strategy_type': strategy_type,
                'strategy_name': strategy_name,
                'allocation_pct': allocation / 100.0,
                'max_position_size': 0.10
            })

        self.config['strategies'] = strategies

    async def _configure_risk(self):
        """Configure risk parameters"""

        print("\n" + "-" * 80)
        print("⚠️  RISK CONFIGURATION")
        print("-" * 80 + "\n")

        # Initial capital
        capital = self._prompt_float(
            "Initial capital ($)",
            min_val=10000,
            default=1_000_000,
            help_text="Starting portfolio value"
        )

        # Max position size
        max_position = self._prompt_float(
            "Max position size (%)",
            min_val=1.0,
            max_val=50.0,
            default=10.0,
            help_text="Maximum size of any single position"
        )

        # Max daily VaR
        max_var = self._prompt_float(
            "Max daily VaR (%)",
            min_val=0.5,
            max_val=20.0,
            default=5.0,
            help_text="Maximum daily Value at Risk"
        )

        # Max concentration
        max_concentration = self._prompt_float(
            "Max concentration (%)",
            min_val=5.0,
            max_val=50.0,
            default=20.0,
            help_text="Maximum concentration per position"
        )

        self.config['risk'] = {
            'initial_capital': capital,
            'max_position_size': max_position / 100.0,
            'max_daily_var': max_var / 100.0,
            'max_concentration': max_concentration / 100.0
        }

    async def _configure_execution(self):
        """Configure execution parameters"""

        print("\n" + "-" * 80)
        print("⚡ EXECUTION CONFIGURATION")
        print("-" * 80 + "\n")

        # Use realistic execution?
        realistic = self._prompt_yes_no(
            "Enable realistic execution simulation?",
            default=True,
            help_text="Includes spread costs, market impact, and slippage"
        )

        self.config['execution'] = {
            'enable_realistic_fills': realistic,
            'enable_cost_modeling': realistic,
            'apply_slippage': realistic,
            'apply_market_impact': realistic
        }

    async def _configure_analytics(self):
        """Configure analytics and reporting"""

        print("\n" + "-" * 80)
        print("📊 ANALYTICS CONFIGURATION")
        print("-" * 80 + "\n")

        # Generate reports?
        generate_reports = self._prompt_yes_no(
            "Generate performance reports?",
            default=True
        )

        self.config['analytics'] = {
            'enable_regime_attribution': True,
            'enable_strategy_attribution': True,
            'generate_html_report': generate_reports,
            'generate_json_report': generate_reports
        }

    async def _review_and_confirm(self) -> bool:
        """Review configuration and confirm"""

        print("\n" + "=" * 80)
        print("📋 CONFIGURATION REVIEW")
        print("=" * 80)

        # Display summary
        print(f"\n✅ Backtest Name: {self.config['backtest_name']}")
        print(f"\n📊 Data:")
        print(f"   Symbols: {', '.join(self.config['data']['symbols'])}")
        print(f"   Period: {self.config['data']['start_date']} → {self.config['data']['end_date']}")
        print(f"   Interval: {self.config['data']['interval']}")

        print(f"\n🎯 Strategies: {len(self.config['strategies'])}")
        for strategy in self.config['strategies']:
            print(f"   • {strategy['strategy_name']} ({strategy['strategy_type']}): {strategy['allocation_pct']:.1%}")

        print(f"\n⚠️  Risk:")
        print(f"   Initial Capital: ${self.config['risk']['initial_capital']:,.0f}")
        print(f"   Max Position: {self.config['risk']['max_position_size']:.1%}")
        print(f"   Max VaR: {self.config['risk']['max_daily_var']:.1%}")

        print(f"\n⚡ Execution:")
        print(f"   Realistic Fills: {'✅' if self.config['execution']['enable_realistic_fills'] else '❌'}")
        print(f"   Cost Modeling: {'✅' if self.config['execution']['enable_cost_modeling'] else '❌'}")

        print("\n" + "=" * 80)

        return self._prompt_yes_no("\nProceed with this configuration?", default=True)

    async def _save_configuration(self) -> str:
        """Save configuration to file"""

        import json
        from pathlib import Path

        # Default path
        config_dir = Path('backtest_configs')
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / f"{self.config['backtest_name']}.json"

        # Save
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        return str(config_path)

    def _prompt_string(self, prompt: str, default: Optional[str] = None,
                      help_text: Optional[str] = None) -> str:
        """Prompt for string input"""

        if help_text:
            print(f"   ℹ️  {help_text}")

        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input if user_input else default
        else:
            while True:
                user_input = input(f"{prompt}: ").strip()
                if user_input:
                    return user_input
                print("   ⚠️  Required field")

    def _prompt_integer(self, prompt: str, min_val: Optional[int] = None,
                       max_val: Optional[int] = None, default: Optional[int] = None,
                       help_text: Optional[str] = None) -> int:
        """Prompt for integer input"""

        if help_text:
            print(f"   ℹ️  {help_text}")

        while True:
            if default is not None:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()

            try:
                value = int(user_input)

                if min_val is not None and value < min_val:
                    print(f"   ⚠️  Value must be at least {min_val}")
                    continue

                if max_val is not None and value > max_val:
                    print(f"   ⚠️  Value must be at most {max_val}")
                    continue

                return value

            except ValueError:
                print("   ⚠️  Please enter a valid number")

    def _prompt_float(self, prompt: str, min_val: Optional[float] = None,
                     max_val: Optional[float] = None, default: Optional[float] = None,
                     help_text: Optional[str] = None) -> float:
        """Prompt for float input"""

        if help_text:
            print(f"   ℹ️  {help_text}")

        while True:
            if default is not None:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()

            try:
                value = float(user_input)

                if min_val is not None and value < min_val:
                    print(f"   ⚠️  Value must be at least {min_val}")
                    continue

                if max_val is not None and value > max_val:
                    print(f"   ⚠️  Value must be at most {max_val}")
                    continue

                return value

            except ValueError:
                print("   ⚠️  Please enter a valid number")

    def _prompt_date(self, prompt: str, default: Optional[str] = None) -> str:
        """Prompt for date input"""

        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()

            try:
                datetime.strptime(user_input, '%Y-%m-%d')
                return user_input
            except ValueError:
                print("   ⚠️  Invalid date format. Use YYYY-MM-DD")

    def _prompt_choice(self, prompt: str, choices: List[str], default: Optional[str] = None,
                      help_text: Optional[str] = None) -> str:
        """Prompt for choice from list"""

        if help_text:
            print(f"   ℹ️  {help_text}")

        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()

            if user_input in choices:
                return user_input

            print(f"   ⚠️  Invalid choice. Options: {', '.join(choices)}")

    def _prompt_yes_no(self, prompt: str, default: bool = True,
                      help_text: Optional[str] = None) -> bool:
        """Prompt for yes/no confirmation"""

        if help_text:
            print(f"   ℹ️  {help_text}")

        default_str = 'Y/n' if default else 'y/N'

        while True:
            user_input = input(f"{prompt} [{default_str}]: ").strip().lower()

            if not user_input:
                return default

            if user_input in ['y', 'yes']:
                return True
            elif user_input in ['n', 'no']:
                return False
            else:
                print("   ⚠️  Please enter 'y' or 'n'")

