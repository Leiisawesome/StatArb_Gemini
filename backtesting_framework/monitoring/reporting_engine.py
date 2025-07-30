#!/usr/bin/env python3
"""
Reporting Engine
Phase 2: Core System Integration - Batch 5
"""

import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Report generation system"""
    
    def __init__(self):
        self.report_templates = {}
        self.report_history = []
        
        logger.info("Initialized ReportGenerator")
    
    def generate_performance_report(self, performance_data: Dict, 
                                  portfolio_data: Dict = None,
                                  risk_data: Dict = None) -> Dict:
        """Generate comprehensive performance report"""
        
        report = {
            'report_id': f"PERF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'report_type': 'PERFORMANCE',
            'summary': {
                'total_return': performance_data.get('total_return', 0.0),
                'sharpe_ratio': performance_data.get('sharpe_ratio', 0.0),
                'sortino_ratio': performance_data.get('sortino_ratio', 0.0),
                'max_drawdown': performance_data.get('max_drawdown', 0.0),
                'win_rate': performance_data.get('win_rate', 0.0),
                'profit_factor': performance_data.get('profit_factor', 0.0),
                'total_trades': performance_data.get('total_trades', 0)
            },
            'performance_metrics': performance_data,
            'portfolio_summary': portfolio_data or {},
            'risk_metrics': risk_data or {},
            'recommendations': self._generate_recommendations(performance_data)
        }
        
        # Store report
        self.report_history.append(report)
        
        logger.info(f"Generated performance report: {report['report_id']}")
        return report
    
    def generate_risk_report(self, risk_data: Dict, 
                           portfolio_data: Dict = None) -> Dict:
        """Generate comprehensive risk report"""
        
        report = {
            'report_id': f"RISK_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'report_type': 'RISK',
            'summary': {
                'current_drawdown': risk_data.get('current_drawdown', 0.0),
                'portfolio_risk_level': risk_data.get('portfolio_risk_level', 'LOW'),
                'position_risks_count': risk_data.get('position_risks_count', 0),
                'should_stop_trading': risk_data.get('should_stop_trading', False)
            },
            'risk_metrics': risk_data,
            'portfolio_summary': portfolio_data or {},
            'risk_alerts': risk_data.get('alerts', []),
            'recommendations': self._generate_risk_recommendations(risk_data)
        }
        
        # Store report
        self.report_history.append(report)
        
        logger.info(f"Generated risk report: {report['report_id']}")
        return report
    
    def generate_trading_report(self, trading_data: Dict,
                              performance_data: Dict = None) -> Dict:
        """Generate trading activity report"""
        
        report = {
            'report_id': f"TRADE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'timestamp': datetime.now().isoformat(),
            'report_type': 'TRADING',
            'summary': {
                'total_orders': trading_data.get('total_orders', 0),
                'filled_orders': trading_data.get('filled_orders', 0),
                'cancelled_orders': trading_data.get('cancelled_orders', 0),
                'total_fill_value': trading_data.get('total_fill_value', 0.0),
                'available_capital': trading_data.get('available_capital', 0.0)
            },
            'trading_metrics': trading_data,
            'performance_summary': performance_data or {},
            'order_breakdown': trading_data.get('order_breakdown', {}),
            'recommendations': self._generate_trading_recommendations(trading_data)
        }
        
        # Store report
        self.report_history.append(report)
        
        logger.info(f"Generated trading report: {report['report_id']}")
        return report
    
    def _generate_recommendations(self, performance_data: Dict) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Sharpe ratio recommendations
        sharpe_ratio = performance_data.get('sharpe_ratio', 0.0)
        if sharpe_ratio < 0.5:
            recommendations.append("Sharpe ratio below 0.5 - consider reducing risk or improving strategy")
        elif sharpe_ratio > 1.5:
            recommendations.append("Excellent Sharpe ratio - strategy performing well")
        
        # Drawdown recommendations
        max_drawdown = performance_data.get('max_drawdown', 0.0)
        if max_drawdown < -0.15:
            recommendations.append("Maximum drawdown exceeded 15% - review risk management")
        elif max_drawdown > -0.05:
            recommendations.append("Low drawdown - good risk management")
        
        # Win rate recommendations
        win_rate = performance_data.get('win_rate', 0.0)
        if win_rate < 0.4:
            recommendations.append("Win rate below 40% - review entry/exit criteria")
        elif win_rate > 0.6:
            recommendations.append("High win rate - strategy working well")
        
        # Profit factor recommendations
        profit_factor = performance_data.get('profit_factor', 0.0)
        if profit_factor < 1.2:
            recommendations.append("Profit factor below 1.2 - review risk-reward ratio")
        elif profit_factor > 2.0:
            recommendations.append("Excellent profit factor - strong strategy")
        
        return recommendations
    
    def _generate_risk_recommendations(self, risk_data: Dict) -> List[str]:
        """Generate risk recommendations"""
        recommendations = []
        
        # Drawdown recommendations
        current_drawdown = risk_data.get('current_drawdown', 0.0)
        if current_drawdown < -0.10:
            recommendations.append("Current drawdown exceeds 10% - consider reducing position sizes")
        
        # Risk level recommendations
        risk_level = risk_data.get('portfolio_risk_level', 'LOW')
        if risk_level == 'HIGH':
            recommendations.append("Portfolio risk level HIGH - review position concentrations")
        elif risk_level == 'MEDIUM':
            recommendations.append("Portfolio risk level MEDIUM - monitor closely")
        
        # Trading stop recommendations
        should_stop = risk_data.get('should_stop_trading', False)
        if should_stop:
            recommendations.append("Trading should be stopped - risk limits exceeded")
        
        return recommendations
    
    def _generate_trading_recommendations(self, trading_data: Dict) -> List[str]:
        """Generate trading recommendations"""
        recommendations = []
        
        # Order execution recommendations
        total_orders = trading_data.get('total_orders', 0)
        filled_orders = trading_data.get('filled_orders', 0)
        if total_orders > 0:
            fill_rate = filled_orders / total_orders
            if fill_rate < 0.8:
                recommendations.append("Low fill rate - review order placement strategy")
            elif fill_rate > 0.95:
                recommendations.append("Excellent fill rate - good execution")
        
        # Capital utilization recommendations
        available_capital = trading_data.get('available_capital', 0.0)
        total_fill_value = trading_data.get('total_fill_value', 0.0)
        if total_fill_value > 0:
            utilization = total_fill_value / (available_capital + total_fill_value)
            if utilization < 0.3:
                recommendations.append("Low capital utilization - consider increasing position sizes")
            elif utilization > 0.8:
                recommendations.append("High capital utilization - monitor risk exposure")
        
        return recommendations
    
    def save_report(self, report: Dict, filename: str = None) -> str:
        """Save report to file"""
        if filename is None:
            filename = f"reports/{report['report_id']}.json"
        
        # Ensure reports directory exists
        import os
        os.makedirs("reports", exist_ok=True)
        
        # Save report
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Saved report to {filename}")
        return filename
    
    def get_report_summary(self) -> Dict:
        """Get reporting engine summary"""
        return {
            'total_reports': len(self.report_history),
            'performance_reports': len([r for r in self.report_history if r['report_type'] == 'PERFORMANCE']),
            'risk_reports': len([r for r in self.report_history if r['report_type'] == 'RISK']),
            'trading_reports': len([r for r in self.report_history if r['report_type'] == 'TRADING']),
            'latest_report': self.report_history[-1]['report_id'] if self.report_history else None
        } 