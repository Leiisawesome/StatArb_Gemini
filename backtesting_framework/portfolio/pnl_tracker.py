#!/usr/bin/env python3
"""
P&L Tracking System
Phase 2: Core System Integration - Batch 3
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class PnLTracker:
    """Profit and Loss tracking system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.pnl_history = []
        self.daily_pnl = {}
        self.position_pnl = {}
        
        # P&L metrics
        self.total_realized_pnl = 0.0
        self.total_unrealized_pnl = 0.0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        logger.info(f"Initialized PnLTracker with ${initial_capital:,.2f} initial capital")
    
    def update_pnl(self, realized_pnl: float = 0.0, unrealized_pnl: float = 0.0,
                  symbol: str = None, position_pnl: float = 0.0):
        """Update P&L with new values"""
        
        # Update totals
        self.total_realized_pnl += realized_pnl
        self.total_unrealized_pnl = unrealized_pnl
        self.total_pnl = self.total_realized_pnl + self.total_unrealized_pnl
        
        # Update current capital
        self.current_capital = self.initial_capital + self.total_pnl
        
        # Update peak capital and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Record P&L entry
        pnl_entry = {
            'timestamp': datetime.now(),
            'realized_pnl': self.total_realized_pnl,
            'unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'current_capital': self.current_capital,
            'drawdown': current_drawdown,
            'symbol': symbol,
            'position_pnl': position_pnl
        }
        self.pnl_history.append(pnl_entry)
        
        # Update daily P&L
        today = datetime.now().date()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = {
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'total_pnl': 0.0,
                'trades_count': 0
            }
        
        self.daily_pnl[today]['realized_pnl'] += realized_pnl
        self.daily_pnl[today]['unrealized_pnl'] = unrealized_pnl
        self.daily_pnl[today]['total_pnl'] = self.daily_pnl[today]['realized_pnl'] + self.daily_pnl[today]['unrealized_pnl']
        if realized_pnl != 0:
            self.daily_pnl[today]['trades_count'] += 1
        
        # Update position P&L
        if symbol:
            if symbol not in self.position_pnl:
                self.position_pnl[symbol] = {
                    'total_pnl': 0.0,
                    'trades_count': 0,
                    'last_update': datetime.now()
                }
            self.position_pnl[symbol]['total_pnl'] += position_pnl
            self.position_pnl[symbol]['trades_count'] += 1
            self.position_pnl[symbol]['last_update'] = datetime.now()
        
        # Keep only last 1000 records
        if len(self.pnl_history) > 1000:
            self.pnl_history = self.pnl_history[-1000:]
        
        logger.debug(f"Updated P&L: Realized=${self.total_realized_pnl:.2f}, "
                    f"Unrealized=${self.total_unrealized_pnl:.2f}, "
                    f"Total=${self.total_pnl:.2f}")
    
    def get_pnl_summary(self) -> Dict:
        """Get P&L summary"""
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_realized_pnl': self.total_realized_pnl,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_pnl': self.total_pnl,
            'total_return': total_return,
            'max_drawdown': self.max_drawdown,
            'peak_capital': self.peak_capital,
            'pnl_history_count': len(self.pnl_history),
            'daily_pnl_count': len(self.daily_pnl),
            'position_pnl_count': len(self.position_pnl)
        }
    
    def get_daily_pnl(self, days: int = 30) -> pd.DataFrame:
        """Get daily P&L for specified number of days"""
        if not self.daily_pnl:
            return pd.DataFrame()
        
        # Get last N days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_data = []
        for date, data in self.daily_pnl.items():
            if start_date <= date <= end_date:
                daily_data.append({
                    'date': date,
                    **data
                })
        
        if not daily_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(daily_data)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def get_position_pnl(self) -> Dict:
        """Get P&L by position"""
        return self.position_pnl.copy()
    
    def get_pnl_history(self, lookback_periods: int = 100) -> pd.DataFrame:
        """Get P&L history as DataFrame"""
        if not self.pnl_history:
            return pd.DataFrame()
        
        history = self.pnl_history[-lookback_periods:]
        df = pd.DataFrame(history)
        df.set_index('timestamp', inplace=True)
        return df
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(self.pnl_history) < 2:
            return 0.0
        
        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(self.pnl_history)):
            daily_return = (self.pnl_history[i]['total_pnl'] - self.pnl_history[i-1]['total_pnl']) / self.initial_capital
            daily_returns.append(daily_return)
        
        if not daily_returns:
            return 0.0
        
        # Calculate Sharpe ratio
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe_ratio = (avg_return - risk_free_rate/252) / std_return * np.sqrt(252)
        
        return sharpe_ratio
    
    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        if len(self.pnl_history) < 2:
            return 0.0
        
        # Calculate daily returns
        daily_returns = []
        for i in range(1, len(self.pnl_history)):
            daily_return = (self.pnl_history[i]['total_pnl'] - self.pnl_history[i-1]['total_pnl']) / self.initial_capital
            daily_returns.append(daily_return)
        
        if not daily_returns:
            return 0.0
        
        # Calculate downside deviation
        negative_returns = [r for r in daily_returns if r < 0]
        if not negative_returns:
            return float('inf')
        
        avg_return = np.mean(daily_returns)
        downside_deviation = np.std(negative_returns)
        
        if downside_deviation == 0:
            return 0.0
        
        sortino_ratio = (avg_return - risk_free_rate/252) / downside_deviation * np.sqrt(252)
        
        return sortino_ratio 