"""
Execution Engine Integration Tests - Batch 6

This module tests the execution engine infrastructure, including order routing, execution quality,
latency monitoring, slippage analysis, and execution reporting.
"""

import pytest
import asyncio
import time
import random
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from tests.integration.conftest import TestConfig
from tests.integration.mock_services import (
    MockSignalGenerator, MockExecutionEngine, MockRiskManager, MockPortfolioManager,
    MockSignal, MockOrder, MockExecution
)
from tests.integration.test_data_scenarios import TestDataScenarios
from tests.integration.test_logging import monitoring_context, log_test_event


@dataclass
class MockMarketOrder:
    """Mock market order structure for testing."""
    order_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: int
    order_type: str  # 'MARKET', 'LIMIT', 'STOP'
    timestamp: datetime
    price: Optional[float] = None
    stop_price: Optional[float] = None


@dataclass
class MockExecutionResult:
    """Mock execution result structure for testing."""
    execution_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    executed_quantity: int
    price: float
    execution_price: float
    timestamp: datetime
    status: str  # 'FILLED', 'PARTIAL', 'REJECTED', 'CANCELLED'
    slippage: float
    latency_ms: float
    venue: str


@dataclass
class MockExecutionMetrics:
    """Mock execution metrics structure for testing."""
    total_orders: int
    filled_orders: int
    rejected_orders: int
    avg_latency_ms: float
    avg_slippage: float
    fill_rate: float
    avg_execution_price: float
    timestamp: datetime


class MockExecutionEngineSystem:
    """Mock execution engine system for testing."""
    
    def __init__(self):
        self.orders = {}
        self.executions = {}
        self.venues = ['NYSE', 'NASDAQ', 'ARCA', 'BATS']
        self.performance_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'rejected_orders': 0,
            'total_latency_ms': 0.0,
            'total_slippage': 0.0,
            'avg_latency_ms': 0.0,
            'avg_slippage': 0.0
        }
        self.execution_alerts = []
        self.venue_performance = {venue: {'orders': 0, 'fills': 0, 'latency': 0.0} for venue in self.venues}
    
    async def route_order(self, order: MockMarketOrder) -> Dict[str, Any]:
        """Route order to appropriate venue."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.001, 0.005))  # 1-5ms
            
            # Select venue based on order characteristics
            if order.quantity > 10000:
                venue = 'NYSE'  # Large orders to NYSE
            elif order.symbol in ['AAPL', 'GOOGL', 'MSFT']:
                venue = 'NASDAQ'  # Tech stocks to NASDAQ
            else:
                venue = random.choice(self.venues)
            
            # Update venue performance
            self.venue_performance[venue]['orders'] += 1
            
            # Simulate routing decision
            routing_result = {
                'order_id': order.order_id,
                'venue': venue,
                'routing_time_ms': (time.time() - start_time) * 1000,
                'status': 'ROUTED'
            }
            
            # Store order
            self.orders[order.order_id] = order
            
            return routing_result
            
        except Exception as e:
            return {
                'order_id': order.order_id,
                'venue': None,
                'routing_time_ms': (time.time() - start_time) * 1000,
                'status': 'FAILED',
                'error': str(e)
            }
    
    async def execute_order(self, order: MockMarketOrder, venue: str) -> MockExecutionResult:
        """Execute order on specified venue."""
        start_time = time.time()
        
        try:
            # Simulate execution time
            execution_latency = random.uniform(0.005, 0.020)  # 5-20ms
            await asyncio.sleep(execution_latency)
            
            # Simulate market conditions
            base_price = random.uniform(50, 500)
            market_volatility = random.uniform(0.001, 0.01)  # 0.1% to 1%
            
            # Calculate execution price with slippage
            if order.side == 'BUY':
                execution_price = base_price * (1 + market_volatility)  # Buy at higher price
            else:
                execution_price = base_price * (1 - market_volatility)  # Sell at lower price
            
            # Calculate slippage
            slippage = abs(execution_price - base_price) / base_price
            
            # Determine execution status
            if random.random() < 0.95:  # 95% fill rate
                status = 'FILLED'
                executed_quantity = order.quantity
                self.performance_stats['filled_orders'] += 1
                self.venue_performance[venue]['fills'] += 1
            else:
                status = 'REJECTED'
                executed_quantity = 0
                self.performance_stats['rejected_orders'] += 1
            
            # Update performance stats
            latency_ms = (time.time() - start_time) * 1000
            self.performance_stats['total_orders'] += 1
            self.performance_stats['total_latency_ms'] += latency_ms
            self.performance_stats['total_slippage'] += slippage
            self.performance_stats['avg_latency_ms'] = (
                self.performance_stats['total_latency_ms'] / 
                self.performance_stats['total_orders']
            )
            self.performance_stats['avg_slippage'] = (
                self.performance_stats['total_slippage'] / 
                self.performance_stats['total_orders']
            )
            
            # Update venue performance
            self.venue_performance[venue]['latency'] += latency_ms
            
            # Create execution result
            execution = MockExecutionResult(
                execution_id=f"exec_{len(self.executions) + 1}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                executed_quantity=executed_quantity,
                price=base_price,
                execution_price=execution_price,
                timestamp=datetime.now(),
                status=status,
                slippage=slippage,
                latency_ms=latency_ms,
                venue=venue
            )
            
            # Store execution
            self.executions[execution.execution_id] = execution
            
            # Generate alerts for poor performance
            if latency_ms > 15:  # High latency alert
                self.execution_alerts.append({
                    'type': 'high_latency',
                    'message': f'High execution latency: {latency_ms:.2f}ms',
                    'timestamp': datetime.now(),
                    'execution_id': execution.execution_id
                })
            
            if slippage > 0.005:  # High slippage alert
                self.execution_alerts.append({
                    'type': 'high_slippage',
                    'message': f'High slippage: {slippage:.4f}',
                    'timestamp': datetime.now(),
                    'execution_id': execution.execution_id
                })
            
            return execution
            
        except Exception as e:
            # Return failed execution
            return MockExecutionResult(
                execution_id=f"exec_{len(self.executions) + 1}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                executed_quantity=0,
                price=0.0,
                execution_price=0.0,
                timestamp=datetime.now(),
                status='FAILED',
                slippage=0.0,
                latency_ms=(time.time() - start_time) * 1000,
                venue=venue
            )
    
    async def monitor_execution_quality(self, executions: List[MockExecutionResult]) -> MockExecutionMetrics:
        """Monitor execution quality and calculate metrics."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.002, 0.005))  # 2-5ms
            
            if not executions:
                return MockExecutionMetrics(
                    total_orders=0,
                    filled_orders=0,
                    rejected_orders=0,
                    avg_latency_ms=0.0,
                    avg_slippage=0.0,
                    fill_rate=0.0,
                    avg_execution_price=0.0,
                    timestamp=datetime.now()
                )
            
            # Calculate metrics
            total_orders = len(executions)
            filled_orders = sum(1 for e in executions if e.status == 'FILLED')
            rejected_orders = sum(1 for e in executions if e.status == 'REJECTED')
            
            avg_latency = sum(e.latency_ms for e in executions) / total_orders
            avg_slippage = sum(e.slippage for e in executions) / total_orders
            fill_rate = filled_orders / total_orders if total_orders > 0 else 0.0
            
            # Calculate average execution price (only for filled orders)
            filled_executions = [e for e in executions if e.status == 'FILLED']
            avg_execution_price = (
                sum(e.execution_price for e in filled_executions) / len(filled_executions)
                if filled_executions else 0.0
            )
            
            metrics = MockExecutionMetrics(
                total_orders=total_orders,
                filled_orders=filled_orders,
                rejected_orders=rejected_orders,
                avg_latency_ms=avg_latency,
                avg_slippage=avg_slippage,
                fill_rate=fill_rate,
                avg_execution_price=avg_execution_price,
                timestamp=datetime.now()
            )
            
            return metrics
            
        except Exception as e:
            # Return default metrics on error
            return MockExecutionMetrics(
                total_orders=0,
                filled_orders=0,
                rejected_orders=0,
                avg_latency_ms=0.0,
                avg_slippage=0.0,
                fill_rate=0.0,
                avg_execution_price=0.0,
                timestamp=datetime.now()
            )
    
    async def analyze_slippage(self, executions: List[MockExecutionResult]) -> Dict[str, Any]:
        """Analyze slippage patterns and causes."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.003, 0.008))  # 3-8ms
            
            if not executions:
                return {'error': 'No executions to analyze'}
            
            # Analyze slippage by side
            buy_executions = [e for e in executions if e.side == 'BUY']
            sell_executions = [e for e in executions if e.side == 'SELL']
            
            buy_slippage = sum(e.slippage for e in buy_executions) / len(buy_executions) if buy_executions else 0.0
            sell_slippage = sum(e.slippage for e in sell_executions) / len(sell_executions) if sell_executions else 0.0
            
            # Analyze slippage by venue
            venue_slippage = {}
            for venue in self.venues:
                venue_executions = [e for e in executions if e.venue == venue]
                if venue_executions:
                    venue_slippage[venue] = sum(e.slippage for e in venue_executions) / len(venue_executions)
                else:
                    venue_slippage[venue] = 0.0
            
            # Analyze slippage by order size
            small_orders = [e for e in executions if e.quantity <= 1000]
            medium_orders = [e for e in executions if 1000 < e.quantity <= 5000]
            large_orders = [e for e in executions if e.quantity > 5000]
            
            small_slippage = sum(e.slippage for e in small_orders) / len(small_orders) if small_orders else 0.0
            medium_slippage = sum(e.slippage for e in medium_orders) / len(medium_orders) if medium_orders else 0.0
            large_slippage = sum(e.slippage for e in large_orders) / len(large_orders) if large_orders else 0.0
            
            analysis = {
                'total_executions': len(executions),
                'avg_slippage': sum(e.slippage for e in executions) / len(executions),
                'buy_slippage': buy_slippage,
                'sell_slippage': sell_slippage,
                'venue_slippage': venue_slippage,
                'size_slippage': {
                    'small': small_slippage,
                    'medium': medium_slippage,
                    'large': large_slippage
                },
                'analysis_time_ms': (time.time() - start_time) * 1000
            }
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def generate_execution_report(self) -> Dict[str, Any]:
        """Generate comprehensive execution report."""
        try:
            recent_executions = list(self.executions.values())[-20:]  # Last 20 executions
            
            report = {
                'timestamp': datetime.now(),
                'performance_stats': self.performance_stats,
                'venue_performance': self.venue_performance,
                'execution_alerts': self.execution_alerts[-10:],  # Last 10 alerts
                'orders_count': len(self.orders),
                'executions_count': len(self.executions),
                'recent_executions': len(recent_executions)
            }
            
            return report
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()


class TestExecutionEngineInfrastructure:
    """Test execution engine infrastructure integration."""
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_execution_engine_infrastructure(self):
        """Test execution engine infrastructure setup and basic functionality."""
        with monitoring_context("execution_engine_infrastructure") as logger:
            logger.log_test_event("Testing execution engine infrastructure")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Create test orders
            orders = [
                MockMarketOrder(
                    order_id=f"order_{i}",
                    symbol=random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA']),
                    side=random.choice(['BUY', 'SELL']),
                    quantity=random.randint(100, 5000),
                    order_type='MARKET',
                    timestamp=datetime.now()
                )
                for i in range(5)
            ]
            
            # Test order routing
            routing_results = []
            for order in orders:
                routing = await execution_engine.route_order(order)
                routing_results.append(routing)
            
            # Test order execution
            execution_results = []
            for order, routing in zip(orders, routing_results):
                if routing['status'] == 'ROUTED':
                    execution = await execution_engine.execute_order(order, routing['venue'])
                    execution_results.append(execution)
            
            # Validate results
            assert len(routing_results) == len(orders)
            assert len(execution_results) > 0
            
            for routing in routing_results:
                assert 'order_id' in routing
                assert 'venue' in routing
                assert 'status' in routing
            
            for execution in execution_results:
                assert execution.execution_id is not None
                assert execution.order_id is not None
                assert execution.symbol is not None
                assert execution.side in ['BUY', 'SELL']
                assert execution.quantity > 0
                assert execution.latency_ms > 0
            
            # Get performance stats
            stats = execution_engine.get_performance_stats()
            
            logger.log_test_event("Execution engine infrastructure validated", {
                'orders_processed': len(orders),
                'executions_completed': len(execution_results),
                'total_orders': stats['total_orders'],
                'avg_latency_ms': stats['avg_latency_ms']
            })
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_order_routing_accuracy(self):
        """Test order routing accuracy and venue selection."""
        with monitoring_context("order_routing_accuracy") as logger:
            logger.log_test_event("Testing order routing accuracy")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Test different order types
            test_orders = [
                # Large order (should route to NYSE)
                MockMarketOrder(
                    order_id="large_order",
                    symbol='AAPL',
                    side='BUY',
                    quantity=15000,
                    order_type='MARKET',
                    timestamp=datetime.now()
                ),
                # Tech stock (should route to NASDAQ)
                MockMarketOrder(
                    order_id="tech_order",
                    symbol='GOOGL',
                    side='SELL',
                    quantity=1000,
                    order_type='MARKET',
                    timestamp=datetime.now()
                ),
                # Regular order (random venue)
                MockMarketOrder(
                    order_id="regular_order",
                    symbol='TSLA',
                    side='BUY',
                    quantity=500,
                    order_type='MARKET',
                    timestamp=datetime.now()
                )
            ]
            
            routing_results = []
            
            for order in test_orders:
                routing = await execution_engine.route_order(order)
                routing_results.append(routing)
                
                # Validate routing
                assert routing['status'] == 'ROUTED'
                assert routing['venue'] in execution_engine.venues
                assert routing['routing_time_ms'] > 0
                
                # Check venue selection logic
                if order.quantity > 10000:
                    assert routing['venue'] == 'NYSE'
                elif order.symbol in ['AAPL', 'GOOGL', 'MSFT']:
                    assert routing['venue'] == 'NASDAQ'
            
            logger.log_test_event("Order routing accuracy validated", {
                'test_orders': len(test_orders),
                'routing_results': routing_results
            })
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_execution_quality_monitoring(self):
        """Test execution quality monitoring and metrics calculation."""
        with monitoring_context("execution_quality_monitoring") as logger:
            logger.log_test_event("Testing execution quality monitoring")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Generate test executions
            test_executions = []
            for i in range(10):
                execution = await execution_engine.execute_order(
                    MockMarketOrder(
                        order_id=f"test_order_{i}",
                        symbol=random.choice(['AAPL', 'GOOGL', 'MSFT']),
                        side=random.choice(['BUY', 'SELL']),
                        quantity=random.randint(100, 2000),
                        order_type='MARKET',
                        timestamp=datetime.now()
                    ),
                    random.choice(execution_engine.venues)
                )
                test_executions.append(execution)
            
            # Monitor execution quality
            metrics = await execution_engine.monitor_execution_quality(test_executions)
            
            # Validate metrics
            assert metrics.total_orders > 0
            assert metrics.filled_orders >= 0
            assert metrics.rejected_orders >= 0
            assert metrics.avg_latency_ms > 0
            assert metrics.avg_slippage >= 0
            assert 0 <= metrics.fill_rate <= 1
            
            # Validate relationships
            assert metrics.filled_orders + metrics.rejected_orders <= metrics.total_orders
            assert metrics.fill_rate == metrics.filled_orders / metrics.total_orders
            
            # Get performance stats
            stats = execution_engine.get_performance_stats()
            
            logger.log_test_event("Execution quality monitoring validated", {
                'executions_analyzed': len(test_executions),
                'total_orders': metrics.total_orders,
                'fill_rate': metrics.fill_rate,
                'avg_latency_ms': metrics.avg_latency_ms,
                'avg_slippage': metrics.avg_slippage
            })
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_latency_monitoring(self):
        """Test latency monitoring and performance tracking."""
        with monitoring_context("latency_monitoring") as logger:
            logger.log_test_event("Testing latency monitoring")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Test different order sizes and measure latency
            latency_results = []
            order_sizes = [100, 500, 1000, 5000]
            
            for size in order_sizes:
                start_time = time.time()
                
                execution = await execution_engine.execute_order(
                    MockMarketOrder(
                        order_id=f"latency_test_{size}",
                        symbol='AAPL',
                        side='BUY',
                        quantity=size,
                        order_type='MARKET',
                        timestamp=datetime.now()
                    ),
                    'NASDAQ'
                )
                
                end_time = time.time()
                total_latency = (end_time - start_time) * 1000
                
                latency_results.append({
                    'order_size': size,
                    'execution_latency_ms': execution.latency_ms,
                    'total_latency_ms': total_latency,
                    'status': execution.status
                })
                
                # Validate latency is reasonable
                assert execution.latency_ms > 0
                assert execution.latency_ms < 100  # Should be under 100ms
                assert total_latency > execution.latency_ms  # Total includes test overhead
            
            # Get performance stats
            stats = execution_engine.get_performance_stats()
            
            logger.log_test_event("Latency monitoring validated", {
                'order_sizes_tested': order_sizes,
                'latency_results': latency_results,
                'avg_latency_ms': stats['avg_latency_ms'],
                'total_orders': stats['total_orders']
            })
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_slippage_analysis(self):
        """Test slippage analysis and pattern detection."""
        with monitoring_context("slippage_analysis") as logger:
            logger.log_test_event("Testing slippage analysis")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Generate diverse test executions
            test_executions = []
            
            # Mix of buy and sell orders
            for i in range(5):
                execution = await execution_engine.execute_order(
                    MockMarketOrder(
                        order_id=f"buy_order_{i}",
                        symbol='AAPL',
                        side='BUY',
                        quantity=random.randint(100, 2000),
                        order_type='MARKET',
                        timestamp=datetime.now()
                    ),
                    'NASDAQ'
                )
                test_executions.append(execution)
            
            for i in range(5):
                execution = await execution_engine.execute_order(
                    MockMarketOrder(
                        order_id=f"sell_order_{i}",
                        symbol='GOOGL',
                        side='SELL',
                        quantity=random.randint(100, 2000),
                        order_type='MARKET',
                        timestamp=datetime.now()
                    ),
                    'NYSE'
                )
                test_executions.append(execution)
            
            # Analyze slippage
            slippage_analysis = await execution_engine.analyze_slippage(test_executions)
            
            # Validate analysis results
            assert 'total_executions' in slippage_analysis
            assert 'avg_slippage' in slippage_analysis
            assert 'buy_slippage' in slippage_analysis
            assert 'sell_slippage' in slippage_analysis
            assert 'venue_slippage' in slippage_analysis
            assert 'size_slippage' in slippage_analysis
            
            # Validate slippage values
            assert slippage_analysis['total_executions'] == len(test_executions)
            assert slippage_analysis['avg_slippage'] >= 0
            assert slippage_analysis['buy_slippage'] >= 0
            assert slippage_analysis['sell_slippage'] >= 0
            
            # Validate venue slippage
            for venue in execution_engine.venues:
                assert venue in slippage_analysis['venue_slippage']
                assert slippage_analysis['venue_slippage'][venue] >= 0
            
            # Validate size slippage
            size_slippage = slippage_analysis['size_slippage']
            assert 'small' in size_slippage
            assert 'medium' in size_slippage
            assert 'large' in size_slippage
            
            logger.log_test_event("Slippage analysis validated", {
                'executions_analyzed': len(test_executions),
                'avg_slippage': slippage_analysis['avg_slippage'],
                'buy_slippage': slippage_analysis['buy_slippage'],
                'sell_slippage': slippage_analysis['sell_slippage'],
                'analysis_time_ms': slippage_analysis['analysis_time_ms']
            })
    
    @pytest.mark.execution
    @pytest.mark.asyncio
    async def test_execution_reporting(self):
        """Test execution reporting functionality."""
        with monitoring_context("execution_reporting") as logger:
            logger.log_test_event("Testing execution reporting")
            
            # Create test components
            execution_engine = MockExecutionEngineSystem()
            
            # Generate some activity to populate the system
            for i in range(15):
                await execution_engine.execute_order(
                    MockMarketOrder(
                        order_id=f"report_test_{i}",
                        symbol=random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA']),
                        side=random.choice(['BUY', 'SELL']),
                        quantity=random.randint(100, 3000),
                        order_type='MARKET',
                        timestamp=datetime.now()
                    ),
                    random.choice(execution_engine.venues)
                )
            
            # Generate execution report
            execution_report = execution_engine.generate_execution_report()
            
            # Validate report structure
            assert 'timestamp' in execution_report
            assert 'performance_stats' in execution_report
            assert 'venue_performance' in execution_report
            assert 'execution_alerts' in execution_report
            assert 'orders_count' in execution_report
            assert 'executions_count' in execution_report
            assert 'recent_executions' in execution_report
            
            # Validate report contents
            assert execution_report['orders_count'] >= 0
            assert execution_report['executions_count'] >= 0
            assert execution_report['recent_executions'] >= 0
            
            # Validate performance stats
            perf_stats = execution_report['performance_stats']
            assert 'total_orders' in perf_stats
            assert 'filled_orders' in perf_stats
            assert 'avg_latency_ms' in perf_stats
            assert 'avg_slippage' in perf_stats
            
            # Validate venue performance
            venue_perf = execution_report['venue_performance']
            for venue in execution_engine.venues:
                assert venue in venue_perf
                assert 'orders' in venue_perf[venue]
                assert 'fills' in venue_perf[venue]
                assert 'latency' in venue_perf[venue]
            
            # Get performance stats
            stats = execution_engine.get_performance_stats()
            
            logger.log_test_event("Execution reporting validated", {
                'execution_report_generated': True,
                'orders_count': execution_report['orders_count'],
                'executions_count': execution_report['executions_count'],
                'total_orders': stats['total_orders'],
                'fill_rate': stats['filled_orders'] / stats['total_orders'] if stats['total_orders'] > 0 else 0
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "execution"]) 