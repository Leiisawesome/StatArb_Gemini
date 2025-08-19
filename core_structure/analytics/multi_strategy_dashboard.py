#!/usr/bin/env python3
"""
Multi-Strategy Analytics Dashboard
=================================

Advanced analytics dashboard for multi-strategy trading systems with:
- Real-time performance visualization
- Strategy correlation analysis
- Risk attribution and decomposition
- Performance attribution analysis
- Interactive strategy comparison
- Research platform integration

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import numpy as np
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class DashboardConfig:
    """Configuration for analytics dashboard"""
    update_frequency: int = 60  # seconds
    lookback_days: int = 252
    enable_real_time: bool = True
    enable_alerts: bool = True
    export_formats: List[str] = field(default_factory=lambda: ['json', 'csv'])

class MultiStrategyDashboard:
    """
    Advanced analytics dashboard for multi-strategy systems
    """
    
    def __init__(self, config: DashboardConfig = None):
        self.config = config or DashboardConfig()
        self.dashboard_data = {}
        self.performance_history = defaultdict(list)
        self.correlation_matrix = {}
        self.attribution_analysis = {}
        self.last_update = None
        
    async def generate_comprehensive_dashboard(
        self, 
        strategy_results: Dict[str, Any],
        performance_comparison: Dict[str, Any] = None,
        market_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive analytics dashboard"""
        logger.info("📊 Generating comprehensive multi-strategy dashboard...")
        
        try:
            dashboard = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'strategies_count': len(strategy_results),
                    'analysis_period': self.config.lookback_days,
                    'dashboard_version': '3.0.0'
                },
                'executive_summary': await self._generate_executive_summary(strategy_results),
                'performance_overview': await self._generate_performance_overview(strategy_results),
                'strategy_comparison': await self._generate_strategy_comparison(strategy_results),
                'risk_analysis': await self._generate_risk_analysis(strategy_results),
                'correlation_analysis': await self._generate_correlation_analysis(strategy_results),
                'attribution_analysis': await self._generate_attribution_analysis(strategy_results),
                'alerts_and_recommendations': await self._generate_alerts_and_recommendations(strategy_results),
                'research_insights': await self._generate_research_insights(strategy_results, market_data)
            }
            
            # Store dashboard data
            self.dashboard_data = dashboard
            self.last_update = datetime.now()
            
            logger.info("✅ Comprehensive dashboard generated successfully")
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return {'error': str(e)}
    
    async def _generate_executive_summary(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        try:
            # Calculate aggregate metrics
            total_strategies = len(strategy_results)
            total_signals = sum(result.get('signals_generated', 0) for result in strategy_results.values())
            total_trades = sum(result.get('trades_executed', 0) for result in strategy_results.values())
            
            # Performance metrics
            avg_sharpe = np.mean([result.get('sharpe_ratio', 0) for result in strategy_results.values()])
            avg_return = np.mean([result.get('annualized_return', 0) for result in strategy_results.values()])
            max_drawdown = min([result.get('max_drawdown', 0) for result in strategy_results.values()])
            
            # Strategy performance distribution
            regimes = [result.get('performance_regime', 'average') for result in strategy_results.values()]
            regime_distribution = {regime: regimes.count(regime) for regime in set(regimes)}
            
            return {
                'portfolio_overview': {
                    'total_strategies': total_strategies,
                    'active_strategies': sum(1 for r in strategy_results.values() if r.get('status') == 'completed'),
                    'total_signals_generated': total_signals,
                    'total_trades_executed': total_trades,
                    'signal_to_trade_ratio': total_trades / total_signals if total_signals > 0 else 0
                },
                'performance_summary': {
                    'average_sharpe_ratio': round(avg_sharpe, 3),
                    'average_annualized_return': round(avg_return * 100, 2),  # Convert to percentage
                    'portfolio_max_drawdown': round(max_drawdown * 100, 2),  # Convert to percentage
                    'best_performing_strategy': max(strategy_results.keys(), key=lambda k: strategy_results[k].get('sharpe_ratio', 0)),
                    'worst_performing_strategy': min(strategy_results.keys(), key=lambda k: strategy_results[k].get('sharpe_ratio', 0))
                },
                'regime_distribution': regime_distribution,
                'key_insights': [
                    f"Portfolio generated {total_signals:,} signals and executed {total_trades:,} trades",
                    f"Average Sharpe ratio of {avg_sharpe:.2f} across {total_strategies} strategies",
                    f"Maximum drawdown contained to {max_drawdown*100:.1f}%",
                    f"Strategy performance: {regime_distribution.get('excellent', 0)} excellent, {regime_distribution.get('good', 0)} good, {regime_distribution.get('average', 0)} average"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return {'error': str(e)}
    
    async def _generate_performance_overview(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed performance overview"""
        try:
            performance_data = {}
            
            for strategy_id, results in strategy_results.items():
                performance_data[strategy_id] = {
                    'returns': {
                        'total_return': results.get('total_return', 0),
                        'annualized_return': results.get('annualized_return', 0),
                        'daily_return': results.get('daily_return', 0)
                    },
                    'risk_metrics': {
                        'volatility': results.get('volatility', 0),
                        'max_drawdown': results.get('max_drawdown', 0),
                        'var_95': results.get('var_95', 0)
                    },
                    'risk_adjusted_metrics': {
                        'sharpe_ratio': results.get('sharpe_ratio', 0),
                        'sortino_ratio': results.get('sortino_ratio', 0),
                        'calmar_ratio': results.get('calmar_ratio', 0)
                    },
                    'trading_metrics': {
                        'win_rate': results.get('win_rate', 0),
                        'profit_factor': results.get('profit_factor', 0),
                        'total_trades': results.get('trades_executed', 0),
                        'signals_generated': results.get('signals_generated', 0)
                    },
                    'performance_regime': {
                        'regime': results.get('performance_regime', 'average'),
                        'confidence': results.get('regime_confidence', 0.5)
                    }
                }
            
            # Calculate portfolio-level metrics
            portfolio_metrics = await self._calculate_portfolio_metrics(performance_data)
            
            return {
                'strategy_performance': performance_data,
                'portfolio_metrics': portfolio_metrics,
                'performance_rankings': await self._generate_performance_rankings(performance_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating performance overview: {e}")
            return {'error': str(e)}
    
    async def _generate_strategy_comparison(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategy comparison analysis"""
        try:
            if len(strategy_results) < 2:
                return {'message': 'Need at least 2 strategies for comparison'}
            
            comparison_metrics = ['sharpe_ratio', 'annualized_return', 'max_drawdown', 'volatility', 'win_rate']
            
            comparison_data = {}
            for metric in comparison_metrics:
                values = {strategy_id: results.get(metric, 0) for strategy_id, results in strategy_results.items()}
                
                comparison_data[metric] = {
                    'values': values,
                    'best': max(values.keys(), key=lambda k: values[k]) if metric != 'max_drawdown' else min(values.keys(), key=lambda k: values[k]),
                    'worst': min(values.keys(), key=lambda k: values[k]) if metric != 'max_drawdown' else max(values.keys(), key=lambda k: values[k]),
                    'average': np.mean(list(values.values())),
                    'std_dev': np.std(list(values.values()))
                }
            
            # Relative performance analysis
            relative_performance = {}
            for strategy_id in strategy_results.keys():
                relative_performance[strategy_id] = {
                    'vs_average': {},
                    'percentile_rank': {}
                }
                
                for metric in comparison_metrics:
                    strategy_value = strategy_results[strategy_id].get(metric, 0)
                    avg_value = comparison_data[metric]['average']
                    
                    if avg_value != 0:
                        relative_performance[strategy_id]['vs_average'][metric] = (strategy_value - avg_value) / avg_value
                    else:
                        relative_performance[strategy_id]['vs_average'][metric] = 0
                    
                    # Calculate percentile rank
                    all_values = list(comparison_data[metric]['values'].values())
                    percentile = (sum(1 for v in all_values if v <= strategy_value) / len(all_values)) * 100
                    relative_performance[strategy_id]['percentile_rank'][metric] = percentile
            
            return {
                'comparison_metrics': comparison_data,
                'relative_performance': relative_performance,
                'strategy_strengths': await self._identify_strategy_strengths(strategy_results),
                'diversification_benefits': await self._analyze_diversification_benefits(strategy_results)
            }
            
        except Exception as e:
            logger.error(f"Error generating strategy comparison: {e}")
            return {'error': str(e)}
    
    async def _generate_risk_analysis(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive risk analysis"""
        try:
            risk_analysis = {
                'individual_risk': {},
                'portfolio_risk': {},
                'risk_decomposition': {},
                'stress_scenarios': {}
            }
            
            # Individual strategy risk
            for strategy_id, results in strategy_results.items():
                risk_analysis['individual_risk'][strategy_id] = {
                    'volatility': results.get('volatility', 0),
                    'max_drawdown': results.get('max_drawdown', 0),
                    'var_95': results.get('var_95', 0),
                    'risk_adjusted_return': results.get('sharpe_ratio', 0),
                    'downside_deviation': results.get('sortino_ratio', 0),
                    'risk_level': self._classify_risk_level(results)
                }
            
            # Portfolio-level risk (simplified)
            portfolio_volatility = np.mean([results.get('volatility', 0) for results in strategy_results.values()])
            portfolio_max_drawdown = min([results.get('max_drawdown', 0) for results in strategy_results.values()])
            
            risk_analysis['portfolio_risk'] = {
                'portfolio_volatility': portfolio_volatility,
                'portfolio_max_drawdown': portfolio_max_drawdown,
                'diversification_ratio': await self._calculate_diversification_ratio(strategy_results),
                'risk_budget_allocation': await self._calculate_risk_budget(strategy_results)
            }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Error generating risk analysis: {e}")
            return {'error': str(e)}
    
    async def _generate_correlation_analysis(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate correlation analysis between strategies"""
        try:
            if len(strategy_results) < 2:
                return {'message': 'Need at least 2 strategies for correlation analysis'}
            
            # Mock correlation matrix (in production, would use actual return series)
            strategy_ids = list(strategy_results.keys())
            correlation_matrix = {}
            
            for i, strategy1 in enumerate(strategy_ids):
                correlation_matrix[strategy1] = {}
                for j, strategy2 in enumerate(strategy_ids):
                    if i == j:
                        correlation_matrix[strategy1][strategy2] = 1.0
                    else:
                        # Mock correlation (in production, calculate from actual returns)
                        correlation_matrix[strategy1][strategy2] = np.random.uniform(0.1, 0.7)
            
            # Analyze correlation patterns
            correlations = []
            for strategy1 in strategy_ids:
                for strategy2 in strategy_ids:
                    if strategy1 != strategy2:
                        correlations.append(correlation_matrix[strategy1][strategy2])
            
            avg_correlation = np.mean(correlations)
            max_correlation = max(correlations)
            min_correlation = min(correlations)
            
            return {
                'correlation_matrix': correlation_matrix,
                'correlation_statistics': {
                    'average_correlation': avg_correlation,
                    'maximum_correlation': max_correlation,
                    'minimum_correlation': min_correlation,
                    'diversification_score': 1 - avg_correlation  # Higher is better
                },
                'correlation_insights': [
                    f"Average inter-strategy correlation: {avg_correlation:.3f}",
                    f"Diversification score: {(1-avg_correlation):.3f} (higher is better)",
                    f"Correlation range: {min_correlation:.3f} to {max_correlation:.3f}"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating correlation analysis: {e}")
            return {'error': str(e)}
    
    async def _generate_attribution_analysis(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance attribution analysis"""
        try:
            attribution = {
                'return_attribution': {},
                'risk_attribution': {},
                'factor_attribution': {},
                'contribution_analysis': {}
            }
            
            total_portfolio_return = sum(results.get('total_return', 0) for results in strategy_results.values())
            
            # Return attribution
            for strategy_id, results in strategy_results.items():
                strategy_return = results.get('total_return', 0)
                contribution = strategy_return / len(strategy_results)  # Equal weight assumption
                
                attribution['return_attribution'][strategy_id] = {
                    'absolute_return': strategy_return,
                    'contribution_to_portfolio': contribution,
                    'percentage_contribution': (contribution / total_portfolio_return * 100) if total_portfolio_return != 0 else 0
                }
            
            # Risk attribution (simplified)
            total_risk = sum(results.get('volatility', 0) for results in strategy_results.values())
            
            for strategy_id, results in strategy_results.items():
                strategy_risk = results.get('volatility', 0)
                risk_contribution = strategy_risk / len(strategy_results)  # Equal weight assumption
                
                attribution['risk_attribution'][strategy_id] = {
                    'absolute_risk': strategy_risk,
                    'risk_contribution': risk_contribution,
                    'percentage_risk_contribution': (risk_contribution / total_risk * 100) if total_risk != 0 else 0
                }
            
            return attribution
            
        except Exception as e:
            logger.error(f"Error generating attribution analysis: {e}")
            return {'error': str(e)}
    
    async def _generate_alerts_and_recommendations(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alerts and recommendations"""
        try:
            alerts = []
            recommendations = []
            
            for strategy_id, results in strategy_results.items():
                # Performance alerts
                if results.get('performance_regime') == 'critical':
                    alerts.append({
                        'level': 'critical',
                        'strategy': strategy_id,
                        'message': f"Strategy {strategy_id} performance is critical",
                        'metric': 'performance_regime'
                    })
                
                # Risk alerts
                if results.get('max_drawdown', 0) < -0.20:
                    alerts.append({
                        'level': 'warning',
                        'strategy': strategy_id,
                        'message': f"High drawdown detected: {results.get('max_drawdown', 0)*100:.1f}%",
                        'metric': 'max_drawdown'
                    })
                
                # Recommendations
                if results.get('sharpe_ratio', 0) < 1.0:
                    recommendations.append({
                        'strategy': strategy_id,
                        'type': 'parameter_optimization',
                        'message': f"Consider parameter optimization for {strategy_id} (Sharpe: {results.get('sharpe_ratio', 0):.2f})",
                        'priority': 'medium'
                    })
            
            return {
                'active_alerts': alerts,
                'recommendations': recommendations,
                'alert_summary': {
                    'critical_alerts': len([a for a in alerts if a['level'] == 'critical']),
                    'warning_alerts': len([a for a in alerts if a['level'] == 'warning']),
                    'total_recommendations': len(recommendations)
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating alerts and recommendations: {e}")
            return {'error': str(e)}
    
    async def _generate_research_insights(
        self, 
        strategy_results: Dict[str, Any], 
        market_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate research insights and analysis"""
        try:
            insights = {
                'strategy_insights': [],
                'market_insights': [],
                'optimization_opportunities': [],
                'research_recommendations': []
            }
            
            # Strategy insights
            best_strategy = max(strategy_results.keys(), key=lambda k: strategy_results[k].get('sharpe_ratio', 0))
            worst_strategy = min(strategy_results.keys(), key=lambda k: strategy_results[k].get('sharpe_ratio', 0))
            
            insights['strategy_insights'] = [
                f"Best performing strategy: {best_strategy} (Sharpe: {strategy_results[best_strategy].get('sharpe_ratio', 0):.2f})",
                f"Worst performing strategy: {worst_strategy} (Sharpe: {strategy_results[worst_strategy].get('sharpe_ratio', 0):.2f})",
                f"Strategy performance spread: {strategy_results[best_strategy].get('sharpe_ratio', 0) - strategy_results[worst_strategy].get('sharpe_ratio', 0):.2f} Sharpe units"
            ]
            
            # Optimization opportunities
            for strategy_id, results in strategy_results.items():
                if results.get('win_rate', 0) < 0.4:
                    insights['optimization_opportunities'].append(
                        f"{strategy_id}: Low win rate ({results.get('win_rate', 0)*100:.1f}%) - consider entry criteria optimization"
                    )
                
                if results.get('profit_factor', 0) < 1.5:
                    insights['optimization_opportunities'].append(
                        f"{strategy_id}: Low profit factor ({results.get('profit_factor', 0):.2f}) - consider exit strategy optimization"
                    )
            
            # Research recommendations
            insights['research_recommendations'] = [
                "Conduct walk-forward analysis on best performing strategies",
                "Investigate correlation patterns for portfolio optimization",
                "Analyze market regime sensitivity across strategies",
                "Consider ensemble methods for signal combination"
            ]
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating research insights: {e}")
            return {'error': str(e)}
    
    # Helper methods
    def _classify_risk_level(self, results: Dict[str, Any]) -> str:
        """Classify risk level based on metrics"""
        volatility = results.get('volatility', 0)
        max_drawdown = abs(results.get('max_drawdown', 0))
        
        if volatility > 0.3 or max_drawdown > 0.25:
            return 'high'
        elif volatility > 0.2 or max_drawdown > 0.15:
            return 'medium'
        else:
            return 'low'
    
    async def _calculate_portfolio_metrics(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio-level metrics"""
        # Simplified portfolio metrics (equal weight assumption)
        returns = [data['returns']['annualized_return'] for data in performance_data.values()]
        volatilities = [data['risk_metrics']['volatility'] for data in performance_data.values()]
        sharpes = [data['risk_adjusted_metrics']['sharpe_ratio'] for data in performance_data.values()]
        
        return {
            'portfolio_return': np.mean(returns),
            'portfolio_volatility': np.mean(volatilities),  # Simplified
            'portfolio_sharpe': np.mean(sharpes),
            'return_range': [min(returns), max(returns)],
            'volatility_range': [min(volatilities), max(volatilities)]
        }
    
    async def _generate_performance_rankings(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance rankings"""
        rankings = {}
        
        metrics = ['sharpe_ratio', 'annualized_return', 'win_rate', 'profit_factor']
        
        for metric in metrics:
            if metric == 'sharpe_ratio':
                values = {sid: data['risk_adjusted_metrics']['sharpe_ratio'] for sid, data in performance_data.items()}
            elif metric == 'annualized_return':
                values = {sid: data['returns']['annualized_return'] for sid, data in performance_data.items()}
            elif metric == 'win_rate':
                values = {sid: data['trading_metrics']['win_rate'] for sid, data in performance_data.items()}
            elif metric == 'profit_factor':
                values = {sid: data['trading_metrics']['profit_factor'] for sid, data in performance_data.items()}
            
            rankings[metric] = sorted(values.keys(), key=lambda k: values[k], reverse=True)
        
        return rankings
    
    async def _identify_strategy_strengths(self, strategy_results: Dict[str, Any]) -> Dict[str, List[str]]:
        """Identify each strategy's strengths"""
        strengths = {}
        
        for strategy_id, results in strategy_results.items():
            strategy_strengths = []
            
            if results.get('sharpe_ratio', 0) > 1.5:
                strategy_strengths.append('High risk-adjusted returns')
            if results.get('win_rate', 0) > 0.6:
                strategy_strengths.append('High win rate')
            if results.get('max_drawdown', 0) > -0.1:
                strategy_strengths.append('Low drawdown')
            if results.get('profit_factor', 0) > 2.0:
                strategy_strengths.append('Strong profit factor')
            
            strengths[strategy_id] = strategy_strengths
        
        return strengths
    
    async def _analyze_diversification_benefits(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze diversification benefits"""
        return {
            'diversification_score': 0.75,  # Mock score
            'correlation_reduction': 0.25,   # Mock reduction
            'risk_reduction': 0.15,          # Mock risk reduction
            'benefits': [
                'Reduced portfolio volatility through diversification',
                'Lower correlation between strategies improves risk-adjusted returns',
                'Multiple strategies provide robustness across market conditions'
            ]
        }
    
    async def _calculate_diversification_ratio(self, strategy_results: Dict[str, Any]) -> float:
        """Calculate diversification ratio"""
        # Simplified calculation
        return 0.85  # Mock diversification ratio
    
    async def _calculate_risk_budget(self, strategy_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate risk budget allocation"""
        # Equal risk budget allocation (simplified)
        return {strategy_id: 1.0 / len(strategy_results) for strategy_id in strategy_results.keys()}
    
    async def export_dashboard(self, format: str = 'json') -> str:
        """Export dashboard data"""
        if format == 'json':
            return json.dumps(self.dashboard_data, indent=2, default=str)
        elif format == 'csv':
            # Convert to CSV format (simplified)
            return "Dashboard CSV export not implemented yet"
        else:
            raise ValueError(f"Unsupported export format: {format}")

# Factory function
async def create_dashboard(config: DashboardConfig = None) -> MultiStrategyDashboard:
    """Create and initialize multi-strategy dashboard"""
    dashboard = MultiStrategyDashboard(config)
    logger.info("✅ Multi-strategy analytics dashboard initialized")
    return dashboard
