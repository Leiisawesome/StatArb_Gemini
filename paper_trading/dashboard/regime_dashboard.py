#!/usr/bin/env python3
"""
Regime-Aware Trading Dashboard
==============================

Phase 3: Advanced Analytics & Real-Time Monitoring

Enhanced trading dashboard with regime-aware analytics, building on the existing
dashboard infrastructure to provide institutional-grade monitoring and insights.

Key Features:
- Real-time regime detection and visualization
- Regime-based performance attribution
- Strategy effectiveness by regime
- Predictive regime analytics
- Interactive regime transition charts
- Intelligent alerting for regime changes

Author: Professional Quant Enhancement - Phase 3
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import numpy as np

# Web framework imports
try:
    from fastapi import FastAPI, WebSocket, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Import existing dashboard components
from .dashboard_server import TradingDashboardServer
from .analytics_engine import RealTimeAnalytics
from .data_collector import TradingDataCollector

# Import Phase 3 analytics
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from core_structure.analytics.regime_analytics import (
        RegimeAnalyticsEngine, create_regime_analytics_engine, RegimeAnalyticsType
    )
    from core_structure.orchestration.multi_strategy_orchestrator import MultiStrategyOrchestrator
    from core_structure.components.portfolio.regime_aware_portfolio_manager import RegimeAwarePortfolioManager
    PHASE3_INTEGRATION_AVAILABLE = True
except ImportError:
    PHASE3_INTEGRATION_AVAILABLE = False

logger = logging.getLogger(__name__)

class RegimeAwareDashboard(TradingDashboardServer):
    """
    Enhanced Trading Dashboard with Regime Awareness
    
    Extends the existing TradingDashboardServer with regime-aware analytics,
    visualization, and monitoring capabilities.
    """
    
    def __init__(self, 
                 host: str = "127.0.0.1", 
                 port: int = 8080,
                 enable_regime_analytics: bool = True):
        
        # Initialize base dashboard
        super().__init__(host, port)
        
        self.enable_regime_analytics = enable_regime_analytics
        
        # Phase 3 components
        self.regime_analytics: Optional[RegimeAnalyticsEngine] = None
        self.regime_data_cache: Dict[str, Any] = {}
        self.regime_alerts: List[Dict] = []
        
        # Integration with Phase 1 & 2 systems
        self.orchestrator: Optional[MultiStrategyOrchestrator] = None
        self.portfolio_manager: Optional[RegimeAwarePortfolioManager] = None
        
        # Dashboard state
        self.regime_dashboard_data = {
            'current_regime': 'unknown',
            'regime_confidence': 0.0,
            'regime_duration': 0,
            'predicted_next_regime': 'unknown',
            'regime_performance': {},
            'strategy_effectiveness': {},
            'regime_transitions': [],
            'recommendations': []
        }
        
        if PHASE3_INTEGRATION_AVAILABLE and enable_regime_analytics:
            self.regime_analytics = create_regime_analytics_engine()
            logger.info("📊 Regime analytics engine initialized")
        
        # Add regime-specific routes
        if self.app:
            self._setup_regime_routes()
        
        logger.info("🧠 Regime-Aware Dashboard initialized")
    
    def integrate_phase_systems(self, 
                               orchestrator: Optional[MultiStrategyOrchestrator] = None,
                               portfolio_manager: Optional[RegimeAwarePortfolioManager] = None):
        """Integrate with Phase 1 & 2 systems"""
        
        self.orchestrator = orchestrator
        self.portfolio_manager = portfolio_manager
        
        # Integrate analytics engine
        if self.regime_analytics:
            self.regime_analytics.integrate_phase_systems(
                regime_system=None,  # Could integrate regime system here
                portfolio_manager=portfolio_manager,
                orchestrator=orchestrator
            )
        
        integration_count = sum([orchestrator is not None, portfolio_manager is not None])
        logger.info(f"🔗 Regime dashboard integrated with {integration_count}/2 Phase systems")
    
    def _setup_regime_routes(self):
        """Setup regime-specific API routes"""
        
        if not self.app:
            return
        
        # Regime analytics routes
        self.app.get("/api/regime/current")(self._get_current_regime)
        self.app.get("/api/regime/performance")(self._get_regime_performance)
        self.app.get("/api/regime/transitions")(self._get_regime_transitions)
        self.app.get("/api/regime/strategies")(self._get_strategy_effectiveness)
        self.app.get("/api/regime/predictions")(self._get_regime_predictions)
        self.app.get("/api/regime/alerts")(self._get_regime_alerts)
        
        # Enhanced dashboard route
        self.app.get("/regime")(self._regime_dashboard_home)
        
        logger.info("🛣️ Regime dashboard routes configured")
    
    async def _regime_dashboard_home(self):
        """Serve regime-aware dashboard home page"""
        
        html_content = self._generate_regime_dashboard_html()
        return HTMLResponse(content=html_content)
    
    async def _get_current_regime(self):
        """Get current regime information"""
        
        try:
            if self.regime_analytics:
                regime_summary = self.regime_analytics.get_real_time_regime_summary()
                return JSONResponse(content=regime_summary)
            
            # Fallback data
            return JSONResponse(content={
                'current_regime': 'unknown',
                'regime_confidence': 0.0,
                'predicted_next_regime': 'unknown',
                'prediction_confidence': 0.0,
                'last_update': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Current regime API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    async def _get_regime_performance(self):
        """Get regime performance analytics"""
        
        try:
            if not self.regime_analytics:
                return JSONResponse(content={'error': 'Regime analytics not available'})
            
            # Get performance analysis
            analysis = await self.regime_analytics.analyze_regime_performance()
            
            # Convert to JSON-serializable format
            performance_data = {
                'total_return': analysis.total_return,
                'regime_attribution': analysis.regime_attribution,
                'best_regime': analysis.best_regime,
                'worst_regime': analysis.worst_regime,
                'analysis_timestamp': analysis.timestamp.isoformat(),
                'regime_performance': {}
            }
            
            # Add regime performance details
            for regime, metrics in analysis.regime_performance.items():
                performance_data['regime_performance'][regime] = {
                    'total_return': metrics.total_return,
                    'annualized_return': metrics.annualized_return,
                    'volatility': metrics.volatility,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'max_drawdown': metrics.max_drawdown,
                    'win_rate': metrics.win_rate,
                    'profit_factor': metrics.profit_factor,
                    'duration_minutes': metrics.total_duration_minutes
                }
            
            return JSONResponse(content=performance_data)
            
        except Exception as e:
            logger.error(f"❌ Regime performance API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    async def _get_regime_transitions(self):
        """Get regime transition analysis"""
        
        try:
            if not self.regime_analytics:
                return JSONResponse(content={'transitions': []})
            
            # Get recent analysis
            analysis = await self.regime_analytics.analyze_regime_performance()
            
            # Convert transitions to JSON format
            transitions_data = []
            for transition in analysis.transition_analysis:
                transitions_data.append({
                    'from_regime': transition.from_regime,
                    'to_regime': transition.to_regime,
                    'count': transition.transition_count,
                    'avg_duration': transition.avg_transition_duration,
                    'performance': transition.transition_performance,
                    'volatility': transition.transition_volatility,
                    'predictability': transition.predictability_score
                })
            
            return JSONResponse(content={'transitions': transitions_data})
            
        except Exception as e:
            logger.error(f"❌ Regime transitions API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    async def _get_strategy_effectiveness(self):
        """Get strategy effectiveness by regime"""
        
        try:
            if not self.regime_analytics:
                return JSONResponse(content={'strategies': {}})
            
            # Get recent analysis
            analysis = await self.regime_analytics.analyze_regime_performance()
            
            # Convert strategy effectiveness to JSON format
            strategies_data = {}
            for strategy, effectiveness in analysis.strategy_effectiveness.items():
                strategies_data[strategy] = {
                    'optimal_regimes': effectiveness.optimal_regimes,
                    'suboptimal_regimes': effectiveness.suboptimal_regimes,
                    'consistency_score': effectiveness.consistency_score,
                    'adaptability_score': effectiveness.adaptability_score,
                    'regime_sensitivity': effectiveness.regime_sensitivity,
                    'regime_performance': {}
                }
                
                # Add regime-specific performance
                for regime, perf in effectiveness.regime_performance.items():
                    strategies_data[strategy]['regime_performance'][regime] = {
                        'total_return': perf.total_return,
                        'annualized_return': perf.annualized_return,
                        'sharpe_ratio': perf.sharpe_ratio,
                        'win_rate': perf.win_rate
                    }
            
            return JSONResponse(content={'strategies': strategies_data})
            
        except Exception as e:
            logger.error(f"❌ Strategy effectiveness API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    async def _get_regime_predictions(self):
        """Get regime predictions and forecasts"""
        
        try:
            if not self.regime_analytics:
                return JSONResponse(content={'predictions': {}})
            
            # Get recent analysis
            analysis = await self.regime_analytics.analyze_regime_performance()
            
            predictions_data = {
                'predicted_next_regime': analysis.predicted_next_regime,
                'regime_confidence': analysis.regime_confidence,
                'expected_duration': analysis.expected_regime_duration,
                'analysis_confidence': analysis.analysis_confidence,
                'data_quality_score': analysis.data_quality_score,
                'recommendations': analysis.recommendations
            }
            
            return JSONResponse(content={'predictions': predictions_data})
            
        except Exception as e:
            logger.error(f"❌ Regime predictions API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    async def _get_regime_alerts(self):
        """Get regime-related alerts"""
        
        try:
            # Generate sample alerts (in real implementation, would come from alert system)
            current_time = datetime.now()
            
            alerts = [
                {
                    'id': 'regime_change_001',
                    'type': 'regime_change',
                    'severity': 'HIGH',
                    'message': 'Regime changed from sideways to trending',
                    'timestamp': (current_time - timedelta(minutes=5)).isoformat(),
                    'regime_from': 'sideways',
                    'regime_to': 'trending',
                    'confidence': 0.85
                },
                {
                    'id': 'performance_alert_001',
                    'type': 'performance',
                    'severity': 'MEDIUM',
                    'message': 'Mean reversion strategy underperforming in current regime',
                    'timestamp': (current_time - timedelta(minutes=15)).isoformat(),
                    'strategy': 'mean_reversion',
                    'current_regime': 'trending',
                    'performance_impact': -0.02
                }
            ]
            
            return JSONResponse(content={'alerts': alerts})
            
        except Exception as e:
            logger.error(f"❌ Regime alerts API error: {e}")
            return JSONResponse(content={'error': str(e)}, status_code=500)
    
    def _generate_regime_dashboard_html(self) -> str:
        """Generate regime-aware dashboard HTML"""
        
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regime-Aware Trading Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            color: #ffffff;
        }
        .dashboard-header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .dashboard-card {
            background-color: #2d2d2d;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .card-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #4CAF50;
        }
        .regime-indicator {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .regime-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }
        .regime-trending { background-color: #4CAF50; }
        .regime-sideways { background-color: #FF9800; }
        .regime-volatile { background-color: #F44336; }
        .regime-crisis { background-color: #9C27B0; }
        .regime-unknown { background-color: #757575; }
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }
        .metric-label {
            color: #bbb;
        }
        .metric-value {
            font-weight: bold;
        }
        .positive { color: #4CAF50; }
        .negative { color: #F44336; }
        .neutral { color: #FF9800; }
        .recommendations {
            background-color: #1e3a8a;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin-top: 20px;
        }
        .alert {
            background-color: #dc2626;
            border-left: 4px solid #ef4444;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 15px;
        }
        .status-online {
            color: #4CAF50;
        }
        .status-offline {
            color: #F44336;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>🧠 Regime-Aware Trading Dashboard</h1>
        <p>Phase 3: Advanced Analytics & Real-Time Monitoring</p>
        <div id="connection-status">
            <span class="status-online">● Connected</span>
        </div>
    </div>

    <div class="dashboard-grid">
        <!-- Current Regime Card -->
        <div class="dashboard-card">
            <div class="card-title">📊 Current Market Regime</div>
            <div id="current-regime">
                <div class="regime-indicator">
                    <div class="regime-dot regime-unknown" id="regime-dot"></div>
                    <span id="regime-name">Loading...</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Confidence:</span>
                    <span class="metric-value" id="regime-confidence">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Duration:</span>
                    <span class="metric-value" id="regime-duration">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Predicted Next:</span>
                    <span class="metric-value" id="predicted-regime">--</span>
                </div>
            </div>
        </div>

        <!-- Performance Attribution Card -->
        <div class="dashboard-card">
            <div class="card-title">📈 Regime Performance</div>
            <div id="regime-performance">
                <div class="metric-row">
                    <span class="metric-label">Total Return:</span>
                    <span class="metric-value" id="total-return">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Best Regime:</span>
                    <span class="metric-value" id="best-regime">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Worst Regime:</span>
                    <span class="metric-value" id="worst-regime">--</span>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="performance-chart"></canvas>
            </div>
        </div>

        <!-- Strategy Effectiveness Card -->
        <div class="dashboard-card">
            <div class="card-title">🎯 Strategy Effectiveness</div>
            <div id="strategy-effectiveness">
                <div class="metric-row">
                    <span class="metric-label">Momentum:</span>
                    <span class="metric-value" id="momentum-score">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Mean Reversion:</span>
                    <span class="metric-value" id="mean-reversion-score">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Pairs Trading:</span>
                    <span class="metric-value" id="pairs-trading-score">--</span>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="strategy-chart"></canvas>
            </div>
        </div>

        <!-- Regime Transitions Card -->
        <div class="dashboard-card">
            <div class="card-title">🔄 Regime Transitions</div>
            <div id="regime-transitions">
                <div class="metric-row">
                    <span class="metric-label">Total Transitions:</span>
                    <span class="metric-value" id="total-transitions">--</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Most Common:</span>
                    <span class="metric-value" id="common-transition">--</span>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="transitions-chart"></canvas>
            </div>
        </div>
    </div>

    <!-- Recommendations Section -->
    <div class="recommendations">
        <h3>💡 AI Recommendations</h3>
        <div id="recommendations-list">
            Loading recommendations...
        </div>
    </div>

    <!-- Alerts Section -->
    <div id="alerts-section">
        <h3>🚨 Recent Alerts</h3>
        <div id="alerts-list">
            Loading alerts...
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        let ws = null;
        let charts = {};

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = function(event) {
                console.log('WebSocket connected');
                document.getElementById('connection-status').innerHTML = '<span class="status-online">● Connected</span>';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket disconnected');
                document.getElementById('connection-status').innerHTML = '<span class="status-offline">● Disconnected</span>';
                // Reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
        }

        function updateDashboard(data) {
            // Update current regime
            if (data.current_regime) {
                updateCurrentRegime(data.current_regime);
            }
            
            // Update performance
            if (data.performance) {
                updatePerformance(data.performance);
            }
            
            // Update strategies
            if (data.strategies) {
                updateStrategies(data.strategies);
            }
        }

        function updateCurrentRegime(regimeData) {
            const regimeName = document.getElementById('regime-name');
            const regimeDot = document.getElementById('regime-dot');
            const regimeConfidence = document.getElementById('regime-confidence');
            const predictedRegime = document.getElementById('predicted-regime');
            
            regimeName.textContent = regimeData.regime || 'Unknown';
            regimeConfidence.textContent = `${(regimeData.confidence * 100).toFixed(1)}%`;
            predictedRegime.textContent = regimeData.predicted_next || 'Unknown';
            
            // Update regime dot color
            regimeDot.className = `regime-dot regime-${regimeData.regime || 'unknown'}`;
        }

        function updatePerformance(performanceData) {
            const totalReturn = document.getElementById('total-return');
            const bestRegime = document.getElementById('best-regime');
            const worstRegime = document.getElementById('worst-regime');
            
            totalReturn.textContent = `${(performanceData.total_return * 100).toFixed(2)}%`;
            totalReturn.className = `metric-value ${performanceData.total_return >= 0 ? 'positive' : 'negative'}`;
            
            bestRegime.textContent = performanceData.best_regime || '--';
            worstRegime.textContent = performanceData.worst_regime || '--';
        }

        function updateStrategies(strategiesData) {
            // Update strategy scores (simplified)
            const momentumScore = document.getElementById('momentum-score');
            const meanReversionScore = document.getElementById('mean-reversion-score');
            const pairsTradingScore = document.getElementById('pairs-trading-score');
            
            if (strategiesData.momentum) {
                momentumScore.textContent = `${(strategiesData.momentum.consistency_score * 100).toFixed(1)}%`;
            }
            if (strategiesData.mean_reversion) {
                meanReversionScore.textContent = `${(strategiesData.mean_reversion.consistency_score * 100).toFixed(1)}%`;
            }
            if (strategiesData.pairs_trading) {
                pairsTradingScore.textContent = `${(strategiesData.pairs_trading.consistency_score * 100).toFixed(1)}%`;
            }
        }

        // Load initial data
        async function loadInitialData() {
            try {
                // Load current regime
                const regimeResponse = await fetch('/api/regime/current');
                const regimeData = await regimeResponse.json();
                updateCurrentRegime(regimeData);
                
                // Load performance
                const performanceResponse = await fetch('/api/regime/performance');
                const performanceData = await performanceResponse.json();
                updatePerformance(performanceData);
                
                // Load strategies
                const strategiesResponse = await fetch('/api/regime/strategies');
                const strategiesData = await strategiesResponse.json();
                updateStrategies(strategiesData.strategies);
                
                // Load recommendations
                const predictionsResponse = await fetch('/api/regime/predictions');
                const predictionsData = await predictionsResponse.json();
                updateRecommendations(predictionsData.predictions.recommendations);
                
                // Load alerts
                const alertsResponse = await fetch('/api/regime/alerts');
                const alertsData = await alertsResponse.json();
                updateAlerts(alertsData.alerts);
                
            } catch (error) {
                console.error('Error loading initial data:', error);
            }
        }

        function updateRecommendations(recommendations) {
            const recommendationsList = document.getElementById('recommendations-list');
            if (recommendations && recommendations.length > 0) {
                recommendationsList.innerHTML = recommendations.map(rec => `<div>• ${rec}</div>`).join('');
            } else {
                recommendationsList.innerHTML = 'No recommendations available';
            }
        }

        function updateAlerts(alerts) {
            const alertsList = document.getElementById('alerts-list');
            if (alerts && alerts.length > 0) {
                alertsList.innerHTML = alerts.map(alert => 
                    `<div class="alert">
                        <strong>${alert.severity}:</strong> ${alert.message}
                        <br><small>${new Date(alert.timestamp).toLocaleString()}</small>
                    </div>`
                ).join('');
            } else {
                alertsList.innerHTML = 'No recent alerts';
            }
        }

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            loadInitialData();
            connectWebSocket();
            
            // Refresh data every 30 seconds
            setInterval(loadInitialData, 30000);
        });
    </script>
</body>
</html>
        """
    
    async def start_regime_monitoring(self):
        """Start regime monitoring and analytics"""
        
        if not self.regime_analytics:
            logger.warning("⚠️ Regime analytics not available")
            return
        
        logger.info("🔄 Starting regime monitoring...")
        
        # Start periodic analytics updates
        asyncio.create_task(self._periodic_regime_analysis())
        
        logger.info("✅ Regime monitoring started")
    
    async def _periodic_regime_analysis(self):
        """Periodic regime analysis and cache updates"""
        
        while True:
            try:
                if self.regime_analytics:
                    # Run regime analysis
                    analysis = await self.regime_analytics.analyze_regime_performance()
                    
                    # Update cache
                    self.regime_data_cache = {
                        'current_regime': analysis.predicted_next_regime,
                        'regime_confidence': analysis.regime_confidence,
                        'performance': {
                            'total_return': analysis.total_return,
                            'best_regime': analysis.best_regime,
                            'worst_regime': analysis.worst_regime,
                            'regime_attribution': analysis.regime_attribution
                        },
                        'strategies': analysis.strategy_effectiveness,
                        'recommendations': analysis.recommendations,
                        'last_update': datetime.now().isoformat()
                    }
                    
                    # Broadcast to WebSocket clients
                    await self._broadcast_regime_update()
                
                # Wait 60 seconds before next analysis
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Periodic regime analysis failed: {e}")
                await asyncio.sleep(60)  # Continue despite errors
    
    async def _broadcast_regime_update(self):
        """Broadcast regime updates to WebSocket clients"""
        
        if not self.active_connections:
            return
        
        try:
            message = json.dumps({
                'type': 'regime_update',
                'data': self.regime_data_cache
            })
            
            # Send to all connected clients
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for connection in disconnected:
                self.active_connections.discard(connection)
                
        except Exception as e:
            logger.error(f"❌ WebSocket broadcast failed: {e}")

# Factory function for easy initialization
def create_regime_aware_dashboard(
    host: str = "127.0.0.1",
    port: int = 8080,
    enable_regime_analytics: bool = True,
    orchestrator: Optional[MultiStrategyOrchestrator] = None,
    portfolio_manager: Optional[RegimeAwarePortfolioManager] = None
) -> RegimeAwareDashboard:
    """
    Factory function to create a regime-aware dashboard
    
    Args:
        host: Dashboard host address
        port: Dashboard port
        enable_regime_analytics: Enable regime analytics features
        orchestrator: Phase 2 orchestrator (optional)
        portfolio_manager: Phase 2 portfolio manager (optional)
        
    Returns:
        Configured RegimeAwareDashboard instance
    """
    
    dashboard = RegimeAwareDashboard(
        host=host,
        port=port,
        enable_regime_analytics=enable_regime_analytics
    )
    
    # Integrate with Phase systems if provided
    if orchestrator or portfolio_manager:
        dashboard.integrate_phase_systems(orchestrator, portfolio_manager)
    
    return dashboard
