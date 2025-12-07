"""
Momentum Strategy Backtest
===========================

Comprehensive backtest of EnhancedMomentumStrategy with lowered threshold (composite_z_entry=0.3).

Test Configuration:
- Symbol: TSLA
- Period: November 2024 (full month)
- Timeframe: 1-minute bars
- Initial Capital: $100,000
- Strategy: Enhanced Momentum with composite signals

Performance Metrics Calculated:
- Total Return (%)
- Sharpe Ratio
- Max Drawdown (%)
- Win Rate (%)
- Profit Factor
- Total Trades
- Average Trade Duration
- Best/Worst Trade
- Risk-Adjusted Returns

Author: StatArb_Gemini Backtest Suite
Date: November 18, 2025
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import core engine components
from core_engine.config import (
    DataConfig, RegimeConfig, IndicatorConfig,
    FeatureConfig, SignalConfig, MomentumConfig, RiskConfig
)
from core_engine.data.manager import ClickHouseDataManager
from core_engine.regime.engine import EnhancedRegimeEngine
from core_engine.processing.pipeline_orchestrator import ProcessingPipelineOrchestrator
from core_engine.trading.strategies.implementations.momentum.enhanced_momentum import EnhancedMomentumStrategy
from core_engine.system.central_risk_manager import CentralRiskManager
from core_engine.trading.strategies.strategy_engine import SignalType


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    duration_minutes: int
    entry_reason: str = ""
    exit_reason: str = ""


@dataclass
class BacktestResults:
    """Backtest performance metrics"""

    # Capital and Returns
    initial_capital: float = 100000.0
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    total_pnl: float = 0.0

    # Trade Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0

    # P&L Statistics
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    profit_factor: float = 0.0
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0

    # Risk Metrics
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: float = 0.0

    # Trade Duration
    avg_trade_duration_minutes: float = 0.0

    # Trade Breakdown
    long_trades: int = 0
    short_trades: int = 0
    long_win_rate_pct: float = 0.0
    short_win_rate_pct: float = 0.0

    # Detailed trades
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)


class MomentumBacktest:
    """
    Backtest engine for Momentum Strategy
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_per_trade: float = 1.0  # $1 per trade (very low for testing)
    ):
        self.initial_capital = initial_capital
        self.commission_per_trade = commission_per_trade
        self.current_capital = initial_capital

        # Trading state
        self.current_position = None  # Currently open position
        self.completed_trades = []
        self.equity_curve = []

        # Components (will be initialized)
        self.data_manager = None
        self.regime_engine = None
        self.pipeline = None
        self.strategy = None
        self.risk_manager = None

    async def initialize_components(self):
        """Initialize all trading components"""
        logger.info("🚀 Initializing backtest components...")

        # Data Manager
        self.data_manager = ClickHouseDataManager(DataConfig())
        await self.data_manager.initialize()
        await self.data_manager.start()
        logger.info("   ✅ Data Manager initialized")

        # Regime Engine
        self.regime_engine = EnhancedRegimeEngine(RegimeConfig())
        await self.regime_engine.initialize()
        await self.regime_engine.start()
        logger.info("   ✅ Regime Engine initialized")

        # Processing Pipeline
        self.pipeline = ProcessingPipelineOrchestrator(
            data_config=DataConfig(),
            indicator_config=IndicatorConfig(),
            feature_config=FeatureConfig(),
            signal_config=SignalConfig()
        )
        await self.pipeline.initialize()
        await self.pipeline.start()
        logger.info("   ✅ Processing Pipeline initialized")

        # Momentum Strategy (with ORIGINAL threshold + better filters)
        momentum_config = MomentumConfig(
            symbols=['TSLA'],
            composite_z_entry=0.5,  # RESTORED to original
            composite_pct_entry=70.0,
            scan_all_bars=False  # Bar-by-bar mode
        )
        self.strategy = EnhancedMomentumStrategy(momentum_config)
        await self.strategy.initialize()
        logger.info("   ✅ Momentum Strategy initialized (composite_z_entry=0.5 - ORIGINAL)")

        # Risk Manager
        self.risk_manager = CentralRiskManager(RiskConfig())
        await self.risk_manager.initialize()
        await self.risk_manager.start()
        logger.info("   ✅ Risk Manager initialized")

    async def run_backtest(
        self,
        symbol: str = 'TSLA',
        start_date: str = '2024-11-01',
        end_date: str = '2024-11-30'
    ) -> BacktestResults:
        """
        Run complete backtest

        Args:
            symbol: Trading symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            BacktestResults with performance metrics
        """
        logger.info("=" * 80)
        logger.info("🎯 MOMENTUM STRATEGY BACKTEST - IMPROVED VERSION")
        logger.info("=" * 80)
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"")
        logger.info(f"Strategy Improvements:")
        logger.info(f"  • Entry Threshold: composite_z_entry=0.5 (RESTORED to original)")
        logger.info(f"  • Entry Filters: ADX>25, Volume>1.0, RSI not extreme")
        logger.info(f"  • Exit Logic: Min hold 5min, 2% profit target, -1% stop loss")
        logger.info(f"  • Time Stop: 90 minutes max hold")
        logger.info("=" * 80)

        try:
            # Initialize components
            await self.initialize_components()

            # Load historical data
            logger.info(f"\n📊 Loading historical data for {symbol}...")
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

            raw_data = self.data_manager.get_market_data(
                symbol=symbol,
                start_time=start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                end_time=end_dt.strftime('%Y-%m-%d %H:%M:%S')
            )

            if raw_data is None or raw_data.empty:
                logger.error("❌ No data loaded - cannot run backtest")
                return BacktestResults(initial_capital=self.initial_capital)

            logger.info(f"✅ Loaded {len(raw_data)} bars ({raw_data.index[0]} to {raw_data.index[-1]})")

            # Process data through pipeline
            logger.info("\n⚙️  Processing data through pipeline...")
            enriched_data = await self.pipeline.process_market_data(
                symbols=[symbol],
                start_time=start_dt,
                end_time=end_dt,
                timeframe='1min'
            )

            if symbol not in enriched_data:
                logger.error(f"❌ No enriched data for {symbol}")
                return BacktestResults(initial_capital=self.initial_capital)

            full_df = enriched_data[symbol].get_enriched_dataframe()
            logger.info(f"✅ Processed {len(full_df)} bars through pipeline")

            # Bar-by-bar simulation
            logger.info("\n🔄 Running bar-by-bar simulation...")
            start_bar = 60  # Need enough data for indicators
            total_bars = len(full_df)

            signals_generated = 0
            bars_processed = 0

            for current_bar_idx in range(start_bar, total_bars):
                # Get data up to current bar (simulate live trading)
                historical_df = full_df.iloc[:current_bar_idx + 1].copy()

                # Generate signals from strategy
                strategy_data = {symbol: historical_df}
                signals = await self.strategy.generate_signals(strategy_data)

                if signals:
                    signals_generated += len(signals)

                    for signal in signals:
                        await self._process_signal(signal, historical_df)

                # Check if we need to close position (exit logic)
                if self.current_position:
                    await self._check_exit_conditions(historical_df, current_bar_idx)

                bars_processed += 1

                # Progress logging every 1000 bars
                if bars_processed % 1000 == 0:
                    pct_complete = (current_bar_idx / total_bars) * 100
                    logger.info(f"   Progress: {pct_complete:.1f}% ({current_bar_idx}/{total_bars} bars)")

            logger.info(f"✅ Simulation complete: {bars_processed} bars processed, {signals_generated} signals generated")

            # Close any open position at end
            if self.current_position:
                logger.info("\n🔚 Closing open position at end of backtest...")
                await self._close_position(
                    exit_price=full_df.iloc[-1]['close'],
                    exit_time=full_df.index[-1],
                    exit_reason="End of backtest period"
                )

            # Calculate results
            results = self._calculate_results()

            # Display results
            self._display_results(results)

            return results

        finally:
            # Cleanup
            await self._cleanup()

    async def _process_signal(self, signal, historical_df: pd.DataFrame):
        """
        Process a trading signal with additional filters

        IMPROVED FILTERS:
        1. Check if we already have a position (one at a time)
        2. Require ADX > 25 (trending market filter)
        3. Require volume_ratio > 1.0 (volume confirmation)
        4. Check RSI not overbought/oversold (RSI filter)
        """

        # Filter 1: If we already have a position, skip
        if self.current_position:
            return

        current_bar = historical_df.iloc[-1]
        current_price = current_bar['close']
        current_time = historical_df.index[-1]

        # FILTER 2: ADX > 25 (trending market)
        adx = current_bar.get('adx', 0)
        if adx < 25:
            logger.debug(f"   🚫 Signal filtered: ADX {adx:.1f} < 25 (not trending)")
            return

        # FILTER 3: Volume confirmation (volume_ratio > 1.0)
        volume_ratio = current_bar.get('volume_ratio', 1.0)
        if volume_ratio < 1.0:
            logger.debug(f"   🚫 Signal filtered: volume_ratio {volume_ratio:.2f} < 1.0 (low volume)")
            return

        # FILTER 4: RSI not extreme (avoid overbought/oversold)
        rsi = current_bar.get('rsi', 50)
        if signal.signal_type == SignalType.BUY and rsi > 70:
            logger.debug(f"   🚫 LONG signal filtered: RSI {rsi:.1f} > 70 (overbought)")
            return
        if signal.signal_type == SignalType.SELL and rsi < 30:
            logger.debug(f"   🚫 SHORT signal filtered: RSI {rsi:.1f} < 30 (oversold)")
            return

        # Determine position size (use 90% of available capital)
        position_value = self.current_capital * 0.90
        quantity = int(position_value / current_price)

        if quantity <= 0:
            return

        # Open position
        self.current_position = {
            'symbol': signal.symbol,
            'side': 'long' if signal.signal_type == SignalType.BUY else 'short',
            'entry_price': current_price,
            'entry_time': current_time,
            'quantity': quantity,
            'entry_capital': self.current_capital,
            'entry_bar_idx': len(historical_df) - 1  # Track entry bar index
        }

        # Deduct commission
        self.current_capital -= self.commission_per_trade

        logger.info(f"   📈 OPEN {self.current_position['side'].upper()} position: "
                   f"{quantity} shares @ ${current_price:.2f} "
                   f"(ADX={adx:.1f}, Vol={volume_ratio:.2f}, RSI={rsi:.1f})")

    async def _check_exit_conditions(self, historical_df: pd.DataFrame, current_bar_idx: int):
        """
        Check if position should be closed

        IMPROVED EXIT LOGIC:
        1. Minimum holding period: 5 minutes (reduce churn)
        2. Use ATR-based stops (more adaptive)
        3. Time-based exit: 90 minutes max
        4. Profit target: 2% (take profits)
        5. Stop loss: -1% (cut losses)
        """

        if not self.current_position:
            return

        current_bar = historical_df.iloc[-1]
        current_price = current_bar['close']
        current_time = historical_df.index[-1]

        pos = self.current_position
        entry_bar_idx = pos.get('entry_bar_idx', current_bar_idx - 1)
        bars_held = current_bar_idx - entry_bar_idx

        # Handle both datetime and integer indices for duration
        if isinstance(current_time, (int, np.integer)) and isinstance(pos['entry_time'], (int, np.integer)):
            duration_minutes = current_time - pos['entry_time']  # Assume index is in minutes
        else:
            duration_minutes = (current_time - pos['entry_time']).total_seconds() / 60

        # EXIT FILTER 1: Minimum holding period (5 minutes)
        if duration_minutes < 5:
            return  # Don't exit too quickly

        # Calculate current P&L
        if pos['side'] == 'long':
            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        else:  # short
            pnl_pct = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100

        should_exit = False
        exit_reason = ""

        # EXIT CONDITION 1: Profit target (2%)
        if pnl_pct >= 2.0:
            should_exit = True
            exit_reason = f"Profit target hit ({pnl_pct:+.2f}%)"

        # EXIT CONDITION 2: Stop loss (-1%)
        elif pnl_pct <= -1.0:
            should_exit = True
            exit_reason = f"Stop loss hit ({pnl_pct:+.2f}%)"

        # EXIT CONDITION 3: Time stop (90 minutes)
        elif duration_minutes > 90:
            should_exit = True
            exit_reason = f"Time stop ({duration_minutes:.0f} min)"

        # EXIT CONDITION 4: Momentum reversal (composite signals)
        else:
            composite_z = current_bar.get('composite_z', 0)
            composite_pct = current_bar.get('composite_pct', 50)

            if pos['side'] == 'long':
                # Exit LONG if momentum turns negative
                if composite_z < 0.3:  # Below entry threshold
                    should_exit = True
                    exit_reason = f"Momentum weakened (z={composite_z:.2f})"
            else:  # short
                # Exit SHORT if momentum turns positive
                if composite_z > -0.3:  # Above entry threshold (negative)
                    should_exit = True
                    exit_reason = f"Momentum weakened (z={composite_z:.2f})"

        if should_exit:
            await self._close_position(current_price, current_time, exit_reason)

    async def _close_position(self, exit_price: float, exit_time: datetime, exit_reason: str):
        """Close current position"""

        if not self.current_position:
            return

        pos = self.current_position
        quantity = pos['quantity']

        # Calculate P&L
        if pos['side'] == 'long':
            pnl = (exit_price - pos['entry_price']) * quantity
        else:  # short
            pnl = (pos['entry_price'] - exit_price) * quantity

        # Deduct commission
        pnl -= self.commission_per_trade

        # Update capital
        self.current_capital += pnl

        # Calculate metrics
        pnl_pct = (pnl / (pos['entry_price'] * quantity)) * 100

        # Handle both datetime and integer indices for duration
        if isinstance(exit_time, (int, np.integer)) and isinstance(pos['entry_time'], (int, np.integer)):
            duration_minutes = int(exit_time - pos['entry_time'])  # Assume index is in minutes
        else:
            duration_minutes = int((exit_time - pos['entry_time']).total_seconds() / 60)

        # Record trade
        trade = Trade(
            entry_time=pos['entry_time'],
            exit_time=exit_time,
            symbol=pos['symbol'],
            side=pos['side'],
            entry_price=pos['entry_price'],
            exit_price=exit_price,
            quantity=quantity,
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_minutes=duration_minutes,
            exit_reason=exit_reason
        )

        self.completed_trades.append(trade)

        # Record equity point
        self.equity_curve.append({
            'time': exit_time,
            'equity': self.current_capital,
            'trade_pnl': pnl,
            'trade_pnl_pct': pnl_pct
        })

        logger.debug(f"   📉 CLOSE {pos['side'].upper()} position: "
                    f"P&L=${pnl:,.2f} ({pnl_pct:+.2f}%) - {exit_reason}")

        # Clear position
        self.current_position = None

    def _calculate_results(self) -> BacktestResults:
        """Calculate backtest performance metrics"""

        results = BacktestResults(
            initial_capital=self.initial_capital,
            final_capital=self.current_capital,
            trades=self.completed_trades,
            equity_curve=self.equity_curve
        )

        if not self.completed_trades:
            logger.warning("⚠️  No trades completed during backtest")
            return results

        # Basic metrics
        results.total_trades = len(self.completed_trades)
        results.total_pnl = self.current_capital - self.initial_capital
        results.total_return_pct = (results.total_pnl / self.initial_capital) * 100

        # Win/Loss statistics
        winning_trades = [t for t in self.completed_trades if t.pnl > 0]
        losing_trades = [t for t in self.completed_trades if t.pnl <= 0]

        results.winning_trades = len(winning_trades)
        results.losing_trades = len(losing_trades)
        results.win_rate_pct = (results.winning_trades / results.total_trades) * 100 if results.total_trades > 0 else 0

        # P&L statistics
        if winning_trades:
            results.avg_win_pct = np.mean([t.pnl_pct for t in winning_trades])
            results.best_trade_pct = max([t.pnl_pct for t in winning_trades])

        if losing_trades:
            results.avg_loss_pct = np.mean([t.pnl_pct for t in losing_trades])
            results.worst_trade_pct = min([t.pnl_pct for t in losing_trades])

        # Profit factor
        total_wins = sum([t.pnl for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t.pnl for t in losing_trades])) if losing_trades else 0
        results.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Duration
        results.avg_trade_duration_minutes = np.mean([t.duration_minutes for t in self.completed_trades])

        # Long/Short breakdown
        long_trades = [t for t in self.completed_trades if t.side == 'long']
        short_trades = [t for t in self.completed_trades if t.side == 'short']

        results.long_trades = len(long_trades)
        results.short_trades = len(short_trades)

        if long_trades:
            long_wins = len([t for t in long_trades if t.pnl > 0])
            results.long_win_rate_pct = (long_wins / len(long_trades)) * 100

        if short_trades:
            short_wins = len([t for t in short_trades if t.pnl > 0])
            results.short_win_rate_pct = (short_wins / len(short_trades)) * 100

        # Sharpe ratio (simplified - using trade returns)
        if len(self.completed_trades) > 1:
            trade_returns = [t.pnl_pct / 100 for t in self.completed_trades]
            results.sharpe_ratio = (np.mean(trade_returns) / np.std(trade_returns)) * np.sqrt(252) if np.std(trade_returns) > 0 else 0

        # Max drawdown
        equity_values = [self.initial_capital] + [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_dd = 0

        for equity in equity_values:
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            if dd > max_dd:
                max_dd = dd

        results.max_drawdown_pct = max_dd

        return results

    def _display_results(self, results: BacktestResults):
        """Display backtest results"""

        logger.info("\n" + "=" * 80)
        logger.info("📊 BACKTEST RESULTS")
        logger.info("=" * 80)

        logger.info(f"\n💰 Capital & Returns:")
        logger.info(f"   Initial Capital:    ${results.initial_capital:,.2f}")
        logger.info(f"   Final Capital:      ${results.final_capital:,.2f}")
        logger.info(f"   Total P&L:          ${results.total_pnl:+,.2f}")
        logger.info(f"   Total Return:       {results.total_return_pct:+.2f}%")

        logger.info(f"\n📈 Trade Statistics:")
        logger.info(f"   Total Trades:       {results.total_trades}")
        logger.info(f"   Winning Trades:     {results.winning_trades} ({results.win_rate_pct:.1f}%)")
        logger.info(f"   Losing Trades:      {results.losing_trades}")
        logger.info(f"   Long Trades:        {results.long_trades} (Win Rate: {results.long_win_rate_pct:.1f}%)")
        logger.info(f"   Short Trades:       {results.short_trades} (Win Rate: {results.short_win_rate_pct:.1f}%)")

        logger.info(f"\n💵 P&L Analysis:")
        logger.info(f"   Average Win:        {results.avg_win_pct:+.2f}%")
        logger.info(f"   Average Loss:       {results.avg_loss_pct:+.2f}%")
        logger.info(f"   Best Trade:         {results.best_trade_pct:+.2f}%")
        logger.info(f"   Worst Trade:        {results.worst_trade_pct:+.2f}%")
        logger.info(f"   Profit Factor:      {results.profit_factor:.2f}")

        logger.info(f"\n⚠️  Risk Metrics:")
        logger.info(f"   Sharpe Ratio:       {results.sharpe_ratio:.2f}")
        logger.info(f"   Max Drawdown:       {results.max_drawdown_pct:.2f}%")

        logger.info(f"\n⏱️  Trade Duration:")
        logger.info(f"   Avg Duration:       {results.avg_trade_duration_minutes:.1f} minutes")

        logger.info("\n" + "=" * 80)

        # Sample trades
        if results.trades:
            logger.info("\n📋 Sample Trades (First 5):")
            for i, trade in enumerate(results.trades[:5], 1):
                logger.info(f"   {i}. {trade.side.upper()} {trade.symbol} @ ${trade.entry_price:.2f} → ${trade.exit_price:.2f} "
                           f"P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2f}%) - {trade.exit_reason}")

    async def _cleanup(self):
        """Cleanup components"""
        logger.info("\n🧹 Cleaning up components...")

        if self.data_manager:
            await self.data_manager.stop()
        if self.regime_engine:
            await self.regime_engine.stop()
        if self.pipeline:
            await self.pipeline.stop()

        logger.info("✅ Cleanup complete")


async def main():
    """Run backtest"""

    backtest = MomentumBacktest(
        initial_capital=100000.0,
        commission_per_trade=1.0
    )

    # Run backtest for November 2024
    results = await backtest.run_backtest(
        symbol='TSLA',
        start_date='2024-11-01',
        end_date='2024-11-30'
    )

    return results


if __name__ == "__main__":
    # Run backtest
    results = asyncio.run(main())

