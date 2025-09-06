#!/usr/bin/env python3
"""
Trading Dashboard Server
========================

Real-time web-based trading dashboard server.
Provides professional trading interface with real-time updates via WebSocket.

Author: Pro Quant Desk Trader
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path
import webbrowser
import threading

# Web server imports
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("⚠️  FastAPI not available. Install with: pip install fastapi uvicorn websockets")

from .data_collector import TradingDataCollector
from .analytics_engine import RealTimeAnalytics

logger = logging.getLogger(__name__)

class TradingDashboardServer:
    """
    Real-time trading dashboard server
    
    Features:
    - Real-time portfolio monitoring
    - Strategy performance tracking
    - Risk metrics dashboard
    - WebSocket-based live updates
    - Professional trading interface
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        
        # Core components
        self.data_collector = TradingDataCollector()
        self.analytics_engine = RealTimeAnalytics()
        
        # Web server
        self.app: Optional[FastAPI] = None
        self.server_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # WebSocket connections
        self.active_connections: Set[WebSocket] = set()
        
        # Dashboard data
        self.dashboard_data = {}
        self.last_update = datetime.now()
        
        if FASTAPI_AVAILABLE:
            self._setup_web_app()
        
        # Register analytics engine with data collector
        self.data_collector.add_update_callback(self._on_data_update)
        
        logger.info("🌐 Trading Dashboard Server initialized")
    
    def _setup_web_app(self):
        """Setup FastAPI web application"""
        self.app = FastAPI(title="Trading Dashboard", version="1.0.0")
        
        # Create static files directory
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Routes
        self.app.get("/")(self._dashboard_home)
        self.app.get("/api/data")(self._get_dashboard_data)
        self.app.get("/api/analytics")(self._get_analytics_data)
        self.app.websocket("/ws")(self._websocket_endpoint)
        
        logger.info("🔧 Web application configured")
    
    async def _dashboard_home(self):
        """Serve dashboard home page"""
        html_content = self._generate_dashboard_html()
        return HTMLResponse(content=html_content)
    
    async def _get_dashboard_data(self):
        """API endpoint for dashboard data"""
        return self.data_collector.get_current_data()
    
    async def _get_analytics_data(self):
        """API endpoint for analytics data"""
        return self.analytics_engine.get_analytics_summary()
    
    async def _websocket_endpoint(self, websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        try:
            # Send initial data
            initial_data = {
                'type': 'initial_data',
                'data': self.data_collector.get_current_data(),
                'analytics': self.analytics_engine.get_analytics_summary()
            }
            await websocket.send_text(json.dumps(initial_data))
            
            # Keep connection alive
            while True:
                await websocket.receive_text()  # Heartbeat
                
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
            logger.info("🔌 WebSocket client disconnected")
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    def _on_data_update(self, snapshot, performance_metrics):
        """Handle data updates from collector"""
        try:
            # Update analytics engine
            self.analytics_engine.update_data(snapshot, performance_metrics)
            
            # Prepare update data
            update_data = {
                'type': 'data_update',
                'timestamp': datetime.now().isoformat(),
                'data': self.data_collector.get_current_data(),
                'analytics': self.analytics_engine.get_analytics_summary(),
                'alerts': self.analytics_engine.get_real_time_alerts()
            }
            
            # Send to all WebSocket clients
            asyncio.create_task(self._broadcast_update(update_data))
            
        except Exception as e:
            logger.error(f"❌ Error handling data update: {e}")
    
    async def _broadcast_update(self, data: Dict):
        """Broadcast update to all connected clients"""
        if not self.active_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for websocket in self.active_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"❌ Error sending to WebSocket client: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.active_connections -= disconnected
    
    def register_trading_engine(self, engine):
        """Register trading engine for data collection"""
        self.data_collector.register_trading_engine(engine)
        logger.info("🔗 Trading engine registered with dashboard")
    
    async def start_server(self, open_browser: bool = True):
        """Start the dashboard server"""
        if not FASTAPI_AVAILABLE:
            logger.error("❌ FastAPI not available. Cannot start web server.")
            return
        
        if self.is_running:
            logger.warning("⚠️  Dashboard server already running")
            return
        
        try:
            # Start data collection
            self.data_collector.start_collection()
            
            # Start web server
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            self.is_running = True
            
            # Open browser
            if open_browser:
                url = f"http://{self.host}:{self.port}"
                threading.Timer(2.0, lambda: webbrowser.open(url)).start()
                logger.info(f"🌐 Opening dashboard in browser: {url}")
            
            logger.info(f"🚀 Dashboard server starting on http://{self.host}:{self.port}")
            await server.serve()
            
        except Exception as e:
            logger.error(f"❌ Error starting dashboard server: {e}")
            self.is_running = False
    
    def stop_server(self):
        """Stop the dashboard server"""
        if not self.is_running:
            return
        
        try:
            # Stop data collection
            self.data_collector.stop_collection()
            
            # Close WebSocket connections
            for websocket in self.active_connections:
                asyncio.create_task(websocket.close())
            self.active_connections.clear()
            
            self.is_running = False
            logger.info("🛑 Dashboard server stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping dashboard server: {e}")
    
    def _generate_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(0, 0, 0, 0.2);
            padding: 1rem 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 300;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .dashboard {
            padding: 2rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.2s ease;
        }
        
        .card:hover {
            transform: translateY(-2px);
        }
        
        .card h3 {
            margin-bottom: 1rem;
            color: #ffffff;
            font-weight: 500;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .metric-label {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }
        
        .metric-value {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .positive {
            color: #4CAF50;
        }
        
        .negative {
            color: #f44336;
        }
        
        .neutral {
            color: #ffffff;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .connected {
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            border: 1px solid #4CAF50;
        }
        
        .disconnected {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
            border: 1px solid #f44336;
        }
        
        .strategy-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .strategy-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .alert {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid #FFC107;
            color: #FFC107;
            padding: 0.8rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
        }
        
        .alert.high {
            background: rgba(244, 67, 54, 0.2);
            border-color: #f44336;
            color: #f44336;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            📊 Trading Dashboard
            <div class="status-indicator" id="statusIndicator"></div>
        </h1>
    </div>
    
    <div class="connection-status" id="connectionStatus">
        Connecting...
    </div>
    
    <div class="dashboard" id="dashboard">
        <div class="loading">
            <h3>🔄 Loading dashboard data...</h3>
            <p>Connecting to trading system...</p>
        </div>
    </div>

    <script>
        class TradingDashboard {
            constructor() {
                this.ws = null;
                this.data = {};
                this.analytics = {};
                this.isConnected = false;
                
                this.init();
            }
            
            init() {
                this.connectWebSocket();
                this.updateConnectionStatus();
            }
            
            connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    this.isConnected = true;
                    this.updateConnectionStatus();
                    console.log('📡 WebSocket connected');
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('❌ Error parsing WebSocket message:', error);
                    }
                };
                
                this.ws.onclose = () => {
                    this.isConnected = false;
                    this.updateConnectionStatus();
                    console.log('🔌 WebSocket disconnected');
                    
                    // Reconnect after 3 seconds
                    setTimeout(() => this.connectWebSocket(), 3000);
                };
                
                this.ws.onerror = (error) => {
                    console.error('❌ WebSocket error:', error);
                };
                
                // Send heartbeat every 30 seconds
                setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send('heartbeat');
                    }
                }, 30000);
            }
            
            handleMessage(message) {
                switch (message.type) {
                    case 'initial_data':
                        this.data = message.data;
                        this.analytics = message.analytics;
                        this.renderDashboard();
                        break;
                        
                    case 'data_update':
                        this.data = message.data;
                        this.analytics = message.analytics;
                        this.renderDashboard();
                        
                        // Handle alerts
                        if (message.alerts && message.alerts.length > 0) {
                            this.showAlerts(message.alerts);
                        }
                        break;
                }
            }
            
            updateConnectionStatus() {
                const statusEl = document.getElementById('connectionStatus');
                const indicatorEl = document.getElementById('statusIndicator');
                
                if (this.isConnected) {
                    statusEl.textContent = '🟢 Connected';
                    statusEl.className = 'connection-status connected';
                    indicatorEl.style.background = '#4CAF50';
                } else {
                    statusEl.textContent = '🔴 Disconnected';
                    statusEl.className = 'connection-status disconnected';
                    indicatorEl.style.background = '#f44336';
                }
            }
            
            renderDashboard() {
                const dashboard = document.getElementById('dashboard');
                
                dashboard.innerHTML = `
                    <div class="card">
                        <h3>📈 Portfolio Overview</h3>
                        <div class="metric">
                            <span class="metric-label">Portfolio Value</span>
                            <span class="metric-value neutral">$${this.formatNumber(this.data.portfolio_value || 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Total P&L</span>
                            <span class="metric-value ${this.getColorClass(this.data.total_pnl || 0)}">
                                $${this.formatNumber(this.data.total_pnl || 0)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Daily P&L</span>
                            <span class="metric-value ${this.getColorClass(this.data.daily_pnl || 0)}">
                                $${this.formatNumber(this.data.daily_pnl || 0)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Total Return</span>
                            <span class="metric-value ${this.getColorClass(this.data.performance_metrics?.total_return || 0)}">
                                ${this.formatPercent(this.data.performance_metrics?.total_return || 0)}
                            </span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🛡️ Risk Metrics</h3>
                        <div class="metric">
                            <span class="metric-label">Current Drawdown</span>
                            <span class="metric-value ${this.getColorClass(-(this.data.performance_metrics?.current_drawdown || 0))}">
                                ${this.formatPercent(this.data.performance_metrics?.current_drawdown || 0)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Max Drawdown</span>
                            <span class="metric-value ${this.getColorClass(-(this.data.performance_metrics?.max_drawdown || 0))}">
                                ${this.formatPercent(this.data.performance_metrics?.max_drawdown || 0)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Sharpe Ratio</span>
                            <span class="metric-value neutral">${this.formatNumber(this.data.performance_metrics?.sharpe_ratio || 0, 2)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Volatility</span>
                            <span class="metric-value neutral">${this.formatPercent(this.data.performance_metrics?.volatility || 0)}</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📊 Strategy Performance</h3>
                        <div class="strategy-grid">
                            ${this.renderStrategies()}
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📋 Active Positions</h3>
                        ${this.renderPositions()}
                    </div>
                `;
            }
            
            renderStrategies() {
                if (!this.data.strategy_performance) return '<p>No strategy data available</p>';
                
                return Object.entries(this.data.strategy_performance).map(([id, strategy]) => `
                    <div class="strategy-card">
                        <h4>${strategy.name || id}</h4>
                        <div class="metric">
                            <span class="metric-label">P&L</span>
                            <span class="metric-value ${this.getColorClass(strategy.current_pnl || 0)}">
                                $${this.formatNumber(strategy.current_pnl || 0)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Return</span>
                            <span class="metric-value ${this.getColorClass(strategy.return_pct || 0)}">
                                ${this.formatPercent((strategy.return_pct || 0) * 100)}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Positions</span>
                            <span class="metric-value neutral">${strategy.positions_count || 0}</span>
                        </div>
                    </div>
                `).join('');
            }
            
            renderPositions() {
                if (!this.data.positions || Object.keys(this.data.positions).length === 0) {
                    return '<p>No active positions</p>';
                }
                
                return Object.entries(this.data.positions).map(([id, position]) => `
                    <div class="metric">
                        <span class="metric-label">${position.symbol} (${position.strategy_id})</span>
                        <span class="metric-value ${this.getColorClass(position.pnl || 0)}">
                            ${position.quantity} @ $${this.formatNumber(position.entry_price || 0, 2)} 
                            (P&L: $${this.formatNumber(position.pnl || 0)})
                        </span>
                    </div>
                `).join('');
            }
            
            showAlerts(alerts) {
                // This would show alerts in a notification system
                alerts.forEach(alert => {
                    console.log(`🚨 ${alert.severity}: ${alert.message}`);
                });
            }
            
            formatNumber(num, decimals = 0) {
                return Number(num).toLocaleString('en-US', {
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals
                });
            }
            
            formatPercent(num) {
                return `${Number(num).toFixed(2)}%`;
            }
            
            getColorClass(value) {
                if (value > 0) return 'positive';
                if (value < 0) return 'negative';
                return 'neutral';
            }
        }
        
        // Initialize dashboard when page loads
        document.addEventListener('DOMContentLoaded', () => {
            new TradingDashboard();
        });
    </script>
</body>
</html>
        """

# Standalone server function for testing
async def run_dashboard_server(trading_engine=None, host="127.0.0.1", port=8080):
    """Run dashboard server standalone"""
    dashboard = TradingDashboardServer(host=host, port=port)
    
    if trading_engine:
        dashboard.register_trading_engine(trading_engine)
    
    await dashboard.start_server()

if __name__ == "__main__":
    # For testing
    asyncio.run(run_dashboard_server())
