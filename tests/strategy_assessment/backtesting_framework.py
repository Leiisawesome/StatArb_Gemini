#!/usr/bin/env python3
"""
Professional Backtesting Framework for Strategy Assessment
==========================================================

Institutional-grade backtesting infrastructure for comprehensive strategy validation.
Supports regime-based analysis, walk-forward testing, and Monte Carlo simulation.

Key Features:
- Standardized performance metrics calculation
- Regime-aware backtesting
- Transaction cost modeling
- Slippage simulation
- Position sizing and risk management
- Comprehensive reporting

Author: StatArb_Gemini Strategy Optimization
Version: 1.0.0 (Phase 1 Implementation)
Date: October 2025
"""

import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
from pathlib import Path
import json

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classifications"""
    BULL = "bull_market"
    BEAR = "bear_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    SIDEWAYS = "sideways"
    TRENDING = "trending"
    UNKNOWN = "unknown"


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    
    # Time period
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    
    # Initial capital
    initial_capital: float = 100000.0
    
    # Transaction costs
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005   # 0.05% slippage
    
    # Position sizing
    max_position_pct: float = 0.10  # 10% max per position
    max_leverage: float = 2.0       # 2x max leverage
    
    # Risk management
    enable_risk_management: bool = True
    max_daily_loss: float = 0.02    # 2% max daily loss
    max_drawdown_stop: float = 0.20  # 20% max drawdown stop
    
    # Data configuration
    data_interval: str = "1min"
    rebalance_frequency: str = "daily"  # "intraday", "daily", "weekly"
    
    # Regime analysis
    enable_regime_analysis: bool = True
    regime_lookback_period: int = 252  # 1 year
    
    # Reporting
    save_trades: bool = True
    save_daily_stats: bool = True
    generate_plots: bool = True


@dataclass
class Trade:
    """Individual trade record"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str  # "BUY" or "SELL"
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    total_cost: float = 0.0
    holding_period: int = 0  # in bars
    strategy_id: str = ""
    signal_confidence: float = 0.0
    regime: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        import pandas as pd
        
        # Handle mixed timestamp types
        entry_time_str = None
        if self.entry_time:
            if isinstance(self.entry_time, (int, float)):
                entry_time_str = pd.to_datetime(self.entry_time, unit='s').isoformat()
            else:
                entry_time_str = self.entry_time.isoformat()
        
        exit_time_str = None
        if self.exit_time:
            if isinstance(self.exit_time, (int, float)):
                exit_time_str = pd.to_datetime(self.exit_time, unit='s').isoformat()
            else:
                exit_time_str = self.exit_time.isoformat()
        
        return {
            'entry_time': entry_time_str,
            'exit_time': exit_time_str,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'commission': self.commission,
            'slippage': self.slippage,
            'total_cost': self.total_cost,
            'holding_period': self.holding_period,
            'strategy_id': self.strategy_id,
            'signal_confidence': self.signal_confidence,
            'regime': self.regime
        }


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    
    # Basic metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Drawdown metrics
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    current_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    
    # Return metrics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Trading metrics
    avg_holding_period: float = 0.0
    turnover: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_cost: float = 0.0
    
    # Regime-specific metrics
    bull_market_return: float = 0.0
    bear_market_return: float = 0.0
    high_vol_return: float = 0.0
    sideways_return: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ProfessionalBacktester:
    """
    Professional Backtesting Framework
    
    Institutional-grade backtesting with comprehensive performance analysis,
    regime awareness, and transaction cost modeling.
    """
    
    def __init__(self, config: BacktestConfig):
        """Initialize backtester"""
        self.config = config
        
        # State tracking
        self.current_capital = config.initial_capital
        self.initial_capital = config.initial_capital
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Trade] = []
        self.equity_curve: List[float] = [config.initial_capital]
        self.daily_returns: List[float] = []
        self.timestamps: List[datetime] = []
        
        # Performance tracking
        self.peak_equity = config.initial_capital
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.drawdown_start: Optional[datetime] = None
        self.max_drawdown_duration = 0
        
        # Regime tracking
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []
        
        # Daily statistics
        self.daily_stats: List[Dict[str, Any]] = []
        
        logger.info(f"🔧 Professional Backtester initialized")
        logger.info(f"   Initial Capital: ${config.initial_capital:,.2f}")
        logger.info(f"   Period: {config.start_date} to {config.end_date}")
        logger.info(f"   Commission: {config.commission_rate*100:.3f}%")
        logger.info(f"   Slippage: {config.slippage_rate*100:.3f}%")
    
    def execute_trade(self, signal: Dict[str, Any], current_price: float, 
                     timestamp: datetime) -> Optional[Trade]:
        """
        Execute a trading signal
        
        Args:
            signal: Trading signal dictionary with symbol, side, quantity, confidence
            current_price: Current market price
            timestamp: Current timestamp
            
        Returns:
            Trade object if executed, None otherwise
        """
        symbol = signal.get('symbol')
        side = signal.get('side', 'BUY').upper()
        quantity = signal.get('quantity', 0)
        confidence = signal.get('confidence', 0.5)
        strategy_id = signal.get('strategy_id', 'unknown')
        
        # Validate trade
        if quantity <= 0:
            logger.warning(f"Invalid quantity: {quantity}")
            return None
        
        # Calculate costs
        commission = current_price * quantity * self.config.commission_rate
        slippage = current_price * quantity * self.config.slippage_rate
        total_cost = commission + slippage
        
        # Adjust price for slippage
        execution_price = current_price * (1 + self.config.slippage_rate) if side == 'BUY' else current_price * (1 - self.config.slippage_rate)
        
        # Check if we have enough capital
        required_capital = execution_price * quantity + total_cost
        if side == 'BUY' and required_capital > self.current_capital:
            logger.warning(f"Insufficient capital: need ${required_capital:.2f}, have ${self.current_capital:.2f}")
            # Adjust quantity to affordable amount
            affordable_quantity = (self.current_capital - total_cost) / execution_price
            if affordable_quantity < quantity * 0.5:  # If less than 50% of desired, skip
                return None
            quantity = affordable_quantity
            required_capital = execution_price * quantity + total_cost
        
        # Execute trade
        if side == 'BUY':
            # Check if closing a short position
            if symbol in self.positions and self.positions[symbol]['side'] == 'SHORT':
                position = self.positions[symbol]
                close_quantity = min(quantity, position['quantity'])
                
                # Calculate P&L for short (profit when price goes down)
                entry_price = position['entry_price']
                pnl = (entry_price - execution_price) * close_quantity - commission - slippage
                pnl_pct = (entry_price - execution_price) / entry_price
                
                # Create trade record
                # Handle mixed timestamp types
                import pandas as pd
                exit_ts = timestamp if isinstance(timestamp, pd.Timestamp) else pd.to_datetime(timestamp, unit='s' if isinstance(timestamp, (int, float)) else None)
                entry_ts = position['entry_time'] if isinstance(position['entry_time'], pd.Timestamp) else pd.to_datetime(position['entry_time'], unit='s' if isinstance(position['entry_time'], (int, float)) else None)
                holding_period_minutes = int((exit_ts - entry_ts).total_seconds() / 60)
                
                trade = Trade(
                    entry_time=position['entry_time'],
                    exit_time=timestamp,
                    symbol=symbol,
                    side='SHORT',
                    entry_price=entry_price,
                    exit_price=execution_price,
                    quantity=close_quantity,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    commission=position['commission'] + commission,
                    slippage=position['slippage'] + slippage,
                    total_cost=position['commission'] + position['slippage'] + commission + slippage,
                    holding_period=holding_period_minutes,
                    strategy_id=position['strategy_id'],
                    signal_confidence=position['confidence'],
                    regime=position['regime']
                )
                
                self.closed_positions.append(trade)
                # For shorts: we get back the initial short proceeds plus/minus P&L
                self.current_capital += execution_price * close_quantity + pnl - total_cost
                
                # Remove or reduce position
                if close_quantity >= position['quantity']:
                    del self.positions[symbol]
                    logger.info(f"📉 CLOSE SHORT {symbol}: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%) | Capital: ${self.current_capital:.2f}")
                else:
                    position['quantity'] -= close_quantity
                    logger.info(f"📉 PARTIAL CLOSE SHORT {symbol}: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%)")
                
                return trade
            
            # Open or add to LONG position
            elif symbol not in self.positions:
                self.positions[symbol] = {
                    'entry_time': timestamp,
                    'entry_price': execution_price,
                    'quantity': quantity,
                    'side': 'LONG',
                    'strategy_id': strategy_id,
                    'confidence': confidence,
                    'regime': self.current_regime.value,
                    'commission': commission,
                    'slippage': slippage
                }
                self.current_capital -= required_capital
                
                logger.info(f"📈 LONG {symbol}: {quantity:.2f} @ ${execution_price:.2f} (Capital: ${self.current_capital:.2f})")
            else:
                # Add to existing LONG position (average in)
                existing = self.positions[symbol]
                if existing['side'] == 'LONG':
                    total_quantity = existing['quantity'] + quantity
                    avg_price = (existing['entry_price'] * existing['quantity'] + execution_price * quantity) / total_quantity
                    existing['quantity'] = total_quantity
                    existing['entry_price'] = avg_price
                    existing['commission'] += commission
                    existing['slippage'] += slippage
                    self.current_capital -= required_capital
                
        elif side == 'SELL':
            # Check if closing a LONG position or opening a SHORT
            if symbol in self.positions and self.positions[symbol]['side'] == 'LONG':
                try:
                    position = self.positions[symbol]
                    close_quantity = min(quantity, position['quantity'])
                    
                    # Calculate P&L for long (profit when price goes up)
                    entry_price = position['entry_price']
                    pnl = (execution_price - entry_price) * close_quantity - commission - slippage
                    pnl_pct = (execution_price - entry_price) / entry_price
                    
                    # Create trade record
                    # Handle mixed timestamp types
                    import pandas as pd
                    exit_ts = timestamp if isinstance(timestamp, pd.Timestamp) else pd.to_datetime(timestamp, unit='s' if isinstance(timestamp, (int, float)) else None)
                    entry_ts = position['entry_time'] if isinstance(position['entry_time'], pd.Timestamp) else pd.to_datetime(position['entry_time'], unit='s' if isinstance(position['entry_time'], (int, float)) else None)
                    holding_period_minutes = int((exit_ts - entry_ts).total_seconds() / 60)
                    
                    trade = Trade(
                        entry_time=position['entry_time'],
                        exit_time=timestamp,
                        symbol=symbol,
                        side='LONG',
                        entry_price=entry_price,
                        exit_price=execution_price,
                        quantity=close_quantity,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        commission=position['commission'] + commission,
                        slippage=position['slippage'] + slippage,
                        total_cost=position['commission'] + position['slippage'] + commission + slippage,
                        holding_period=holding_period_minutes,
                        strategy_id=position['strategy_id'],
                        signal_confidence=position['confidence'],
                        regime=position['regime']
                    )
                    
                    self.closed_positions.append(trade)
                    self.current_capital += execution_price * close_quantity - total_cost
                    
                    # Remove or reduce position
                    if close_quantity >= position['quantity']:
                        del self.positions[symbol]
                        logger.info(f"📉 CLOSE LONG {symbol}: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%) | Capital: ${self.current_capital:.2f}")
                    else:
                        position['quantity'] -= close_quantity
                        logger.info(f"📉 PARTIAL CLOSE LONG {symbol}: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%)")
                    
                    return trade
                except Exception as e:
                    logger.error(f"Exception closing LONG {symbol}: {e}")
                    return None
            
            # Open SHORT position (sell without owning)
            elif symbol not in self.positions:
                # For short selling, we receive the proceeds and open a short position
                self.positions[symbol] = {
                    'entry_time': timestamp,
                    'entry_price': execution_price,
                    'quantity': quantity,
                    'side': 'SHORT',
                    'strategy_id': strategy_id,
                    'confidence': confidence,
                    'regime': self.current_regime.value,
                    'commission': commission,
                    'slippage': slippage
                }
                # For shorts: we receive the short proceeds minus costs
                self.current_capital += execution_price * quantity - total_cost
                
                logger.info(f"📉 SHORT {symbol}: {quantity:.2f} @ ${execution_price:.2f} (Capital: ${self.current_capital:.2f})")
            
            else:
                # Trying to short more when already short (add to short position)
                existing = self.positions[symbol]
                if existing['side'] == 'SHORT':
                    total_quantity = existing['quantity'] + quantity
                    avg_price = (existing['entry_price'] * existing['quantity'] + execution_price * quantity) / total_quantity
                    existing['quantity'] = total_quantity
                    existing['entry_price'] = avg_price
                    existing['commission'] += commission
                    existing['slippage'] += slippage
                    self.current_capital += execution_price * quantity - total_cost
                    logger.info(f"📉 ADD TO SHORT {symbol}: {quantity:.2f} @ ${execution_price:.2f}")
                else:
                    logger.warning(f"Unexpected position state for {symbol}")
        
        return None
    
    def update_equity(self, timestamp: datetime, market_prices: Dict[str, float]) -> None:
        """Update equity curve with mark-to-market"""
        
        # Calculate mark-to-market value of open positions
        mtm_value = 0.0
        for symbol, position in self.positions.items():
            if symbol in market_prices:
                current_price = market_prices[symbol]
                
                if position['side'] == 'LONG':
                    # Long positions: value increases when price goes up
                    position_value = current_price * position['quantity']
                    (current_price - position['entry_price']) * position['quantity']
                    mtm_value += position_value
                elif position['side'] == 'SHORT':
                    # Short positions: we owe the current value, gain when price goes down
                    # The liability is the current market value we'd need to buy back
                    position_liability = current_price * position['quantity']
                    (position['entry_price'] - current_price) * position['quantity']
                    # For shorts: subtract the liability from capital (we owe this)
                    mtm_value -= position_liability
        
        # Total equity = cash + mark-to-market value (positive for longs, negative for shorts)
        total_equity = self.current_capital + mtm_value
        self.equity_curve.append(total_equity)
        self.timestamps.append(timestamp)
        
        # Calculate daily return
        if len(self.equity_curve) > 1:
            daily_return = (self.equity_curve[-1] - self.equity_curve[-2]) / self.equity_curve[-2]
            self.daily_returns.append(daily_return)
        
        # Update drawdown
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity
            self.drawdown_start = None
        
        self.current_drawdown = (self.peak_equity - total_equity) / self.peak_equity
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
            if self.drawdown_start is None:
                self.drawdown_start = timestamp
            
            if self.drawdown_start:
                # Handle different timestamp types
                import pandas as pd
                current_ts = timestamp if isinstance(timestamp, pd.Timestamp) else pd.to_datetime(timestamp, unit='s' if isinstance(timestamp, (int, float)) else None)
                start_ts = self.drawdown_start if isinstance(self.drawdown_start, pd.Timestamp) else pd.to_datetime(self.drawdown_start, unit='s' if isinstance(self.drawdown_start, (int, float)) else None)
                
                drawdown_duration = (current_ts - start_ts).days
                if drawdown_duration > self.max_drawdown_duration:
                    self.max_drawdown_duration = drawdown_duration
        
        # Emergency stop if max drawdown exceeded
        if self.config.enable_risk_management and self.current_drawdown > self.config.max_drawdown_stop:
            logger.critical(f"🚨 MAX DRAWDOWN EXCEEDED: {self.current_drawdown*100:.2f}% > {self.config.max_drawdown_stop*100:.2f}%")
            # Close all positions
            for symbol in list(self.positions.keys()):
                if symbol in market_prices:
                    close_signal = {
                        'symbol': symbol,
                        'side': 'SELL',
                        'quantity': self.positions[symbol]['quantity'],
                        'strategy_id': 'RISK_STOP'
                    }
                    self.execute_trade(close_signal, market_prices[symbol], timestamp)
    
    def update_regime(self, regime: MarketRegime, timestamp: datetime) -> None:
        """Update current market regime"""
        if regime != self.current_regime:
            self.current_regime = regime
            self.regime_history.append((timestamp, regime))
            logger.info(f"📊 Regime change: {regime.value}")
    
    def calculate_performance_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        metrics = PerformanceMetrics()
        
        if len(self.equity_curve) < 2:
            return metrics
        
        # Basic metrics
        metrics.total_return = (self.equity_curve[-1] - self.initial_capital) / self.initial_capital
        
        # Calculate annualized return
        if len(self.timestamps) >= 2:
            # Convert timestamps to datetime if needed
            import pandas as pd
            
            start_ts = self.timestamps[0]
            end_ts = self.timestamps[-1]
            
            # Handle different timestamp types
            if isinstance(start_ts, (int, float)):
                start_ts = pd.to_datetime(start_ts, unit='s')
                end_ts = pd.to_datetime(end_ts, unit='s')
            elif isinstance(start_ts, pd.Timestamp):
                pass  # Already pandas timestamp
            
            total_days = (end_ts - start_ts).days
            if total_days > 0:
                metrics.annualized_return = (1 + metrics.total_return) ** (365 / total_days) - 1
        
        # Trade statistics
        metrics.total_trades = len(self.closed_positions)
        metrics.winning_trades = len([t for t in self.closed_positions if t.pnl > 0])
        metrics.losing_trades = len([t for t in self.closed_positions if t.pnl <= 0])
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0
        
        # Win/Loss metrics
        winning_trades = [t.pnl for t in self.closed_positions if t.pnl > 0]
        losing_trades = [t.pnl for t in self.closed_positions if t.pnl <= 0]
        
        metrics.avg_win = np.mean(winning_trades) if winning_trades else 0
        metrics.avg_loss = np.mean(losing_trades) if losing_trades else 0
        metrics.profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else 0
        metrics.expectancy = (metrics.win_rate * metrics.avg_win + (1 - metrics.win_rate) * metrics.avg_loss)
        
        # Returns and volatility
        returns = np.array(self.daily_returns) if self.daily_returns else np.array([0])
        metrics.volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0
        
        # Downside deviation (for Sortino)
        downside_returns = returns[returns < 0] if len(returns) > 0 else np.array([0])
        metrics.downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0
        
        # Risk-adjusted metrics
        risk_free_rate = 0.02  # 2% annual
        returns - (risk_free_rate / 252)
        
        if metrics.volatility > 0:
            metrics.sharpe_ratio = (metrics.annualized_return - risk_free_rate) / metrics.volatility
        
        if metrics.downside_deviation > 0:
            metrics.sortino_ratio = (metrics.annualized_return - risk_free_rate) / metrics.downside_deviation
        
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
        
        # Drawdown metrics
        metrics.max_drawdown = self.max_drawdown
        metrics.max_drawdown_duration = self.max_drawdown_duration
        metrics.current_drawdown = self.current_drawdown
        
        # Calculate average drawdown
        equity_series = pd.Series(self.equity_curve)
        running_max = equity_series.expanding().max()
        drawdown_series = (equity_series - running_max) / running_max
        metrics.avg_drawdown = abs(drawdown_series.mean())
        
        # VaR and CVaR
        if len(returns) > 0:
            metrics.var_95 = np.percentile(returns, 5)
            tail_returns = returns[returns <= metrics.var_95]
            metrics.cvar_95 = np.mean(tail_returns) if len(tail_returns) > 0 else metrics.var_95
        
        # Trading metrics
        if metrics.total_trades > 0:
            metrics.avg_holding_period = np.mean([t.holding_period for t in self.closed_positions])
            metrics.total_commission = sum([t.commission for t in self.closed_positions])
            metrics.total_slippage = sum([t.slippage for t in self.closed_positions])
            metrics.total_cost = metrics.total_commission + metrics.total_slippage
        
        # Regime-specific returns
        regime_returns = {
            MarketRegime.BULL: [],
            MarketRegime.BEAR: [],
            MarketRegime.HIGH_VOLATILITY: [],
            MarketRegime.SIDEWAYS: []
        }
        
        for trade in self.closed_positions:
            regime = MarketRegime(trade.regime) if trade.regime != "unknown" else MarketRegime.UNKNOWN
            if regime in regime_returns:
                regime_returns[regime].append(trade.pnl_pct)
        
        metrics.bull_market_return = np.mean(regime_returns[MarketRegime.BULL]) if regime_returns[MarketRegime.BULL] else 0
        metrics.bear_market_return = np.mean(regime_returns[MarketRegime.BEAR]) if regime_returns[MarketRegime.BEAR] else 0
        metrics.high_vol_return = np.mean(regime_returns[MarketRegime.HIGH_VOLATILITY]) if regime_returns[MarketRegime.HIGH_VOLATILITY] else 0
        metrics.sideways_return = np.mean(regime_returns[MarketRegime.SIDEWAYS]) if regime_returns[MarketRegime.SIDEWAYS] else 0
        
        return metrics
    
    def generate_report(self, strategy_name: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive backtest report"""
        
        metrics = self.calculate_performance_metrics()
        
        report = {
            'strategy_name': strategy_name,
            'backtest_config': asdict(self.config),
            'performance_metrics': metrics.to_dict(),
            'summary_statistics': {
                'initial_capital': self.initial_capital,
                'final_equity': self.equity_curve[-1] if self.equity_curve else self.initial_capital,
                'total_return_pct': metrics.total_return * 100,
                'annualized_return_pct': metrics.annualized_return * 100,
                'max_drawdown_pct': metrics.max_drawdown * 100,
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'win_rate_pct': metrics.win_rate * 100,
                'profit_factor': metrics.profit_factor,
                'total_trades': metrics.total_trades
            },
            'regime_performance': {
                'bull_market': metrics.bull_market_return * 100,
                'bear_market': metrics.bear_market_return * 100,
                'high_volatility': metrics.high_vol_return * 100,
                'sideways': metrics.sideways_return * 100
            },
            'trades': [t.to_dict() for t in self.closed_positions] if self.config.save_trades else [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Save report
        if save_path:
            save_dir = Path(save_path)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = save_dir / f"{strategy_name}_backtest_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📄 Report saved: {report_file}")
        
        return report
    
    def print_summary(self, strategy_name: str) -> None:
        """Print backtest summary to console"""
        
        metrics = self.calculate_performance_metrics()
        
        print("\n" + "="*80)
        print(f"BACKTEST SUMMARY: {strategy_name}")
        print("="*80)
        print(f"\n📊 Performance Metrics:")
        print(f"   Total Return:        {metrics.total_return*100:>10.2f}%")
        print(f"   Annualized Return:   {metrics.annualized_return*100:>10.2f}%")
        print(f"   Sharpe Ratio:        {metrics.sharpe_ratio:>10.2f}")
        print(f"   Sortino Ratio:       {metrics.sortino_ratio:>10.2f}")
        print(f"   Calmar Ratio:        {metrics.calmar_ratio:>10.2f}")
        print(f"\n📉 Risk Metrics:")
        print(f"   Maximum Drawdown:    {metrics.max_drawdown*100:>10.2f}%")
        print(f"   Volatility:          {metrics.volatility*100:>10.2f}%")
        print(f"   VaR (95%):           {metrics.var_95*100:>10.2f}%")
        print(f"   CVaR (95%):          {metrics.cvar_95*100:>10.2f}%")
        print(f"\n📈 Trading Statistics:")
        print(f"   Total Trades:        {metrics.total_trades:>10,}")
        print(f"   Win Rate:            {metrics.win_rate*100:>10.2f}%")
        print(f"   Profit Factor:       {metrics.profit_factor:>10.2f}")
        print(f"   Expectancy:          ${metrics.expectancy:>10.2f}")
        print(f"   Avg Win:             ${metrics.avg_win:>10.2f}")
        print(f"   Avg Loss:            ${metrics.avg_loss:>10.2f}")
        print(f"\n💰 Cost Analysis:")
        print(f"   Total Commission:    ${metrics.total_commission:>10.2f}")
        print(f"   Total Slippage:      ${metrics.total_slippage:>10.2f}")
        print(f"   Total Cost:          ${metrics.total_cost:>10.2f}")
        print(f"\n🌍 Regime Performance:")
        print(f"   Bull Market:         {metrics.bull_market_return*100:>10.2f}%")
        print(f"   Bear Market:         {metrics.bear_market_return*100:>10.2f}%")
        print(f"   High Volatility:     {metrics.high_vol_return*100:>10.2f}%")
        print(f"   Sideways:            {metrics.sideways_return*100:>10.2f}%")
        print("\n" + "="*80 + "\n")


# Export key classes
__all__ = [
    'ProfessionalBacktester',
    'BacktestConfig',
    'PerformanceMetrics',
    'Trade',
    'MarketRegime'
]
