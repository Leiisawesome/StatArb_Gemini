"""
Test data scenarios for integration tests.

This module provides predefined test scenarios for different market conditions and load levels.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketScenario:
    """Market scenario configuration."""
    name: str
    volatility: float
    trend: float
    correlation: float
    volume_multiplier: float
    description: str
    expected_signals: int
    expected_executions: int
    risk_level: str  # 'low', 'medium', 'high', 'extreme'


@dataclass
class LoadScenario:
    """Load scenario configuration."""
    name: str
    symbols: int
    signals_per_minute: int
    executions_per_minute: int
    data_points_per_second: int
    description: str
    expected_duration_minutes: int
    resource_intensity: str  # 'low', 'medium', 'high', 'extreme'


@dataclass
class ErrorScenario:
    """Error scenario configuration."""
    name: str
    failure_rate: float
    recovery_time_seconds: int
    affected_components: List[str]
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'


class TestDataScenarios:
    """Manages test data scenarios for integration testing."""
    
    def __init__(self):
        self.market_scenarios = self._create_market_scenarios()
        self.load_scenarios = self._create_load_scenarios()
        self.error_scenarios = self._create_error_scenarios()
    
    def _create_market_scenarios(self) -> Dict[str, MarketScenario]:
        """Create predefined market scenarios."""
        return {
            'normal': MarketScenario(
                name='normal',
                volatility=0.15,
                trend=0.0,
                correlation=0.3,
                volume_multiplier=1.0,
                description='Normal market conditions with moderate volatility',
                expected_signals=50,
                expected_executions=25,
                risk_level='low'
            ),
            'high_volatility': MarketScenario(
                name='high_volatility',
                volatility=0.35,
                trend=0.0,
                correlation=0.5,
                volume_multiplier=1.5,
                description='High volatility market with increased correlation',
                expected_signals=80,
                expected_executions=40,
                risk_level='medium'
            ),
            'trending': MarketScenario(
                name='trending',
                volatility=0.20,
                trend=0.1,
                correlation=0.4,
                volume_multiplier=1.2,
                description='Trending market with directional movement',
                expected_signals=60,
                expected_executions=30,
                risk_level='medium'
            ),
            'crisis': MarketScenario(
                name='crisis',
                volatility=0.50,
                trend=-0.2,
                correlation=0.8,
                volume_multiplier=2.0,
                description='Crisis market with extreme volatility and correlation',
                expected_signals=100,
                expected_executions=50,
                risk_level='extreme'
            )
        }
    
    def _create_load_scenarios(self) -> Dict[str, LoadScenario]:
        """Create predefined load scenarios."""
        return {
            'normal_load': LoadScenario(
                name='normal_load',
                symbols=10,
                signals_per_minute=100,
                executions_per_minute=50,
                data_points_per_second=1000,
                description='Normal system load with moderate activity',
                expected_duration_minutes=30,
                resource_intensity='low'
            ),
            'high_load': LoadScenario(
                name='high_load',
                symbols=50,
                signals_per_minute=500,
                executions_per_minute=250,
                data_points_per_second=5000,
                description='High system load with increased activity',
                expected_duration_minutes=15,
                resource_intensity='medium'
            ),
            'stress_load': LoadScenario(
                name='stress_load',
                symbols=100,
                signals_per_minute=1000,
                executions_per_minute=500,
                data_points_per_second=10000,
                description='Stress test load with maximum activity',
                expected_duration_minutes=10,
                resource_intensity='high'
            ),
            'extreme_load': LoadScenario(
                name='extreme_load',
                symbols=200,
                signals_per_minute=2000,
                executions_per_minute=1000,
                data_points_per_second=20000,
                description='Extreme load test beyond normal capacity',
                expected_duration_minutes=5,
                resource_intensity='extreme'
            )
        }
    
    def _create_error_scenarios(self) -> Dict[str, ErrorScenario]:
        """Create predefined error scenarios."""
        return {
            'component_failure': ErrorScenario(
                name='component_failure',
                failure_rate=0.1,
                recovery_time_seconds=30,
                affected_components=['signal_generator', 'execution_engine'],
                description='Simulated component failures with recovery',
                severity='medium'
            ),
            'network_failure': ErrorScenario(
                name='network_failure',
                failure_rate=0.05,
                recovery_time_seconds=60,
                affected_components=['market_data', 'order_execution'],
                description='Simulated network connectivity issues',
                severity='high'
            ),
            'data_corruption': ErrorScenario(
                name='data_corruption',
                failure_rate=0.01,
                recovery_time_seconds=5,
                affected_components=['data_processor', 'risk_calculator'],
                description='Simulated data corruption and validation failures',
                severity='medium'
            ),
            'system_overload': ErrorScenario(
                name='system_overload',
                failure_rate=0.2,
                recovery_time_seconds=120,
                affected_components=['all'],
                description='Simulated system overload and resource exhaustion',
                severity='critical'
            )
        }
    
    def get_market_scenario(self, scenario_name: str) -> MarketScenario:
        """Get a specific market scenario."""
        if scenario_name not in self.market_scenarios:
            raise ValueError(f"Unknown market scenario: {scenario_name}")
        return self.market_scenarios[scenario_name]
    
    def get_load_scenario(self, scenario_name: str) -> LoadScenario:
        """Get a specific load scenario."""
        if scenario_name not in self.load_scenarios:
            raise ValueError(f"Unknown load scenario: {scenario_name}")
        return self.load_scenarios[scenario_name]
    
    def get_error_scenario(self, scenario_name: str) -> ErrorScenario:
        """Get a specific error scenario."""
        if scenario_name not in self.error_scenarios:
            raise ValueError(f"Unknown error scenario: {scenario_name}")
        return self.error_scenarios[scenario_name]
    
    def list_market_scenarios(self) -> List[str]:
        """List all available market scenarios."""
        return list(self.market_scenarios.keys())
    
    def list_load_scenarios(self) -> List[str]:
        """List all available load scenarios."""
        return list(self.load_scenarios.keys())
    
    def list_error_scenarios(self) -> List[str]:
        """List all available error scenarios."""
        return list(self.error_scenarios.keys())
    
    def get_scenario_summary(self) -> Dict[str, Any]:
        """Get summary of all scenarios."""
        return {
            'market_scenarios': {
                name: {
                    'description': scenario.description,
                    'risk_level': scenario.risk_level,
                    'expected_signals': scenario.expected_signals,
                    'expected_executions': scenario.expected_executions
                }
                for name, scenario in self.market_scenarios.items()
            },
            'load_scenarios': {
                name: {
                    'description': scenario.description,
                    'resource_intensity': scenario.resource_intensity,
                    'expected_duration_minutes': scenario.expected_duration_minutes
                }
                for name, scenario in self.load_scenarios.items()
            },
            'error_scenarios': {
                name: {
                    'description': scenario.description,
                    'severity': scenario.severity,
                    'recovery_time_seconds': scenario.recovery_time_seconds
                }
                for name, scenario in self.error_scenarios.items()
            }
        }


class TestDataGenerator:
    """Generates test data based on scenarios."""
    
    def __init__(self, scenarios: TestDataScenarios = None):
        self.scenarios = scenarios or TestDataScenarios()
    
    def generate_market_data(self, symbols: List[str], scenario_name: str = 'normal',
                           duration: timedelta = timedelta(hours=1)) -> Dict[str, pd.DataFrame]:
        """Generate market data for a specific scenario."""
        scenario = self.scenarios.get_market_scenario(scenario_name)
        
        data = {}
        base_price = 100.0
        
        for symbol in symbols:
            # Generate price data based on scenario parameters
            n_periods = int(duration.total_seconds() / 60)  # 1-minute intervals
            
            # Generate returns with scenario characteristics
            returns = np.random.normal(
                scenario.trend / 252,  # Daily trend
                scenario.volatility / np.sqrt(252),  # Daily volatility
                n_periods
            )
            
            # Add correlation effects
            if scenario.correlation > 0:
                # Simple correlation simulation
                correlated_noise = np.random.normal(0, scenario.correlation * 0.1, n_periods)
                returns += correlated_noise
            
            # Generate price series
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Generate volume data
            volumes = np.random.lognormal(
                mean=10,
                sigma=0.5,
                size=n_periods
            ) * scenario.volume_multiplier
            
            # Create timestamps
            timestamps = pd.date_range(
                start=datetime.now() - duration,
                end=datetime.now(),
                periods=n_periods
            )
            
            # Create DataFrame
            df = pd.DataFrame({
                'timestamp': timestamps,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': volumes
            })
            
            data[symbol] = df
        
        logger.info(f"Generated market data for {len(symbols)} symbols using {scenario_name} scenario")
        return data
    
    def generate_signals(self, symbols: List[str], scenario_name: str = 'normal',
                        count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate trading signals for a specific scenario."""
        scenario = self.scenarios.get_market_scenario(scenario_name)
        
        if count is None:
            count = scenario.expected_signals
        
        signals = []
        for i in range(count):
            signal = {
                'signal_id': f'signal_{i:06d}',
                'symbol': np.random.choice(symbols),
                'timestamp': datetime.now() - timedelta(minutes=np.random.randint(1, 60)),
                'signal_type': np.random.choice(['BUY', 'SELL']),
                'confidence': np.random.uniform(0.5, 1.0),
                'strength': np.random.uniform(0.1, 0.5),
                'source': f'test_generator_{scenario_name}',
                'metadata': {
                    'test_signal': True,
                    'scenario': scenario_name,
                    'risk_level': scenario.risk_level,
                    'batch_id': f'batch_{i//10:03d}'
                }
            }
            signals.append(signal)
        
        logger.info(f"Generated {len(signals)} signals using {scenario_name} scenario")
        return signals
    
    def generate_orders(self, signals: List[Dict[str, Any]], scenario_name: str = 'normal') -> List[Dict[str, Any]]:
        """Generate orders based on signals and scenario."""
        scenario = self.scenarios.get_market_scenario(scenario_name)
        
        orders = []
        for signal in signals:
            # Adjust order size based on scenario risk level
            base_quantity = np.random.uniform(100, 1000)
            if scenario.risk_level == 'high':
                base_quantity *= 0.5  # Reduce size for high risk
            elif scenario.risk_level == 'extreme':
                base_quantity *= 0.25  # Further reduce for extreme risk
            
            order = {
                'order_id': f'order_{signal["signal_id"]}',
                'symbol': signal['symbol'],
                'side': signal['signal_type'],
                'quantity': int(base_quantity),
                'order_type': 'MARKET',
                'timestamp': signal['timestamp'],
                'signal_id': signal['signal_id'],
                'metadata': {
                    'test_order': True,
                    'scenario': scenario_name,
                    'risk_level': scenario.risk_level,
                    'signal_confidence': signal['confidence']
                }
            }
            orders.append(order)
        
        logger.info(f"Generated {len(orders)} orders using {scenario_name} scenario")
        return orders
    
    def generate_load_test_data(self, load_scenario_name: str = 'normal_load') -> Dict[str, Any]:
        """Generate data for load testing."""
        load_scenario = self.scenarios.get_load_scenario(load_scenario_name)
        
        # Generate symbols
        symbols = [f'SYMBOL_{i:03d}' for i in range(load_scenario.symbols)]
        
        # Generate market data
        market_data = self.generate_market_data(symbols, 'normal', timedelta(minutes=load_scenario.expected_duration_minutes))
        
        # Generate signals
        signals = self.generate_signals(symbols, 'normal', load_scenario.signals_per_minute)
        
        # Generate orders
        orders = self.generate_orders(signals, 'normal')
        
        return {
            'scenario': load_scenario_name,
            'symbols': symbols,
            'market_data': market_data,
            'signals': signals,
            'orders': orders,
            'expected_duration_minutes': load_scenario.expected_duration_minutes,
            'resource_intensity': load_scenario.resource_intensity
        }
    
    def generate_error_test_data(self, error_scenario_name: str = 'component_failure') -> Dict[str, Any]:
        """Generate data for error testing."""
        error_scenario = self.scenarios.get_error_scenario(error_scenario_name)
        
        return {
            'scenario': error_scenario_name,
            'failure_rate': error_scenario.failure_rate,
            'recovery_time_seconds': error_scenario.recovery_time_seconds,
            'affected_components': error_scenario.affected_components,
            'severity': error_scenario.severity,
            'description': error_scenario.description
        }


# Global instance for easy access
test_scenarios = TestDataScenarios()
test_data_generator = TestDataGenerator(test_scenarios)


def get_test_scenario(scenario_type: str, scenario_name: str) -> Any:
    """Get a test scenario by type and name."""
    if scenario_type == 'market':
        return test_scenarios.get_market_scenario(scenario_name)
    elif scenario_type == 'load':
        return test_scenarios.get_load_scenario(scenario_name)
    elif scenario_type == 'error':
        return test_scenarios.get_error_scenario(scenario_name)
    else:
        raise ValueError(f"Unknown scenario type: {scenario_type}")


def generate_test_data(scenario_type: str, scenario_name: str, **kwargs) -> Dict[str, Any]:
    """Generate test data for a specific scenario."""
    if scenario_type == 'market':
        return test_data_generator.generate_market_data(**kwargs)
    elif scenario_type == 'load':
        return test_data_generator.generate_load_test_data(scenario_name)
    elif scenario_type == 'error':
        return test_data_generator.generate_error_test_data(scenario_name)
    else:
        raise ValueError(f"Unknown scenario type: {scenario_type}")


if __name__ == "__main__":
    # Print scenario summary
    summary = test_scenarios.get_scenario_summary()
    import json
    print(json.dumps(summary, indent=2, default=str)) 