"""
Scenario Validation Tests
========================

Advanced scenario-based testing for complex real-world trading situations.
Tests system behavior under         core_engine = DelegatedCoreEngine(
            strategy_interface=strategy,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=configuration,
            config=CoreEngineConfig()
        )
        ket conditions and edge cases.

Author: Professional Trading System Architecture  
Version: 1.0.0
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import all required components
from trade_engine.interfaces import TradingSignal, SignalType
from trade_engine.core.delegated_core_engine import DelegatedCoreEngine, CoreEngineConfig
from trade_engine.templates.momentum_template import ProfessionalMomentumTemplate
from trade_engine.templates import template_registry
from trade_engine.templates.template_bridge import TemplateStrategyBridge, TemplateConfiguration
from trade_engine.dynamic_adaptation import (
    RealTimeParameterOptimizer, AdaptationConfig, AdaptationMode
)

from .test_phase123_integration import (
    MockMarketDataProvider, IntegrationMockPortfolio, 
    IntegrationMockExecution, IntegrationMockConfiguration
)


class AdvancedMarketDataProvider(MockMarketDataProvider):
    """Advanced market data provider with scenario-specific patterns."""
    
    def __init__(self, scenario_type: str = "normal"):
        super().__init__()
        self.scenario_type = scenario_type
        self.price_history = {}
        
    def get_market_data(self, symbols: List[str], timestamp: datetime) -> Dict[str, Any]:
        """Generate scenario-specific market data."""
        market_data = {}
        
        for symbol in symbols:
            if symbol not in self.price_history:
                self.price_history[symbol] = 100.0 + hash(symbol) % 50
            
            previous_price = self.price_history[symbol]
            
            if self.scenario_type == "trending_up":
                # Strong upward trend with low volatility
                price_change = np.random.normal(0.002, 0.01)  # 0.2% drift, 1% volatility
                
            elif self.scenario_type == "trending_down":
                # Strong downward trend
                price_change = np.random.normal(-0.002, 0.01)  # -0.2% drift, 1% volatility
                
            elif self.scenario_type == "high_volatility":
                # High volatility, no trend
                price_change = np.random.normal(0, 0.05)  # 5% volatility
                
            elif self.scenario_type == "low_volatility":
                # Very low volatility
                price_change = np.random.normal(0, 0.005)  # 0.5% volatility
                
            elif self.scenario_type == "mean_reverting":
                # Mean reverting behavior
                deviation_from_mean = (previous_price - 125.0) / 125.0
                price_change = np.random.normal(-0.1 * deviation_from_mean, 0.015)
                
            elif self.scenario_type == "gap_up":
                # Simulate gap up scenario
                if timestamp.hour == 9 and timestamp.minute == 30:  # Market open
                    price_change = np.random.uniform(0.02, 0.05)  # 2-5% gap up
                else:
                    price_change = np.random.normal(0, 0.015)
                    
            elif self.scenario_type == "gap_down":
                # Simulate gap down scenario
                if timestamp.hour == 9 and timestamp.minute == 30:  # Market open
                    price_change = np.random.uniform(-0.05, -0.02)  # 2-5% gap down
                else:
                    price_change = np.random.normal(0, 0.015)
                    
            else:  # "normal"
                price_change = np.random.normal(0, 0.02)  # Normal 2% volatility
            
            current_price = previous_price * (1 + price_change)
            self.price_history[symbol] = current_price
            
            # Generate volume based on scenario
            if self.scenario_type == "high_volatility":
                volume = np.random.randint(2000000, 5000000)  # High volume
            elif self.scenario_type == "low_volatility":
                volume = np.random.randint(500000, 1000000)  # Low volume
            else:
                volume = np.random.randint(1000000, 2500000)  # Normal volume
            
            market_data[symbol] = {
                'timestamp': timestamp,
                'open': previous_price,
                'high': current_price * (1 + abs(price_change) * 0.5),
                'low': current_price * (1 - abs(price_change) * 0.5),
                'close': current_price,
                'volume': volume,
                'vwap': current_price * (1 + np.random.normal(0, 0.0005)),
                'bid': current_price * 0.9995,
                'ask': current_price * 1.0005,
                'spread': current_price * 0.001,
                'volatility': abs(price_change)
            }
            
        return market_data


@pytest.mark.asyncio  
class TestMarketScenarios:
    """Test system behavior under different market scenarios."""
    
    def setup_method(self):
        """Set up scenario testing environment."""
        # Register template
        if template_registry.get_template("professional_momentum_v1") is None:
            template = ProfessionalMomentumTemplate()
            template_registry.register_template(template)
        
        self.test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        
    def create_test_system(self, scenario_type: str = "normal"):
        """Create a complete test system for scenario testing."""
        # Initialize components
        market_data_provider = AdvancedMarketDataProvider(scenario_type)
        portfolio = IntegrationMockPortfolio(initial_capital=100000.0)
        execution = IntegrationMockExecution()
        configuration = IntegrationMockConfiguration()
        
        # Create template configuration
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.015,
                'confidence_threshold': 0.75,
                'volume_lookback': 10,
                'volume_threshold': 1.5,
                'position_size': 0.02,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.08
            },
            strategy_instance_id=f"scenario_{scenario_type}_strategy"
        )
        
        # Create strategy
        strategy = TemplateStrategyBridge(template_config)
        
        # Create core engine
        core_engine = DelegatedCoreEngine(
            strategy_interface=strategy,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=configuration,
            config=CoreEngineConfig()
        )
        template_bridge = TemplateStrategyBridge(configuration)
        strategy = template_bridge.create_strategy_from_template("professional_momentum_v1")
        core_engine.register_strategy(strategy)
        
        # Create adaptation system
        optimizer = RealTimeParameterOptimizer(
            strategy_id=f"scenario_{scenario_type}_strategy",
            template_id="professional_momentum_v1",
            adaptation_config=AdaptationConfig(adaptation_mode=AdaptationMode.MODERATE)
        )
        
        return {
            'market_data_provider': market_data_provider,
            'portfolio': portfolio,
            'execution': execution,
            'configuration': configuration,
            'core_engine': core_engine,
            'optimizer': optimizer
        }
    
    async def test_trending_market_scenario(self):
        """Test system behavior in trending markets."""
        
        # Test uptrend scenario
        uptrend_system = self.create_test_system("trending_up")
        uptrend_results = await self.run_scenario(uptrend_system, duration_minutes=120)
        
        # Test downtrend scenario  
        downtrend_system = self.create_test_system("trending_down")
        downtrend_results = await self.run_scenario(downtrend_system, duration_minutes=120)
        
        # Verify results
        assert uptrend_results['success_rate'] > 0.5, "Should handle uptrend scenarios"
        assert downtrend_results['success_rate'] > 0.5, "Should handle downtrend scenarios"
        
        # In trending markets, strategy should generate more signals
        assert uptrend_results['total_signals'] > 0, "Should generate signals in uptrend"
        assert downtrend_results['total_signals'] > 0, "Should generate signals in downtrend"
        
        print(f"Trending Market Results:")
        print(f"  Uptrend success rate: {uptrend_results['success_rate']:.2%}")
        print(f"  Downtrend success rate: {downtrend_results['success_rate']:.2%}")
        
    async def test_volatile_market_scenario(self):
        """Test system behavior in high volatility markets."""
        
        # Test high volatility scenario
        volatile_system = self.create_test_system("high_volatility")
        volatile_results = await self.run_scenario(volatile_system, duration_minutes=60)
        
        # Test low volatility scenario
        stable_system = self.create_test_system("low_volatility")
        stable_results = await self.run_scenario(stable_system, duration_minutes=60)
        
        # Verify handling of volatility
        assert volatile_results['success_rate'] > 0.4, "Should handle high volatility"
        assert stable_results['success_rate'] > 0.6, "Should perform better in stable markets"
        
        # High volatility should trigger more adaptations
        if volatile_results['adaptations'] > 0 and stable_results['adaptations'] > 0:
            assert volatile_results['adaptations'] >= stable_results['adaptations'], \
                "High volatility should trigger more adaptations"
        
        print(f"Volatility Scenario Results:")
        print(f"  High volatility success rate: {volatile_results['success_rate']:.2%}")
        print(f"  Low volatility success rate: {stable_results['success_rate']:.2%}")
        
    async def test_gap_scenarios(self):
        """Test system behavior during gap up/down events."""
        
        # Test gap up scenario
        gap_up_system = self.create_test_system("gap_up")
        gap_up_results = await self.run_scenario(gap_up_system, duration_minutes=60)
        
        # Test gap down scenario
        gap_down_system = self.create_test_system("gap_down")
        gap_down_results = await self.run_scenario(gap_down_system, duration_minutes=60)
        
        # Verify gap handling
        assert gap_up_results['success_rate'] > 0.3, "Should handle gap up events"
        assert gap_down_results['success_rate'] > 0.3, "Should handle gap down events"
        
        print(f"Gap Scenario Results:")
        print(f"  Gap up success rate: {gap_up_results['success_rate']:.2%}")
        print(f"  Gap down success rate: {gap_down_results['success_rate']:.2%}")
        
    async def test_mean_reverting_scenario(self):
        """Test system behavior in mean-reverting markets."""
        
        mean_revert_system = self.create_test_system("mean_reverting")
        results = await self.run_scenario(mean_revert_system, duration_minutes=180)
        
        # Verify mean reversion handling
        assert results['success_rate'] > 0.4, "Should handle mean-reverting markets"
        
        # Mean reverting markets might trigger parameter adaptations
        print(f"Mean Reverting Scenario Results:")
        print(f"  Success rate: {results['success_rate']:.2%}")
        print(f"  Adaptations triggered: {results['adaptations']}")
        
    async def run_scenario(self, system: Dict[str, Any], duration_minutes: int) -> Dict[str, Any]:
        """Run a complete scenario and return results."""
        
        results = []
        adaptations = 0
        total_signals = 0
        
        start_time = datetime.now()
        
        # Run scenario for specified duration
        for minute_offset in range(0, duration_minutes, 5):  # Every 5 minutes
            timestamp = start_time + timedelta(minutes=minute_offset)
            
            # Generate market data
            market_data = system['market_data_provider'].get_market_data(
                self.test_symbols, timestamp
            )
            
            # Process through system
            try:
                result = await system['core_engine'].process_trading_cycle(market_data)
                results.append(result)
                
                if result.success and result.signals_generated:
                    total_signals += result.signals_generated
                
                # Add trade data and check for adaptations
                if result.execution_results:
                    for exec_result in result.execution_results:
                        trade_data = {
                            'timestamp': timestamp,
                            'symbol': exec_result['symbol'],
                            'side': 'buy' if exec_result['quantity'] > 0 else 'sell',
                            'quantity': abs(exec_result['quantity']),
                            'price': exec_result['executed_price'],
                            'pnl': np.random.normal(5, 25),
                            'commission': exec_result.get('commission', 2.0),
                            'net_pnl': np.random.normal(3, 25),
                            'position_closed': True,
                            'position_value': abs(exec_result['quantity']) * exec_result['executed_price']
                        }
                        system['optimizer'].add_trade_data(trade_data)
                
                # Check for adaptation every 30 minutes
                if minute_offset % 30 == 0 and minute_offset > 0:
                    current_params = system['configuration'].get_strategy_config("test_strategy")
                    adaptation_result = await system['optimizer'].optimize_parameters(
                        current_parameters=current_params,
                        market_conditions={'volatility': 0.20},
                        force_optimization=False
                    )
                    
                    if adaptation_result.parameters_changed:
                        adaptations += 1
                        
            except Exception as e:
                print(f"Scenario exception at {timestamp}: {e}")
                results.append(None)
        
        # Calculate results
        successful_results = [r for r in results if r and r.success]
        success_rate = len(successful_results) / len(results) if results else 0
        
        return {
            'success_rate': success_rate,
            'total_cycles': len(results),
            'successful_cycles': len(successful_results),
            'total_signals': total_signals,
            'adaptations': adaptations,
            'portfolio_trades': len(system['portfolio'].trade_history)
        }


@pytest.mark.asyncio
class TestSystemResilience:
    """Test system resilience and error recovery."""
    
    def setup_method(self):
        """Set up resilience testing."""
        if template_registry.get_template("professional_momentum_v1") is None:
            template = ProfessionalMomentumTemplate()
            template_registry.register_template(template)
            
        self.test_symbols = ['AAPL', 'GOOGL', 'MSFT']
    
    async def test_data_corruption_resilience(self):
        """Test system resilience to corrupted data."""
        
        # Create test system
        system = self.create_resilience_test_system()
        
        # Test with various types of corrupted data
        corruption_tests = [
            {'symbols': [], 'data': {}},  # Empty data
            {'symbols': self.test_symbols, 'data': {'invalid': 'format'}},  # Wrong format
            {'symbols': self.test_symbols, 'data': None},  # None data
            {'symbols': ['INVALID'], 'data': self.generate_valid_data(['INVALID'])},  # Invalid symbols
        ]
        
        resilience_results = []
        
        for i, test_case in enumerate(corruption_tests):
            try:
                if test_case['data'] is None:
                    result = await system['core_engine'].process_trading_cycle(None)
                else:
                    result = await system['core_engine'].process_trading_cycle(test_case['data'])
                
                # System should handle gracefully, not crash
                resilience_results.append({
                    'test_case': i,
                    'handled_gracefully': True,
                    'success': result.success if result else False
                })
                
            except Exception as e:
                # Log but continue - we're testing resilience
                resilience_results.append({
                    'test_case': i,
                    'handled_gracefully': False,
                    'error': str(e)
                })
        
        # Verify resilience
        graceful_handling = sum(1 for r in resilience_results if r['handled_gracefully'])
        resilience_rate = graceful_handling / len(resilience_results)
        
        # Should handle at least 75% of corruption scenarios gracefully
        assert resilience_rate >= 0.75, f"Resilience rate too low: {resilience_rate:.2%}"
        
        print(f"Data Corruption Resilience: {resilience_rate:.2%}")
    
    async def test_memory_pressure_resilience(self):
        """Test system behavior under memory pressure."""
        
        system = self.create_resilience_test_system()
        
        # Process large amounts of data rapidly
        stress_cycles = 100
        successful_cycles = 0
        
        for i in range(stress_cycles):
            # Generate large market data
            large_symbol_list = [f"SYM{j:03d}" for j in range(50)]  # 50 symbols
            market_data = self.generate_valid_data(large_symbol_list)
            
            try:
                result = await system['core_engine'].process_trading_cycle(market_data)
                if result and result.get('cycle_number'):
                    successful_cycles += 1
                    
            except Exception as e:
                print(f"Memory pressure exception at cycle {i}: {e}")
        
        # Should handle at least 70% under memory pressure
        success_rate = successful_cycles / stress_cycles
        assert success_rate >= 0.70, f"Memory pressure success rate too low: {success_rate:.2%}"
        
        print(f"Memory Pressure Resilience: {success_rate:.2%}")
    
    def create_resilience_test_system(self):
        """Create system for resilience testing."""
        portfolio = IntegrationMockPortfolio()
        execution = IntegrationMockExecution()
        configuration = IntegrationMockConfiguration()
        
        # Create template configuration
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.015,
                'confidence_threshold': 0.75,
                'volume_lookback': 10,
                'volume_threshold': 1.5,
                'position_size': 0.02,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.08
            },
            strategy_instance_id="resilience_test_strategy"
        )
        
        strategy = TemplateStrategyBridge(template_config)
        
        core_engine = DelegatedCoreEngine(
            strategy_interface=strategy,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=configuration,
            config=CoreEngineConfig()
        )
        
        return {
            'core_engine': core_engine,
            'portfolio': portfolio,
            'execution': execution,
            'configuration': configuration,
            'strategy': strategy
        }
    
    def generate_valid_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Generate valid market data for testing."""
        market_data = {}
        timestamp = datetime.now()
        
        for symbol in symbols:
            price = 100.0 + hash(symbol) % 50
            market_data[symbol] = {
                'timestamp': timestamp,
                'open': price * 0.999,
                'high': price * 1.001,
                'low': price * 0.998,
                'close': price,
                'volume': 1000000,
                'bid': price * 0.9995,
                'ask': price * 1.0005
            }
            
        return market_data


@pytest.mark.asyncio
class TestPerformanceValidation:
    """Test system performance characteristics."""
    
    def setup_method(self):
        """Set up performance testing."""
        if template_registry.get_template("professional_momentum_v1") is None:
            template = ProfessionalMomentumTemplate()
            template_registry.register_template(template)
    
    async def test_processing_speed(self):
        """Test system processing speed."""
        
        system = self.create_performance_test_system()
        test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
        
        # Measure processing time for various data sizes
        processing_times = []
        
        for symbol_count in [5, 10, 20, 50]:
            symbols = [f"SYM{i:03d}" for i in range(symbol_count)]
            market_data = self.generate_performance_data(symbols)
            
            start_time = datetime.now()
            result = await system['core_engine'].process_trading_cycle(market_data)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            processing_times.append({
                'symbol_count': symbol_count,
                'processing_time': processing_time,
                'success': result.success if result else False
            })
        
        # Verify reasonable processing times
        for timing in processing_times:
            # Should process within reasonable time (< 1 second for most cases)
            max_time = 1.0 if timing['symbol_count'] <= 20 else 2.0
            assert timing['processing_time'] < max_time, \
                f"Processing time too slow: {timing['processing_time']:.3f}s for {timing['symbol_count']} symbols"
        
        print("Processing Speed Results:")
        for timing in processing_times:
            print(f"  {timing['symbol_count']} symbols: {timing['processing_time']:.3f}s")
    
    async def test_adaptation_performance(self):
        """Test adaptation system performance."""
        
        optimizer = RealTimeParameterOptimizer(
            strategy_id="performance_test_strategy",
            template_id="professional_momentum_v1",
            adaptation_config=AdaptationConfig(adaptation_mode=AdaptationMode.MODERATE)
        )
        
        # Add trade data
        for i in range(100):
            trade_data = {
                'timestamp': datetime.now() - timedelta(minutes=i),
                'symbol': f"SYM{i%5:03d}",
                'side': 'buy' if i % 2 == 0 else 'sell',
                'quantity': 100,
                'price': 150.0,
                'pnl': np.random.normal(5, 15),
                'commission': 2.0,
                'net_pnl': np.random.normal(3, 15),
                'position_closed': True,
                'position_value': 15000.0
            }
            optimizer.add_trade_data(trade_data)
        
        # Measure adaptation performance
        current_params = {
            'lookback_period': 20,
            'momentum_threshold': 0.015,
            'confidence_threshold': 0.75,
            'position_size': 0.02
        }
        
        start_time = datetime.now()
        adaptation_result = await optimizer.optimize_parameters(
            current_parameters=current_params,
            market_conditions={'volatility': 0.20},
            force_optimization=True
        )
        end_time = datetime.now()
        
        adaptation_time = (end_time - start_time).total_seconds()
        
        # Adaptation should complete quickly (< 0.5 seconds)
        assert adaptation_time < 0.5, f"Adaptation too slow: {adaptation_time:.3f}s"
        assert adaptation_result is not None, "Adaptation should return result"
        
        print(f"Adaptation Performance: {adaptation_time:.3f}s")
    
    def create_performance_test_system(self):
        """Create system for performance testing."""
        portfolio = IntegrationMockPortfolio()
        execution = IntegrationMockExecution()
        configuration = IntegrationMockConfiguration()
        
        # Create template configuration
        template_config = TemplateConfiguration(
            template_id="professional_momentum_v1",
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.015,
                'confidence_threshold': 0.75,
                'volume_lookback': 10,
                'volume_threshold': 1.5,
                'position_size': 0.02,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.08
            },
            strategy_instance_id="performance_test_strategy"
        )
        
        strategy = TemplateStrategyBridge(template_config)
        
        core_engine = DelegatedCoreEngine(
            strategy_interface=strategy,
            portfolio_interface=portfolio,
            execution_interface=execution,
            configuration_interface=configuration,
            config=CoreEngineConfig()
        )
        
        return {
            'core_engine': core_engine,
            'portfolio': portfolio,
            'execution': execution,
            'configuration': configuration
        }
    
    def generate_performance_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Generate market data for performance testing."""
        market_data = {}
        timestamp = datetime.now()
        
        for symbol in symbols:
            price = 100.0 + hash(symbol) % 50
            market_data[symbol] = {
                'timestamp': timestamp,
                'open': price * 0.999,
                'high': price * 1.002,
                'low': price * 0.998,
                'close': price,
                'volume': np.random.randint(500000, 2000000),
                'vwap': price * 1.0001,
                'bid': price * 0.9995,
                'ask': price * 1.0005,
                'spread': price * 0.001
            }
            
        return market_data
