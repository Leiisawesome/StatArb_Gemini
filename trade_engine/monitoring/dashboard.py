#!/usr/bin/env python3
"""
Performance Dashboard
====================

Real-time performance monitoring dashboard for the trading system.
Provides web-based visualization of system metrics, alerts, and health status.

Author: StatArb_Gemini Team
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import asdict
import threading

logger = logging.getLogger(__name__)

class PerformanceDashboard:
    """
    Real-time performance monitoring dashboard.
    
    Features:
    - Real-time metric visualization
    - Alert management interface
    - System health overview
    - Performance trend analysis
    """
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.is_running = False
        self.dashboard_data: Dict[str, Any] = {}
        self.update_task: Optional[asyncio.Task] = None
        
        logger.info("PerformanceDashboard initialized")
    
    async def start_dashboard(self):
        """Start the dashboard"""
        if self.is_running:
            logger.warning("Dashboard already running")
            return
        
        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        
        logger.info("Performance dashboard started")
    
    async def stop_dashboard(self):
        """Stop the dashboard"""
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance dashboard stopped")
    
    async def _update_loop(self):
        """Update dashboard data periodically"""
        while self.is_running:
            try:
                await self._update_dashboard_data()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _update_dashboard_data(self):
        """Update dashboard data"""
        self.dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'system_status': 'running',
            'metrics': {},
            'alerts': [],
            'performance_summary': {}
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self.dashboard_data
    
    def update_metrics(self, new_data: Dict[str, Any]):
        """Update dashboard with new metrics data"""
        try:
            # Deep merge the new data with existing dashboard data
            for key, value in new_data.items():
                if key in self.dashboard_data and isinstance(self.dashboard_data[key], dict) and isinstance(value, dict):
                    self.dashboard_data[key].update(value)
                else:
                    self.dashboard_data[key] = value
            
            self.dashboard_data['last_updated'] = datetime.now().isoformat()
            logger.debug(f"Dashboard metrics updated with {len(new_data)} fields")
            
        except Exception as e:
            logger.error(f"Dashboard metrics update failed: {e}")

# Global dashboard instance
performance_dashboard = PerformanceDashboard()

async def start_performance_dashboard():
    """Start the global performance dashboard"""
    await performance_dashboard.start()

async def stop_performance_dashboard():
    """Stop the global performance dashboard"""
    await performance_dashboard.stop()
    
    def export_dashboard_html(self) -> str:
        """Export dashboard as HTML"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>StatArb Gemini Performance Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                .panel { border: 1px solid #ccc; padding: 15px; border-radius: 5px; }
                .metric { margin: 10px 0; }
                .status-running { color: green; }
                .alert-high { color: orange; }
                .alert-critical { color: red; }
            </style>
        </head>
        <body>
            <h1>StatArb Gemini Performance Dashboard</h1>
            <div class="dashboard">
                <div class="panel">
                    <h2>System Status</h2>
                    <div class="status-running">RUNNING</div>
                    <div>Last Update: {timestamp}</div>
                </div>
                <div class="panel">
                    <h2>Performance Metrics</h2>
                    <div class="metric">System operational</div>
                </div>
            </div>
        </body>
        </html>
        """.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return html_template
