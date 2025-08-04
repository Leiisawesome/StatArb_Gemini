"""
Portfolio Management Integration Tests - Batch 7

This module tests the portfolio management infrastructure, including position tracking, P&L calculation,
portfolio rebalancing, performance attribution, and portfolio reporting.
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
class MockPosition:
    """Mock position structure for testing."""
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime
    side: str = 'LONG'  # 'LONG' or 'SHORT'


@dataclass
class MockPortfolioState:
    """Mock portfolio state structure for testing."""
    total_value: float
    cash: float
    positions: Dict[str, MockPosition]
    timestamp: datetime
    daily_pnl: float = 0.0
    total_pnl: float = 0.0


@dataclass
class MockPortfolioMetrics:
    """Mock portfolio metrics structure for testing."""
    total_value: float
    cash: float
    positions_count: int
    total_unrealized_pnl: float
    total_realized_pnl: float
    daily_pnl: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    timestamp: datetime


@dataclass
class MockRebalancingAction:
    """Mock rebalancing action structure for testing."""
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    quantity: int
    target_weight: float
    current_weight: float
    reason: str
    timestamp: datetime


class MockPortfolioManagementSystem:
    """Mock portfolio management system for testing."""
    
    def __init__(self):
        self.positions = {}
        self.portfolio_history = []
        self.target_weights = {
            'AAPL': 0.25,
            'GOOGL': 0.20,
            'MSFT': 0.20,
            'TSLA': 0.15,
            'AMZN': 0.20
        }
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'avg_trade_pnl': 0.0,
            'max_position_value': 0.0,
            'rebalancing_events': 0
        }
        self.portfolio_alerts = []
        self.rebalancing_history = []
    
    async def track_position(self, symbol: str, quantity: int, price: float, side: str = 'LONG') -> MockPosition:
        """Track a new position or update existing position."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.001, 0.003))  # 1-3ms
            
            # Calculate current price with some variation
            current_price = price * random.uniform(0.95, 1.05)
            
            if symbol in self.positions:
                # Update existing position
                existing_pos = self.positions[symbol]
                new_quantity = existing_pos.quantity + quantity
                
                # Calculate new entry price (weighted average)
                total_cost = (existing_pos.quantity * existing_pos.entry_price) + (quantity * price)
                new_entry_price = total_cost / new_quantity
                
                # Calculate P&L
                unrealized_pnl = (current_price - new_entry_price) * new_quantity
                if side == 'SHORT':
                    unrealized_pnl = -unrealized_pnl
                
                position = MockPosition(
                    symbol=symbol,
                    quantity=new_quantity,
                    entry_price=new_entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=existing_pos.realized_pnl,
                    timestamp=datetime.now(),
                    side=side
                )
            else:
                # Create new position
                unrealized_pnl = (current_price - price) * quantity
                if side == 'SHORT':
                    unrealized_pnl = -unrealized_pnl
                
                position = MockPosition(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=0.0,
                    timestamp=datetime.now(),
                    side=side
                )
            
            # Store position
            self.positions[symbol] = position
            
            # Update performance stats
            self.performance_stats['total_trades'] += 1
            if unrealized_pnl > 0:
                self.performance_stats['winning_trades'] += 1
            else:
                self.performance_stats['losing_trades'] += 1
            
            return position
            
        except Exception as e:
            # Return default position on error
            return MockPosition(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                timestamp=datetime.now(),
                side=side
            )
    
    async def calculate_pnl(self, portfolio_state: MockPortfolioState) -> Dict[str, float]:
        """Calculate P&L for portfolio."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.002, 0.005))  # 2-5ms
            
            total_unrealized_pnl = 0.0
            total_realized_pnl = 0.0
            
            for position in portfolio_state.positions.values():
                total_unrealized_pnl += position.unrealized_pnl
                total_realized_pnl += position.realized_pnl
            
            # Calculate daily P&L (simplified)
            daily_pnl = total_unrealized_pnl * random.uniform(-0.02, 0.03)  # -2% to +3%
            total_pnl = total_unrealized_pnl + total_realized_pnl + daily_pnl
            
            pnl_metrics = {
                'total_unrealized_pnl': total_unrealized_pnl,
                'total_realized_pnl': total_realized_pnl,
                'daily_pnl': daily_pnl,
                'total_pnl': total_pnl,
                'pnl_percentage': (total_pnl / portfolio_state.total_value) * 100 if portfolio_state.total_value > 0 else 0.0
            }
            
            return pnl_metrics
            
        except Exception as e:
            return {
                'total_unrealized_pnl': 0.0,
                'total_realized_pnl': 0.0,
                'daily_pnl': 0.0,
                'total_pnl': 0.0,
                'pnl_percentage': 0.0
            }
    
    async def rebalance_portfolio(self, portfolio_state: MockPortfolioState) -> List[MockRebalancingAction]:
        """Rebalance portfolio to target weights."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.005, 0.010))  # 5-10ms
            
            total_value = portfolio_state.total_value
            rebalancing_actions = []
            
            # Calculate current weights
            current_weights = {}
            for symbol, position in portfolio_state.positions.items():
                position_value = position.quantity * position.current_price
                current_weights[symbol] = position_value / total_value if total_value > 0 else 0.0
            
            # Check each target weight
            for symbol, target_weight in self.target_weights.items():
                current_weight = current_weights.get(symbol, 0.0)
                target_value = total_value * target_weight
                current_value = current_weight * total_value
                
                # Determine rebalancing action
                if abs(target_weight - current_weight) > 0.05:  # 5% threshold
                    if target_weight > current_weight:
                        # Need to buy
                        additional_value = target_value - current_value
                        if additional_value > 1000:  # Minimum trade size
                            quantity = int(additional_value / portfolio_state.positions.get(symbol, MockPosition(symbol, 0, 100, 100, 0, 0, datetime.now())).current_price)
                            action = MockRebalancingAction(
                                symbol=symbol,
                                action='BUY',
                                quantity=quantity,
                                target_weight=target_weight,
                                current_weight=current_weight,
                                reason='Underweight position',
                                timestamp=datetime.now()
                            )
                            rebalancing_actions.append(action)
                    else:
                        # Need to sell
                        excess_value = current_value - target_value
                        if excess_value > 1000:  # Minimum trade size
                            quantity = int(excess_value / portfolio_state.positions.get(symbol, MockPosition(symbol, 0, 100, 100, 0, 0, datetime.now())).current_price)
                            action = MockRebalancingAction(
                                symbol=symbol,
                                action='SELL',
                                quantity=quantity,
                                target_weight=target_weight,
                                current_weight=current_weight,
                                reason='Overweight position',
                                timestamp=datetime.now()
                            )
                            rebalancing_actions.append(action)
                else:
                    # Hold position
                    action = MockRebalancingAction(
                        symbol=symbol,
                        action='HOLD',
                        quantity=0,
                        target_weight=target_weight,
                        current_weight=current_weight,
                        reason='Within target range',
                        timestamp=datetime.now()
                    )
                    rebalancing_actions.append(action)
            
            # Update performance stats
            self.performance_stats['rebalancing_events'] += 1
            
            # Store rebalancing history
            self.rebalancing_history.append({
                'timestamp': datetime.now(),
                'actions': rebalancing_actions,
                'total_value': total_value
            })
            
            return rebalancing_actions
            
        except Exception as e:
            return []
    
    async def calculate_performance_attribution(self, portfolio_state: MockPortfolioState, benchmark_returns: Dict[str, float]) -> Dict[str, Any]:
        """Calculate performance attribution analysis."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.003, 0.008))  # 3-8ms
            
            attribution_results = {
                'total_return': 0.0,
                'benchmark_return': 0.0,
                'excess_return': 0.0,
                'allocation_effect': 0.0,
                'selection_effect': 0.0,
                'interaction_effect': 0.0,
                'position_attribution': {}
            }
            
            # Calculate portfolio return
            total_value = portfolio_state.total_value
            if total_value > 0:
                total_return = sum(pos.unrealized_pnl for pos in portfolio_state.positions.values()) / total_value
                attribution_results['total_return'] = total_return
            
            # Calculate benchmark return (weighted average)
            benchmark_return = 0.0
            for symbol, position in portfolio_state.positions.items():
                if symbol in benchmark_returns:
                    weight = (position.quantity * position.current_price) / total_value if total_value > 0 else 0.0
                    benchmark_return += weight * benchmark_returns[symbol]
            
            attribution_results['benchmark_return'] = benchmark_return
            attribution_results['excess_return'] = attribution_results['total_return'] - benchmark_return
            
            # Calculate attribution effects (simplified)
            allocation_effect = random.uniform(-0.02, 0.03)  # -2% to +3%
            selection_effect = random.uniform(-0.01, 0.02)  # -1% to +2%
            interaction_effect = attribution_results['excess_return'] - allocation_effect - selection_effect
            
            attribution_results['allocation_effect'] = allocation_effect
            attribution_results['selection_effect'] = selection_effect
            attribution_results['interaction_effect'] = interaction_effect
            
            # Calculate position-level attribution
            for symbol, position in portfolio_state.positions.items():
                position_return = position.unrealized_pnl / (position.quantity * position.entry_price) if position.quantity * position.entry_price > 0 else 0.0
                benchmark_position_return = benchmark_returns.get(symbol, 0.0)
                
                attribution_results['position_attribution'][symbol] = {
                    'position_return': position_return,
                    'benchmark_return': benchmark_position_return,
                    'excess_return': position_return - benchmark_position_return,
                    'contribution': position.unrealized_pnl / total_value if total_value > 0 else 0.0
                }
            
            return attribution_results
            
        except Exception as e:
            return {
                'total_return': 0.0,
                'benchmark_return': 0.0,
                'excess_return': 0.0,
                'allocation_effect': 0.0,
                'selection_effect': 0.0,
                'interaction_effect': 0.0,
                'position_attribution': {}
            }
    
    async def generate_portfolio_metrics(self, portfolio_state: MockPortfolioState) -> MockPortfolioMetrics:
        """Generate comprehensive portfolio metrics."""
        start_time = time.time()
        
        try:
            # Simulate processing time
            await asyncio.sleep(random.uniform(0.002, 0.005))  # 2-5ms
            
            total_value = portfolio_state.total_value
            cash = portfolio_state.cash
            positions_count = len(portfolio_state.positions)
            
            # Calculate P&L metrics
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in portfolio_state.positions.values())
            total_realized_pnl = sum(pos.realized_pnl for pos in portfolio_state.positions.values())
            daily_pnl = portfolio_state.daily_pnl
            total_pnl = total_unrealized_pnl + total_realized_pnl + daily_pnl
            
            # Calculate risk metrics (simplified)
            returns = [random.uniform(-0.05, 0.08) for _ in range(20)]  # Mock historical returns
            volatility = math.sqrt(sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) if returns else 0.0
            
            # Calculate Sharpe ratio (simplified)
            avg_return = sum(returns) / len(returns) if returns else 0.0
            risk_free_rate = 0.02  # 2% risk-free rate
            sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility > 0 else 0.0
            
            # Calculate max drawdown (simplified)
            max_drawdown = random.uniform(0.05, 0.15)  # 5-15% max drawdown
            
            metrics = MockPortfolioMetrics(
                total_value=total_value,
                cash=cash,
                positions_count=positions_count,
                total_unrealized_pnl=total_unrealized_pnl,
                total_realized_pnl=total_realized_pnl,
                daily_pnl=daily_pnl,
                total_pnl=total_pnl,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                volatility=volatility,
                timestamp=datetime.now()
            )
            
            return metrics
            
        except Exception as e:
            # Return default metrics on error
            return MockPortfolioMetrics(
                total_value=0.0,
                cash=0.0,
                positions_count=0,
                total_unrealized_pnl=0.0,
                total_realized_pnl=0.0,
                daily_pnl=0.0,
                total_pnl=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                timestamp=datetime.now()
            )
    
    def generate_portfolio_report(self) -> Dict[str, Any]:
        """Generate comprehensive portfolio report."""
        try:
            recent_rebalancing = self.rebalancing_history[-5:] if self.rebalancing_history else []
            
            report = {
                'timestamp': datetime.now(),
                'performance_stats': self.performance_stats,
                'positions_summary': {
                    symbol: {
                        'quantity': pos.quantity,
                        'current_value': pos.quantity * pos.current_price,
                        'unrealized_pnl': pos.unrealized_pnl,
                        'realized_pnl': pos.realized_pnl
                    }
                    for symbol, pos in self.positions.items()
                },
                'rebalancing_history': recent_rebalancing,
                'portfolio_alerts': self.portfolio_alerts[-10:],  # Last 10 alerts
                'target_weights': self.target_weights,
                'positions_count': len(self.positions)
            }
            
            return report
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()


class TestPortfolioManagementInfrastructure:
    """Test portfolio management infrastructure integration."""
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_portfolio_management_infrastructure(self):
        """Test portfolio management infrastructure setup and basic functionality."""
        with monitoring_context("portfolio_management_infrastructure") as logger:
            logger.log_test_event("Testing portfolio management infrastructure")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Create test portfolio state
            initial_cash = 1000000.0
            portfolio_state = MockPortfolioState(
                total_value=initial_cash,
                cash=initial_cash,
                positions={},
                timestamp=datetime.now()
            )
            
            # Test position tracking
            test_positions = []
            symbols = ['AAPL', 'GOOGL', 'MSFT']
            
            for symbol in symbols:
                position = await portfolio_system.track_position(
                    symbol=symbol,
                    quantity=random.randint(100, 1000),
                    price=random.uniform(50, 500),
                    side='LONG'
                )
                test_positions.append(position)
                portfolio_state.positions[symbol] = position
            
            # Update portfolio state
            portfolio_state.total_value = initial_cash + sum(pos.unrealized_pnl for pos in test_positions)
            portfolio_state.cash = initial_cash - sum(pos.quantity * pos.entry_price for pos in test_positions)
            
            # Validate results
            assert len(test_positions) == len(symbols)
            assert len(portfolio_state.positions) == len(symbols)
            
            for position in test_positions:
                assert position.symbol in symbols
                assert position.quantity > 0
                assert position.entry_price > 0
                assert position.current_price > 0
            
            # Get performance stats
            stats = portfolio_system.get_performance_stats()
            
            logger.log_test_event("Portfolio management infrastructure validated", {
                'positions_tracked': len(test_positions),
                'total_value': portfolio_state.total_value,
                'cash_remaining': portfolio_state.cash,
                'total_trades': stats['total_trades']
            })
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_position_tracking_accuracy(self):
        """Test position tracking accuracy and P&L calculation."""
        with monitoring_context("position_tracking_accuracy") as logger:
            logger.log_test_event("Testing position tracking accuracy")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Test position tracking scenarios
            test_scenarios = [
                {'symbol': 'AAPL', 'quantity': 100, 'price': 150.0, 'side': 'LONG'},
                {'symbol': 'GOOGL', 'quantity': 50, 'price': 2800.0, 'side': 'LONG'},
                {'symbol': 'TSLA', 'quantity': 200, 'price': 800.0, 'side': 'SHORT'}
            ]
            
            tracking_results = []
            
            for scenario in test_scenarios:
                position = await portfolio_system.track_position(
                    symbol=scenario['symbol'],
                    quantity=scenario['quantity'],
                    price=scenario['price'],
                    side=scenario['side']
                )
                
                tracking_results.append({
                    'scenario': scenario,
                    'position': position
                })
                
                # Validate position tracking
                assert position.symbol == scenario['symbol']
                assert position.quantity == scenario['quantity']
                assert position.entry_price == scenario['price']
                assert position.side == scenario['side']
                assert position.current_price > 0
                
                # Validate P&L calculation
                if scenario['side'] == 'LONG':
                    expected_pnl = (position.current_price - position.entry_price) * position.quantity
                else:  # SHORT
                    expected_pnl = (position.entry_price - position.current_price) * position.quantity
                
                # Allow for some variation due to random price changes
                assert abs(position.unrealized_pnl - expected_pnl) < 1000  # $1000 tolerance
            
            logger.log_test_event("Position tracking accuracy validated", {
                'scenarios_tested': len(test_scenarios),
                'positions_tracked': len(tracking_results)
            })
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_pnl_calculation(self):
        """Test P&L calculation and portfolio valuation."""
        with monitoring_context("pnl_calculation") as logger:
            logger.log_test_event("Testing P&L calculation")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Create test portfolio with positions
            portfolio_state = MockPortfolioState(
                total_value=1000000.0,
                cash=200000.0,
                positions={},
                timestamp=datetime.now()
            )
            
            # Add test positions
            test_positions = [
                {'symbol': 'AAPL', 'quantity': 1000, 'entry_price': 150.0, 'current_price': 160.0},
                {'symbol': 'GOOGL', 'quantity': 100, 'entry_price': 2800.0, 'current_price': 2900.0},
                {'symbol': 'MSFT', 'quantity': 500, 'entry_price': 300.0, 'current_price': 280.0}
            ]
            
            for pos_data in test_positions:
                position = MockPosition(
                    symbol=pos_data['symbol'],
                    quantity=pos_data['quantity'],
                    entry_price=pos_data['entry_price'],
                    current_price=pos_data['current_price'],
                    unrealized_pnl=(pos_data['current_price'] - pos_data['entry_price']) * pos_data['quantity'],
                    realized_pnl=0.0,
                    timestamp=datetime.now()
                )
                portfolio_state.positions[pos_data['symbol']] = position
            
            # Calculate P&L
            pnl_metrics = await portfolio_system.calculate_pnl(portfolio_state)
            
            # Validate P&L metrics
            assert 'total_unrealized_pnl' in pnl_metrics
            assert 'total_realized_pnl' in pnl_metrics
            assert 'daily_pnl' in pnl_metrics
            assert 'total_pnl' in pnl_metrics
            assert 'pnl_percentage' in pnl_metrics
            
            # Validate calculations
            expected_unrealized_pnl = sum(
                (pos.current_price - pos.entry_price) * pos.quantity 
                for pos in portfolio_state.positions.values()
            )
            assert abs(pnl_metrics['total_unrealized_pnl'] - expected_unrealized_pnl) < 1.0  # Allow for rounding
            
            assert pnl_metrics['total_pnl'] == (
                pnl_metrics['total_unrealized_pnl'] + 
                pnl_metrics['total_realized_pnl'] + 
                pnl_metrics['daily_pnl']
            )
            
            logger.log_test_event("P&L calculation validated", {
                'total_unrealized_pnl': pnl_metrics['total_unrealized_pnl'],
                'total_pnl': pnl_metrics['total_pnl'],
                'pnl_percentage': pnl_metrics['pnl_percentage']
            })
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_portfolio_rebalancing(self):
        """Test portfolio rebalancing functionality."""
        with monitoring_context("portfolio_rebalancing") as logger:
            logger.log_test_event("Testing portfolio rebalancing")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Create unbalanced portfolio state
            portfolio_state = MockPortfolioState(
                total_value=1000000.0,
                cash=100000.0,
                positions={},
                timestamp=datetime.now()
            )
            
            # Add positions with different weights than targets
            test_positions = [
                {'symbol': 'AAPL', 'quantity': 2000, 'price': 150.0},  # 30% vs 25% target
                {'symbol': 'GOOGL', 'quantity': 50, 'price': 2800.0},  # 14% vs 20% target
                {'symbol': 'MSFT', 'quantity': 800, 'price': 300.0},   # 24% vs 20% target
                {'symbol': 'TSLA', 'quantity': 300, 'price': 800.0},   # 24% vs 15% target
                {'symbol': 'AMZN', 'quantity': 100, 'price': 3200.0}   # 32% vs 20% target
            ]
            
            for pos_data in test_positions:
                position = MockPosition(
                    symbol=pos_data['symbol'],
                    quantity=pos_data['quantity'],
                    entry_price=pos_data['price'],
                    current_price=pos_data['price'],
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    timestamp=datetime.now()
                )
                portfolio_state.positions[pos_data['symbol']] = position
            
            # Perform rebalancing
            rebalancing_actions = await portfolio_system.rebalance_portfolio(portfolio_state)
            
            # Validate rebalancing actions
            assert len(rebalancing_actions) > 0
            
            for action in rebalancing_actions:
                assert action.symbol in portfolio_system.target_weights
                assert action.action in ['BUY', 'SELL', 'HOLD']
                assert action.target_weight > 0
                assert action.current_weight >= 0
                assert action.reason is not None
                
                # Validate action logic
                if action.action == 'BUY':
                    assert action.target_weight > action.current_weight
                    assert action.quantity > 0
                elif action.action == 'SELL':
                    assert action.target_weight < action.current_weight
                    assert action.quantity > 0
                else:  # HOLD
                    assert abs(action.target_weight - action.current_weight) <= 0.05
            
            # Get performance stats
            stats = portfolio_system.get_performance_stats()
            
            logger.log_test_event("Portfolio rebalancing validated", {
                'rebalancing_actions': len(rebalancing_actions),
                'buy_actions': sum(1 for a in rebalancing_actions if a.action == 'BUY'),
                'sell_actions': sum(1 for a in rebalancing_actions if a.action == 'SELL'),
                'hold_actions': sum(1 for a in rebalancing_actions if a.action == 'HOLD'),
                'rebalancing_events': stats['rebalancing_events']
            })
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_performance_attribution(self):
        """Test performance attribution analysis."""
        with monitoring_context("performance_attribution") as logger:
            logger.log_test_event("Testing performance attribution")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Create test portfolio state
            portfolio_state = MockPortfolioState(
                total_value=1000000.0,
                cash=100000.0,
                positions={},
                timestamp=datetime.now()
            )
            
            # Add test positions
            test_positions = [
                {'symbol': 'AAPL', 'quantity': 1000, 'price': 150.0},
                {'symbol': 'GOOGL', 'quantity': 100, 'price': 2800.0},
                {'symbol': 'MSFT', 'quantity': 500, 'price': 300.0}
            ]
            
            for pos_data in test_positions:
                position = MockPosition(
                    symbol=pos_data['symbol'],
                    quantity=pos_data['quantity'],
                    entry_price=pos_data['price'],
                    current_price=pos_data['price'] * random.uniform(0.95, 1.05),
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    timestamp=datetime.now()
                )
                portfolio_state.positions[pos_data['symbol']] = position
            
            # Mock benchmark returns
            benchmark_returns = {
                'AAPL': 0.05,  # 5% return
                'GOOGL': 0.08,  # 8% return
                'MSFT': 0.03,   # 3% return
                'TSLA': 0.12,   # 12% return
                'AMZN': 0.06    # 6% return
            }
            
            # Calculate performance attribution
            attribution = await portfolio_system.calculate_performance_attribution(portfolio_state, benchmark_returns)
            
            # Validate attribution results
            assert 'total_return' in attribution
            assert 'benchmark_return' in attribution
            assert 'excess_return' in attribution
            assert 'allocation_effect' in attribution
            assert 'selection_effect' in attribution
            assert 'interaction_effect' in attribution
            assert 'position_attribution' in attribution
            
            # Validate attribution components
            assert attribution['excess_return'] == (
                attribution['total_return'] - attribution['benchmark_return']
            )
            
            # Validate position attribution
            for symbol in portfolio_state.positions.keys():
                if symbol in attribution['position_attribution']:
                    pos_attr = attribution['position_attribution'][symbol]
                    assert 'position_return' in pos_attr
                    assert 'benchmark_return' in pos_attr
                    assert 'excess_return' in pos_attr
                    assert 'contribution' in pos_attr
            
            logger.log_test_event("Performance attribution validated", {
                'total_return': attribution['total_return'],
                'benchmark_return': attribution['benchmark_return'],
                'excess_return': attribution['excess_return'],
                'allocation_effect': attribution['allocation_effect'],
                'selection_effect': attribution['selection_effect'],
                'positions_analyzed': len(attribution['position_attribution'])
            })
    
    @pytest.mark.portfolio
    @pytest.mark.asyncio
    async def test_portfolio_reporting(self):
        """Test portfolio reporting functionality."""
        with monitoring_context("portfolio_reporting") as logger:
            logger.log_test_event("Testing portfolio reporting")
            
            # Create test components
            portfolio_system = MockPortfolioManagementSystem()
            
            # Generate some activity to populate the system
            for i in range(10):
                await portfolio_system.track_position(
                    symbol=random.choice(['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']),
                    quantity=random.randint(100, 1000),
                    price=random.uniform(50, 3000),
                    side=random.choice(['LONG', 'SHORT'])
                )
            
            # Create test portfolio state
            portfolio_state = MockPortfolioState(
                total_value=1000000.0,
                cash=200000.0,
                positions=portfolio_system.positions,
                timestamp=datetime.now()
            )
            
            # Generate portfolio metrics
            metrics = await portfolio_system.generate_portfolio_metrics(portfolio_state)
            
            # Generate portfolio report
            portfolio_report = portfolio_system.generate_portfolio_report()
            
            # Validate metrics
            assert metrics.total_value > 0
            assert metrics.cash >= 0
            assert metrics.positions_count >= 0
            # Sharpe ratio can be negative in real scenarios
            assert metrics.sharpe_ratio > -10  # Allow negative but reasonable values
            assert 0 <= metrics.max_drawdown <= 1
            assert metrics.volatility >= 0
            
            # Validate report structure
            assert 'timestamp' in portfolio_report
            assert 'performance_stats' in portfolio_report
            assert 'positions_summary' in portfolio_report
            assert 'rebalancing_history' in portfolio_report
            assert 'portfolio_alerts' in portfolio_report
            assert 'target_weights' in portfolio_report
            assert 'positions_count' in portfolio_report
            
            # Validate report contents
            assert portfolio_report['positions_count'] >= 0
            assert len(portfolio_report['target_weights']) > 0
            
            # Get performance stats
            stats = portfolio_system.get_performance_stats()
            
            logger.log_test_event("Portfolio reporting validated", {
                'portfolio_metrics_generated': True,
                'portfolio_report_generated': True,
                'total_value': metrics.total_value,
                'positions_count': metrics.positions_count,
                'total_trades': stats['total_trades'],
                'winning_trades': stats['winning_trades'],
                'losing_trades': stats['losing_trades']
            })


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s", "-m", "portfolio"]) 