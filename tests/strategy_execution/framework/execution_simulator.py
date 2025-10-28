"""
Execution Simulator - Realistic Trade Execution Simulation
========================================================

Advanced trade execution simulation engine that models realistic market conditions
including slippage, transaction costs, market impact, and fill rates.

This simulator provides:
- Realistic slippage modeling
- Transaction cost calculation
- Market impact simulation
- Fill rate optimization
- Multi-asset execution coordination
- Institutional execution quality metrics

Key Features:
- Multiple slippage models (fixed, proportional, market impact)
- Institutional transaction cost structures
- Market impact modeling with temporary/permanent components
- Fill rate simulation based on order characteristics
- Cross-market execution coordination
- Performance attribution for execution costs

Author: StatArb_Gemini Phase 7 Strategy Validation
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

# Import strategy components
from core_engine.trading.strategies.strategy_engine import StrategySignal, SignalType

logger = logging.getLogger(__name__)


class SlippageModel(Enum):
    """Slippage calculation models"""

    NONE = "none"                    # No slippage
    FIXED = "fixed"                  # Fixed slippage amount
    PROPORTIONAL = "proportional"    # Slippage proportional to price
    MARKET_IMPACT = "market_impact"  # Price impact based on order size
    REALISTIC = "realistic"          # Combined model with market conditions


class TransactionCostModel(Enum):
    """Transaction cost calculation models"""

    NONE = "none"                    # No transaction costs
    RETAIL = "retail"                # Retail trading costs
    INSTITUTIONAL = "institutional"  # Institutional trading costs
    CUSTOM = "custom"                # Custom cost structure


@dataclass
class ExecutionConfig:
    """Execution configuration parameters"""

    # Slippage settings
    slippage_model: SlippageModel = SlippageModel.REALISTIC
    fixed_slippage_bps: float = 5.0  # 5 basis points
    proportional_slippage_factor: float = 0.001  # 0.1%
    market_impact_factor: float = 0.0001  # Market impact coefficient

    # Transaction cost settings
    cost_model: TransactionCostModel = TransactionCostModel.INSTITUTIONAL
    commission_per_share: float = 0.0035  # $0.0035 per share
    exchange_fee_bps: float = 0.3  # 0.3 basis points
    regulatory_fee_bps: float = 0.0  # No regulatory fee by default

    # Execution quality settings
    max_slippage_bps: float = 50.0  # Maximum acceptable slippage
    min_fill_rate: float = 0.95     # Minimum fill rate requirement
    execution_timeout_seconds: int = 30  # Order timeout

    # Market condition factors
    volatility_multiplier: float = 1.0
    volume_multiplier: float = 1.0
    spread_multiplier: float = 1.0


@dataclass
class ExecutionResult:
    """Result of a single trade execution"""

    signal_id: str
    symbol: str
    signal_type: SignalType
    intended_quantity: float
    executed_quantity: float
    intended_price: float
    executed_price: float
    slippage_bps: float
    transaction_cost: float
    total_cost: float
    execution_time: datetime
    fill_rate: float
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    execution_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionSummary:
    """Summary of execution results"""

    total_signals: int = 0
    executed_trades: int = 0
    failed_trades: int = 0
    total_intended_quantity: float = 0.0
    total_executed_quantity: float = 0.0
    total_transaction_cost: float = 0.0
    average_slippage_bps: float = 0.0
    average_fill_rate: float = 0.0
    execution_success_rate: float = 0.0

    # Performance metrics
    total_pnl: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0

    # Cost analysis
    total_commission: float = 0.0
    total_fees: float = 0.0
    cost_per_share: float = 0.0

    trade_log: List[ExecutionResult] = field(default_factory=list)


class ExecutionSimulator:
    """
    Realistic trade execution simulation engine

    This simulator models institutional-grade trade execution with
    slippage, transaction costs, market impact, and fill rates.
    """

    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()

        # Execution statistics tracking
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_slippage": 0.0,
            "average_fill_rate": 0.0
        }

        logger.info("ExecutionSimulator initialized")

    async def simulate_strategy_execution(
        self,
        strategy_config: Any,
        market_data: Dict[str, pd.DataFrame],
        test_config: Any
    ) -> Dict[str, Any]:
        """
        Simulate complete strategy execution pipeline

        Args:
            strategy_config: Strategy configuration
            market_data: Market data for execution simulation
            test_config: Test configuration parameters

        Returns:
            Dict containing execution simulation results
        """

        logger.info("Starting strategy execution simulation")

        try:
            # Generate synthetic signals for simulation
            # In real usage, these would come from actual strategy
            signals = self._generate_synthetic_signals(strategy_config, market_data)

            if not signals:
                return self._create_empty_execution_result()

            # Execute signals
            execution_results = []
            for signal in signals:
                result = await self._execute_signal(signal, market_data)
                execution_results.append(result)

            # Calculate summary metrics
            summary = self._calculate_execution_summary(execution_results, market_data)

            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(execution_results, market_data)

            # Combine results
            simulation_results = {
                "signals_tested": len(signals),
                "trades_executed": len([r for r in execution_results if r.executed_quantity > 0]),
                "success_rate": summary.execution_success_rate,
                "avg_slippage": summary.average_slippage_bps,
                "avg_cost": summary.cost_per_share,
                "total_pnl": performance_metrics.get("total_pnl", 0.0),
                "sharpe_ratio": performance_metrics.get("sharpe_ratio", 0.0),
                "max_drawdown": performance_metrics.get("max_drawdown", 0.0),
                "trade_log": [self._execution_result_to_dict(r) for r in execution_results],
                "execution_summary": self._summary_to_dict(summary),
                "performance_metrics": performance_metrics
            }

            logger.info(f"Execution simulation completed: {len(execution_results)} trades simulated")

            return simulation_results

        except Exception as e:
            logger.error(f"Execution simulation failed: {e}")
            return {
                "signals_tested": 0,
                "trades_executed": 0,
                "success_rate": 0.0,
                "avg_slippage": 0.0,
                "avg_cost": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "error": str(e)
            }

    async def simulate_single_execution(
        self,
        signal: StrategySignal,
        market_data: Dict[str, pd.DataFrame]
    ) -> ExecutionResult:
        """
        Simulate execution of a single signal

        Args:
            signal: Trading signal to execute
            market_data: Market data for execution context

        Returns:
            ExecutionResult with detailed execution information
        """

        return await self._execute_signal(signal, market_data)

    async def _execute_signal(
        self,
        signal: StrategySignal,
        market_data: Dict[str, pd.DataFrame]
    ) -> ExecutionResult:
        """
        Execute a single trading signal with realistic simulation

        Args:
            signal: Trading signal to execute
            market_data: Market data context

        Returns:
            ExecutionResult with execution details
        """

        symbol = signal.symbol
        signal_type = signal.signal_type
        intended_quantity = signal.target_quantity

        # Get market data for symbol
        if symbol not in market_data:
            return self._create_failed_execution(signal, "No market data available")

        df = market_data[symbol]
        if df.empty:
            return self._create_failed_execution(signal, "Empty market data")

        # Get current market conditions
        current_data = df.iloc[-1]  # Most recent data
        mid_price = (current_data['bid'] + current_data['ask']) / 2 if 'bid' in current_data and 'ask' in current_data else current_data['close']
        spread = (current_data['ask'] - current_data['bid']) / mid_price if 'bid' in current_data and 'ask' in current_data else 0.001

        # Calculate market conditions
        volatility = df['close'].pct_change().std() * np.sqrt(252)  # Annualized volatility
        volume_ratio = current_data.get('volume', 1000000) / df['volume'].mean() if 'volume' in df.columns else 1.0

        market_conditions = {
            "volatility": volatility,
            "volume_ratio": volume_ratio,
            "spread_bps": spread * 10000,
            "liquidity_score": min(volume_ratio, 2.0) / 2.0  # 0-1 scale
        }

        # Determine execution price with slippage
        slippage_bps = self._calculate_slippage(signal, market_conditions)
        slippage_factor = slippage_bps / 10000.0  # Convert bps to decimal

        # Apply slippage based on signal direction
        if signal_type == SignalType.BUY:
            executed_price = mid_price * (1.0 + slippage_factor)
        else:  # SELL
            executed_price = mid_price * (1.0 - slippage_factor)

        # Simulate partial fills (realistic execution)
        fill_rate = self._calculate_fill_rate(signal, market_conditions)
        executed_quantity = intended_quantity * fill_rate

        # Calculate transaction costs
        transaction_cost = self._calculate_transaction_cost(
            executed_quantity, executed_price, market_conditions
        )

        # Create execution result
        result = ExecutionResult(
            signal_id=getattr(signal, 'signal_id', f"signal_{datetime.now().timestamp()}"),
            symbol=symbol,
            signal_type=signal_type,
            intended_quantity=intended_quantity,
            executed_quantity=executed_quantity,
            intended_price=mid_price,
            executed_price=executed_price,
            slippage_bps=slippage_bps,
            transaction_cost=transaction_cost,
            total_cost=transaction_cost + (executed_price * executed_quantity),
            execution_time=datetime.now(),
            fill_rate=fill_rate,
            market_conditions=market_conditions,
            execution_details={
                "order_type": "market",
                "time_in_force": "immediate_or_cancel",
                "execution_model": self.config.slippage_model.value
            }
        )

        # Update execution statistics
        self.execution_stats["total_executions"] += 1
        if executed_quantity > 0:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1

        return result

    def _calculate_slippage(self, signal: StrategySignal, market_conditions: Dict[str, Any]) -> float:
        """Calculate realistic slippage for the trade"""

        base_slippage = 0.0

        if self.config.slippage_model == SlippageModel.NONE:
            return 0.0

        elif self.config.slippage_model == SlippageModel.FIXED:
            base_slippage = self.config.fixed_slippage_bps

        elif self.config.slippage_model == SlippageModel.PROPORTIONAL:
            # Slippage increases with order size and volatility
            size_factor = min(signal.target_quantity / 100000, 1.0)  # Cap at large orders
            volatility_factor = market_conditions.get("volatility", 0.2)
            base_slippage = self.config.proportional_slippage_factor * size_factor * volatility_factor * 10000

        elif self.config.slippage_model == SlippageModel.MARKET_IMPACT:
            # Market impact model: permanent + temporary impact
            order_size_pct = signal.target_quantity / market_conditions.get("daily_volume", 1000000)
            permanent_impact = self.config.market_impact_factor * np.sqrt(order_size_pct) * 10000
            temporary_impact = permanent_impact * 0.5  # Temporary impact is smaller
            base_slippage = permanent_impact + temporary_impact

        elif self.config.slippage_model == SlippageModel.REALISTIC:
            # Combined realistic model
            fixed_component = self.config.fixed_slippage_bps * 0.3
            proportional_component = self._calculate_slippage_proportional(signal, market_conditions)
            impact_component = self._calculate_market_impact(signal, market_conditions)
            base_slippage = fixed_component + proportional_component + impact_component

        # Apply market condition multipliers
        volatility_mult = 1.0 + (market_conditions.get("volatility", 0.2) - 0.2) * 2.0
        volume_mult = 1.0 / max(market_conditions.get("liquidity_score", 0.5), 0.1)
        spread_mult = 1.0 + market_conditions.get("spread_bps", 10.0) / 10.0

        adjusted_slippage = base_slippage * volatility_mult * volume_mult * spread_mult

        # Add randomness for realism
        random_factor = np.random.normal(1.0, 0.2)
        final_slippage = adjusted_slippage * random_factor

        # Ensure slippage is within bounds
        final_slippage = max(0.0, min(final_slippage, self.config.max_slippage_bps))

        return final_slippage

    def _calculate_slippage_proportional(self, signal: StrategySignal, market_conditions: Dict[str, Any]) -> float:
        """Calculate proportional slippage component"""

        size_factor = min(signal.target_quantity / 100000, 1.0)
        volatility_factor = market_conditions.get("volatility", 0.2)
        return self.config.proportional_slippage_factor * size_factor * volatility_factor * 10000

    def _calculate_market_impact(self, signal: StrategySignal, market_conditions: Dict[str, Any]) -> float:
        """Calculate market impact component"""

        # Estimate daily volume
        daily_volume = market_conditions.get("daily_volume", 1000000)
        order_size_pct = signal.target_quantity / daily_volume

        # Square root market impact model
        permanent_impact = self.config.market_impact_factor * np.sqrt(order_size_pct) * 10000
        temporary_impact = permanent_impact * 0.3  # Temporary impact

        return permanent_impact + temporary_impact

    def _calculate_fill_rate(self, signal: StrategySignal, market_conditions: Dict[str, Any]) -> float:
        """Calculate realistic fill rate for the order"""

        base_fill_rate = 1.0

        # Fill rate decreases with order size and volatility
        size_factor = min(signal.target_quantity / 500000, 1.0)  # Very large orders harder to fill
        volatility_factor = market_conditions.get("volatility", 0.2)
        liquidity_factor = market_conditions.get("liquidity_score", 0.5)

        # Calculate fill rate reduction
        size_penalty = size_factor * 0.1  # Up to 10% reduction for large orders
        volatility_penalty = volatility_factor * 0.05  # Up to 5% reduction for high volatility
        liquidity_bonus = (liquidity_factor - 0.5) * 0.1  # Bonus for high liquidity

        fill_rate = base_fill_rate - size_penalty - volatility_penalty + liquidity_bonus

        # Add randomness
        random_factor = np.random.normal(0.0, 0.02)
        fill_rate += random_factor

        # Ensure fill rate is within realistic bounds
        fill_rate = max(0.85, min(fill_rate, 1.0))  # Between 85% and 100%

        return fill_rate

    def _calculate_transaction_cost(
        self,
        quantity: float,
        price: float,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate total transaction costs"""

        if self.config.cost_model == TransactionCostModel.NONE:
            return 0.0

        total_cost = 0.0
        notional_value = quantity * price

        if self.config.cost_model == TransactionCostModel.RETAIL:
            # Retail costs: higher commissions
            commission = quantity * 0.01  # $0.01 per share
            exchange_fee = notional_value * (self.config.exchange_fee_bps / 10000.0)
            total_cost = commission + exchange_fee

        elif self.config.cost_model == TransactionCostModel.INSTITUTIONAL:
            # Institutional costs: lower commissions, higher exchange fees
            commission = quantity * self.config.commission_per_share
            exchange_fee = notional_value * (self.config.exchange_fee_bps / 10000.0)
            regulatory_fee = notional_value * (self.config.regulatory_fee_bps / 10000.0)
            total_cost = commission + exchange_fee + regulatory_fee

        elif self.config.cost_model == TransactionCostModel.CUSTOM:
            # Custom cost model - extend as needed
            total_cost = quantity * 0.005  # Default custom rate

        # Apply market condition adjustments
        volatility_mult = 1.0 + (market_conditions.get("volatility", 0.2) - 0.2) * 0.5
        total_cost *= volatility_mult

        return total_cost

    def _calculate_execution_summary(self, execution_results: List[ExecutionResult], market_data: Dict[str, pd.DataFrame]) -> ExecutionSummary:
        """Calculate comprehensive execution summary"""

        summary = ExecutionSummary()

        if not execution_results:
            return summary

        summary.total_signals = len(execution_results)
        summary.executed_trades = len([r for r in execution_results if r.executed_quantity > 0])
        summary.failed_trades = summary.total_signals - summary.executed_trades

        # Calculate aggregate metrics
        executed_results = [r for r in execution_results if r.executed_quantity > 0]

        if executed_results:
            summary.total_intended_quantity = sum(r.intended_quantity for r in execution_results)
            summary.total_executed_quantity = sum(r.executed_quantity for r in executed_results)
            summary.total_transaction_cost = sum(r.transaction_cost for r in executed_results)

            summary.average_slippage_bps = np.mean([r.slippage_bps for r in executed_results])
            summary.average_fill_rate = np.mean([r.fill_rate for r in executed_results])
            summary.execution_success_rate = summary.executed_trades / summary.total_signals

            summary.cost_per_share = summary.total_transaction_cost / summary.total_executed_quantity if summary.total_executed_quantity > 0 else 0.0

        summary.trade_log = execution_results

        return summary

    def _calculate_performance_metrics(self, execution_results: List[ExecutionResult], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate performance metrics from execution results"""

        if not execution_results:
            return {}

        try:
            # Simple P&L calculation (would be more sophisticated in real implementation)
            total_pnl = 0.0
            returns = []

            for result in execution_results:
                if result.executed_quantity > 0:
                    # Simplified P&L - in reality would track entry/exit prices over time
                    trade_pnl = (result.executed_price - result.intended_price) * result.executed_quantity * (1 if result.signal_type == SignalType.BUY else -1)
                    trade_pnl -= result.transaction_cost
                    total_pnl += trade_pnl

                    # Calculate return for Sharpe ratio
                    if result.intended_price != 0:
                        trade_return = trade_pnl / (result.intended_price * result.executed_quantity)
                        returns.append(trade_return)

            # Calculate Sharpe ratio
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0

            # Calculate max drawdown (simplified)
            cumulative_returns = np.cumsum(returns) if returns else [0]
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = running_max - cumulative_returns
            max_drawdown = np.max(drawdowns) if drawdowns.size > 0 else 0.0

            return {
                "total_pnl": total_pnl,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "win_rate": len([r for r in returns if r > 0]) / len(returns) if returns else 0.0,
                "total_trades": len(execution_results),
                "profitable_trades": len([r for r in returns if r > 0])
            }

        except Exception as e:
            logger.warning(f"Performance calculation error: {e}")
            return {
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "error": str(e)
            }

    def _generate_synthetic_signals(self, strategy_config: Any, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Generate synthetic signals for testing (placeholder)"""

        signals = []
        signal_count = 100  # Generate 100 test signals

        for i in range(signal_count):
            # Randomly select symbol and signal type
            symbol = np.random.choice(list(market_data.keys())) if market_data else "AAPL"
            signal_type = np.random.choice([SignalType.BUY, SignalType.SELL])

            # Create synthetic signal
            signal = StrategySignal(
                signal_id=f"synthetic_{i}",
                strategy_id=getattr(strategy_config, 'strategy_id', 'test_strategy'),
                symbol=symbol,
                signal_type=signal_type,
                confidence=np.random.uniform(0.5, 0.9),
                strength=np.random.uniform(0.4, 0.8),
                target_quantity=np.random.uniform(1000, 10000),
                timestamp=datetime.now() - timedelta(minutes=np.random.randint(1, 1000))
            )

            signals.append(signal)

        return signals

    def _create_failed_execution(self, signal: StrategySignal, reason: str) -> ExecutionResult:
        """Create execution result for failed trade"""

        return ExecutionResult(
            signal_id=getattr(signal, 'signal_id', 'unknown'),
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            intended_quantity=signal.target_quantity,
            executed_quantity=0.0,
            intended_price=0.0,
            executed_price=0.0,
            slippage_bps=0.0,
            transaction_cost=0.0,
            total_cost=0.0,
            execution_time=datetime.now(),
            fill_rate=0.0,
            execution_details={"failure_reason": reason}
        )

    def _execution_result_to_dict(self, result: ExecutionResult) -> Dict[str, Any]:
        """Convert execution result to dictionary"""

        return {
            "signal_id": result.signal_id,
            "symbol": result.symbol,
            "signal_type": result.signal_type.value,
            "intended_quantity": result.intended_quantity,
            "executed_quantity": result.executed_quantity,
            "intended_price": result.intended_price,
            "executed_price": result.executed_price,
            "slippage_bps": result.slippage_bps,
            "transaction_cost": result.transaction_cost,
            "total_cost": result.total_cost,
            "execution_time": result.execution_time.isoformat(),
            "fill_rate": result.fill_rate,
            "market_conditions": result.market_conditions,
            "execution_details": result.execution_details
        }

    def _summary_to_dict(self, summary: ExecutionSummary) -> Dict[str, Any]:
        """Convert execution summary to dictionary"""

        return {
            "total_signals": summary.total_signals,
            "executed_trades": summary.executed_trades,
            "failed_trades": summary.failed_trades,
            "execution_success_rate": summary.execution_success_rate,
            "average_slippage_bps": summary.average_slippage_bps,
            "average_fill_rate": summary.average_fill_rate,
            "total_transaction_cost": summary.total_transaction_cost,
            "cost_per_share": summary.cost_per_share,
            "total_pnl": summary.total_pnl,
            "sharpe_ratio": summary.sharpe_ratio,
            "max_drawdown": summary.max_drawdown
        }

    def _create_empty_execution_result(self) -> Dict[str, Any]:
        """Create empty execution result"""

        return {
            "signals_tested": 0,
            "trades_executed": 0,
            "success_rate": 0.0,
            "avg_slippage": 0.0,
            "avg_cost": 0.0,
            "total_pnl": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "trade_log": [],
            "message": "No signals to execute"
        }