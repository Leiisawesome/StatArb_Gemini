#!/usr/bin/env python3
"""
Risk Management System
Phase 2: Core System Integration - Batch 4
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class RiskLimits:
    """Risk limits configuration"""
    
    def __init__(self):
        # Position limits
        self.max_position_size = 0.1  # 10% max position size
        self.max_sector_exposure = 0.3  # 30% max sector exposure
        self.max_portfolio_risk = 0.02  # 2% max portfolio risk
        
        # Stop-loss limits
        self.stop_loss_pct = 0.05  # 5% stop-loss
        self.take_profit_pct = 0.10  # 10% take-profit
        self.trailing_stop_pct = 0.03  # 3% trailing stop
        
        # Drawdown limits
        self.max_drawdown = 0.15  # 15% max drawdown
        self.daily_loss_limit = 0.05  # 5% daily loss limit
        
        # Volatility limits
        self.max_volatility = 0.25  # 25% max volatility
        self.var_confidence = 0.95  # 95% VaR confidence level

class RiskManager:
    """Risk management system"""
    
    def __init__(self, risk_limits: RiskLimits = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.risk_callbacks = []
        self.risk_alerts = []
        self.position_risks = {}
        self.portfolio_risk = {}
        
        # Risk tracking
        self.current_drawdown = 0.0
        self.daily_pnl = 0.0
        self.portfolio_var = 0.0
        self.portfolio_cvar = 0.0
        
        logger.info("Initialized RiskManager with risk limits")
    
    def add_risk_callback(self, callback: Callable):
        """Add callback for risk events"""
        self.risk_callbacks.append(callback)
        logger.info(f"Added risk callback: {callback.__name__}")
    
    def check_position_risk(self, symbol: str, position_size: float, 
                          current_price: float, avg_price: float) -> Dict:
        """Check risk for individual position"""
        
        risk_metrics = {
            'symbol': symbol,
            'position_size': position_size,
            'current_price': current_price,
            'avg_price': avg_price,
            'unrealized_pnl': (current_price - avg_price) * position_size,
            'unrealized_pnl_pct': (current_price - avg_price) / avg_price,
            'risk_level': 'LOW',
            'alerts': []
        }
        
        # Check stop-loss
        if risk_metrics['unrealized_pnl_pct'] <= -self.risk_limits.stop_loss_pct:
            risk_metrics['alerts'].append(f"Stop-loss triggered: {risk_metrics['unrealized_pnl_pct']:.2%}")
            risk_metrics['risk_level'] = 'HIGH'
        
        # Check take-profit
        if risk_metrics['unrealized_pnl_pct'] >= self.risk_limits.take_profit_pct:
            risk_metrics['alerts'].append(f"Take-profit triggered: {risk_metrics['unrealized_pnl_pct']:.2%}")
            risk_metrics['risk_level'] = 'MEDIUM'
        
        # Check position size
        if position_size > self.risk_limits.max_position_size:
            risk_metrics['alerts'].append(f"Position size exceeds limit: {position_size:.2%}")
            risk_metrics['risk_level'] = 'HIGH'
        
        # Store position risk
        self.position_risks[symbol] = risk_metrics
        
        # Notify callbacks if alerts
        if risk_metrics['alerts']:
            for callback in self.risk_callbacks:
                try:
                    callback(symbol, risk_metrics)
                except Exception as e:
                    logger.error(f"Risk callback error: {e}")
        
        return risk_metrics
    
    def check_portfolio_risk(self, portfolio_value: float, positions: Dict,
                           market_data: Dict = None) -> Dict:
        """Check overall portfolio risk"""
        
        portfolio_risk = {
            'portfolio_value': portfolio_value,
            'positions_count': len(positions),
            'total_exposure': 0.0,
            'sector_exposure': {},
            'risk_level': 'LOW',
            'alerts': [],
            'var_95': 0.0,
            'cvar_95': 0.0
        }
        
        # Calculate total exposure
        for symbol, position in positions.items():
            if hasattr(position, 'market_value'):
                portfolio_risk['total_exposure'] += position.market_value
        
        # Check sector exposure (simplified)
        if market_data:
            for symbol, position in positions.items():
                sector = market_data.get(symbol, {}).get('sector', 'UNKNOWN')
                if sector not in portfolio_risk['sector_exposure']:
                    portfolio_risk['sector_exposure'][sector] = 0.0
                
                if hasattr(position, 'market_value'):
                    portfolio_risk['sector_exposure'][sector] += position.market_value
                
                # Check sector limits
                sector_exposure_pct = portfolio_risk['sector_exposure'][sector] / portfolio_value
                if sector_exposure_pct > self.risk_limits.max_sector_exposure:
                    portfolio_risk['alerts'].append(f"Sector {sector} exposure exceeds limit: {sector_exposure_pct:.2%}")
                    portfolio_risk['risk_level'] = 'HIGH'
        
        # Calculate VaR and CVaR (simplified)
        if market_data and len(positions) > 0:
            returns = []
            for symbol in positions.keys():
                if symbol in market_data and 'returns' in market_data[symbol]:
                    returns.extend(market_data[symbol]['returns'])
            
            if returns:
                returns = np.array(returns)
                portfolio_risk['var_95'] = np.percentile(returns, (1 - self.risk_limits.var_confidence) * 100)
                portfolio_risk['cvar_95'] = returns[returns <= portfolio_risk['var_95']].mean()
        
        # Check drawdown
        if self.current_drawdown > self.risk_limits.max_drawdown:
            portfolio_risk['alerts'].append(f"Drawdown exceeds limit: {self.current_drawdown:.2%}")
            portfolio_risk['risk_level'] = 'HIGH'
        
        # Check daily loss limit
        if self.daily_pnl < -portfolio_value * self.risk_limits.daily_loss_limit:
            portfolio_risk['alerts'].append(f"Daily loss limit exceeded: {self.daily_pnl:.2f}")
            portfolio_risk['risk_level'] = 'HIGH'
        
        # Store portfolio risk
        self.portfolio_risk = portfolio_risk
        
        # Notify callbacks if alerts
        if portfolio_risk['alerts']:
            for callback in self.risk_callbacks:
                try:
                    callback('PORTFOLIO', portfolio_risk)
                except Exception as e:
                    logger.error(f"Risk callback error: {e}")
        
        return portfolio_risk
    
    def update_drawdown(self, current_value: float, peak_value: float):
        """Update current drawdown"""
        if peak_value > 0:
            self.current_drawdown = (peak_value - current_value) / peak_value
        else:
            self.current_drawdown = 0.0
    
    def update_daily_pnl(self, daily_pnl: float):
        """Update daily P&L"""
        self.daily_pnl = daily_pnl
    
    def should_stop_trading(self) -> bool:
        """Check if trading should be stopped due to risk limits"""
        return (self.current_drawdown > self.risk_limits.max_drawdown or
                self.daily_pnl < -100000 * self.risk_limits.daily_loss_limit)
    
    def get_risk_summary(self) -> Dict:
        """Get risk management summary"""
        return {
            'current_drawdown': self.current_drawdown,
            'daily_pnl': self.daily_pnl,
            'position_risks_count': len(self.position_risks),
            'portfolio_risk_level': self.portfolio_risk.get('risk_level', 'LOW'),
            'risk_alerts_count': len(self.risk_alerts),
            'risk_callbacks_count': len(self.risk_callbacks),
            'should_stop_trading': self.should_stop_trading()
        } 