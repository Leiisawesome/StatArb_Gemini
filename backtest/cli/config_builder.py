"""
Configuration Builder - Template Generation

Provides pre-configured templates for common backtest scenarios.
"""

from typing import Dict, Any
from datetime import datetime, timedelta

class ConfigurationBuilder:
    """
    Build backtest configurations from templates

    Provides ready-to-use configuration templates for common scenarios:
    - Simple single-strategy backtest
    - Momentum strategy
    - Mean reversion strategy
    - Multi-strategy portfolio
    """

    def create_template(self, template_name: str) -> Dict[str, Any]:
        """Create configuration from template"""

        templates = {
            'simple': self._simple_template,
            'momentum': self._momentum_template,
            'mean_reversion': self._mean_reversion_template,
            'multi_strategy': self._multi_strategy_template
        }

        template_func = templates.get(template_name)
        if not template_func:
            raise ValueError(f"Unknown template: {template_name}")

        return template_func()

    def _simple_template(self) -> Dict[str, Any]:
        """Simple single-strategy backtest"""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 3 months

        return {
            'backtest_name': 'simple_backtest',
            'backtest_mode': 'historical',
            'data': {
                'symbols': ['NVDA'],
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'interval': '1min'
            },
            'strategies': [
                {
                    'strategy_type': 'momentum',
                    'strategy_name': 'simple_momentum',
                    'allocation_pct': 1.0,
                    'max_position_size': 0.10,
                    'parameters': {
                        'lookback_period': 20,
                        'momentum_threshold': 0.02,
                        'enable_regime_filter': True
                    }
                }
            ],
            'risk': {
                'initial_capital': 1_000_000.0,
                'max_position_size': 0.10,
                'max_daily_var': 0.05,
                'max_concentration': 0.20
            },
            'execution': {
                'enable_realistic_fills': True,
                'enable_cost_modeling': True,
                'apply_slippage': True,
                'apply_market_impact': True
            },
            'analytics': {
                'enable_regime_attribution': True,
                'enable_strategy_attribution': True,
                'generate_html_report': True,
                'generate_json_report': True
            }
        }

    def _momentum_template(self) -> Dict[str, Any]:
        """Momentum strategy template"""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 6 months

        return {
            'backtest_name': 'momentum_backtest',
            'backtest_mode': 'historical',
            'data': {
                'symbols': ['NVDA', 'TSLA', 'AAPL'],
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'interval': '5min'
            },
            'strategies': [
                {
                    'strategy_type': 'momentum',
                    'strategy_name': 'momentum_strategy',
                    'allocation_pct': 1.0,
                    'max_position_size': 0.08,
                    'parameters': {
                        'lookback_period': 20,
                        'momentum_threshold': 0.02,
                        'enable_regime_filter': True,
                        'min_adx': 25.0,
                        'volume_factor': 1.5
                    }
                }
            ],
            'risk': {
                'initial_capital': 500000.0,
                'max_position_size': 0.10,
                'max_daily_var': 0.05,
                'max_concentration': 0.15
            },
            'execution': {
                'enable_realistic_fills': True,
                'enable_cost_modeling': True,
                'apply_slippage': True,
                'apply_market_impact': True,
                'enable_liquidity_filtering': True
            },
            'analytics': {
                'enable_regime_attribution': True,
                'enable_strategy_attribution': True,
                'generate_html_report': True,
                'generate_json_report': True,
                'generate_csv_trades': True
            }
        }

    def _mean_reversion_template(self) -> Dict[str, Any]:
        """Mean reversion strategy template"""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # 3 months

        return {
            'backtest_name': 'mean_reversion_backtest',
            'backtest_mode': 'historical',
            'data': {
                'symbols': ['NVDA', 'AMD', 'INTC'],
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'interval': '1min'
            },
            'strategies': [
                {
                    'strategy_type': 'mean_reversion',
                    'strategy_name': 'mean_reversion_strategy',
                    'allocation_pct': 1.0,
                    'max_position_size': 0.08,
                    'parameters': {
                        'lookback_period': 10,
                        'entry_threshold': 2.0,  # Z-score
                        'exit_threshold': 0.5,   # Z-score
                        'enable_regime_filter': True
                    }
                }
            ],
            'risk': {
                'initial_capital': 250000.0,
                'max_position_size': 0.10,
                'max_daily_var': 0.04,
                'max_concentration': 0.20
            },
            'execution': {
                'enable_realistic_fills': True,
                'enable_cost_modeling': True,
                'apply_slippage': True,
                'apply_market_impact': True
            },
            'analytics': {
                'enable_regime_attribution': True,
                'enable_strategy_attribution': True,
                'generate_html_report': True,
                'generate_json_report': True
            }
        }

    def _multi_strategy_template(self) -> Dict[str, Any]:
        """Multi-strategy portfolio template"""

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 6 months

        return {
            'backtest_name': 'multi_strategy_backtest',
            'backtest_mode': 'historical',
            'data': {
                'symbols': ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL'],
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'interval': '5min'
            },
            'strategies': [
                {
                    'strategy_type': 'momentum',
                    'strategy_name': 'momentum_strategy',
                    'allocation_pct': 0.40,  # 40%
                    'max_position_size': 0.08,
                    'parameters': {
                        'lookback_period': 20,
                        'momentum_threshold': 0.02,
                        'enable_regime_filter': True
                    }
                },
                {
                    'strategy_type': 'mean_reversion',
                    'strategy_name': 'mean_reversion_strategy',
                    'allocation_pct': 0.30,  # 30%
                    'max_position_size': 0.08,
                    'parameters': {
                        'lookback_period': 10,
                        'entry_threshold': 2.0,
                        'exit_threshold': 0.5,
                        'enable_regime_filter': True
                    }
                },
                {
                    'strategy_type': 'trend_following',
                    'strategy_name': 'trend_strategy',
                    'allocation_pct': 0.30,  # 30%
                    'max_position_size': 0.08,
                    'parameters': {
                        'short_window': 10,
                        'long_window': 30,
                        'trend_threshold': 0.015
                    }
                }
            ],
            'risk': {
                'initial_capital': 1000000.0,
                'max_position_size': 0.10,
                'max_daily_var': 0.05,
                'max_concentration': 0.15
            },
            'execution': {
                'enable_realistic_fills': True,
                'enable_cost_modeling': True,
                'apply_slippage': True,
                'apply_market_impact': True,
                'enable_liquidity_filtering': True
            },
            'analytics': {
                'enable_regime_attribution': True,
                'enable_strategy_attribution': True,
                'generate_html_report': True,
                'generate_json_report': True,
                'generate_csv_trades': True
            }
        }

