"""
Regime Dashboard Panel for Paper Trading
========================================

Real-time regime monitoring dashboard component that integrates
with the paper trading dashboard.

Author: Assistant
Date: September 2025
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

# Dashboard framework imports (Dash/Plotly)
try:
    import dash
    from dash import dcc, html, Input, Output, State
    import plotly.graph_objs as go
    import plotly.express as px
    from dash.exceptions import PreventUpdate
    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False

# Import regime monitoring
from core_structure.regime_monitoring import RegimeDashboardDataProvider

# ================================================================================
# REGIME DASHBOARD PANEL
# ================================================================================

class RegimeDashboardPanel:
    """
    Real-time regime monitoring panel for trading dashboard
    
    Features:
    - Current regime display with confidence
    - Multi-timeframe regime view
    - Regime history chart
    - Transition notifications
    - Performance metrics by regime
    - Alert feed
    """
    
    def __init__(self, data_provider: RegimeDashboardDataProvider):
        self.data_provider = data_provider
        self.update_interval = 5  # seconds
        
    def create_layout(self) -> html.Div:
        """Create dashboard layout"""
        if not DASH_AVAILABLE:
            return html.Div("Dashboard requires Dash/Plotly installation")
        
        return html.Div([
            # Header
            html.Div([
                html.H2("🎯 Market Regime Monitor", className="panel-header"),
                html.Div(id="regime-last-update", className="last-update")
            ], className="panel-header-container"),
            
            # Current Regime Display
            html.Div([
                html.Div([
                    html.H3("Current Regime", className="section-header"),
                    html.Div(id="current-regime-display", className="regime-display")
                ], className="regime-section"),
                
                # Confidence Gauge
                html.Div([
                    html.H3("Confidence", className="section-header"),
                    dcc.Graph(id="confidence-gauge", config={'displayModeBar': False})
                ], className="gauge-section")
            ], className="current-regime-container"),
            
            # Multi-Timeframe View
            html.Div([
                html.H3("Multi-Timeframe Analysis", className="section-header"),
                html.Div(id="timeframe-grid", className="timeframe-grid")
            ], className="timeframe-section"),
            
            # Regime History Chart
            html.Div([
                html.H3("Regime History (24h)", className="section-header"),
                dcc.Graph(id="regime-history-chart")
            ], className="history-section"),
            
            # Stability Scores
            html.Div([
                html.H3("Regime Stability", className="section-header"),
                dcc.Graph(id="stability-chart", config={'displayModeBar': False})
            ], className="stability-section"),
            
            # Alert Feed
            html.Div([
                html.H3("Recent Alerts", className="section-header"),
                html.Div(id="alert-feed", className="alert-feed")
            ], className="alert-section"),
            
            # Update interval
            dcc.Interval(
                id='regime-update-interval',
                interval=self.update_interval * 1000,  # milliseconds
                n_intervals=0
            ),
            
            # Hidden div to store data
            html.Div(id='regime-data-store', style={'display': 'none'})
        ], className="regime-dashboard-panel")
    
    def register_callbacks(self, app):
        """Register Dash callbacks for updates"""
        
        @app.callback(
            [Output('regime-data-store', 'children'),
             Output('regime-last-update', 'children')],
            [Input('regime-update-interval', 'n_intervals')]
        )
        def update_data(n):
            """Fetch latest regime data"""
            data = {
                'current': self.data_provider.get_current_state(),
                'historical': self.data_provider.get_historical_data(hours=24)
            }
            
            return (
                json.dumps(data),
                f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
            )
        
        @app.callback(
            Output('current-regime-display', 'children'),
            [Input('regime-data-store', 'children')]
        )
        def update_current_regime(data_json):
            """Update current regime display"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            current = data['current']
            
            if current.get('status') == 'no_regime':
                return html.Div("No regime detected", className="no-regime")
            
            regime_info = current['current_regime']
            regime_type = regime_info['type']
            
            # Style based on regime type
            regime_colors = {
                'bull_trend': '#00cc88',
                'bear_trend': '#ff3366',
                'high_volatility': '#ff9933',
                'sideways': '#6666ff',
                'crisis': '#cc0000',
                'unknown': '#999999'
            }
            
            color = regime_colors.get(regime_type, '#999999')
            
            return html.Div([
                html.Div(regime_type.upper().replace('_', ' '), 
                        className="regime-type",
                        style={'color': color}),
                html.Div([
                    html.Span(f"Volatility: {regime_info['volatility']:.3f}"),
                    html.Span(" | "),
                    html.Span(f"Trend: {regime_info['trend']:.3f}")
                ], className="regime-details"),
                html.Div(f"Duration: {regime_info['duration']:.0f} minutes",
                        className="regime-duration")
            ])
        
        @app.callback(
            Output('confidence-gauge', 'figure'),
            [Input('regime-data-store', 'children')]
        )
        def update_confidence_gauge(data_json):
            """Update confidence gauge"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            current = data['current']
            
            if current.get('status') == 'no_regime':
                confidence = 0
            else:
                confidence = current['current_regime']['confidence']
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=confidence * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': ""},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': self._get_confidence_color(confidence)},
                    'steps': [
                        {'range': [0, 30], 'color': "lightgray"},
                        {'range': [30, 70], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            return fig
        
        @app.callback(
            Output('timeframe-grid', 'children'),
            [Input('regime-data-store', 'children')]
        )
        def update_timeframe_grid(data_json):
            """Update multi-timeframe grid"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            current = data['current']
            
            timeframes = current.get('multi_timeframe', {})
            
            if not timeframes:
                return html.Div("No multi-timeframe data", className="no-data")
            
            grid_items = []
            for tf, regime in timeframes.items():
                grid_items.append(
                    html.Div([
                        html.Div(tf, className="tf-label"),
                        html.Div(regime.upper().replace('_', ' '), 
                                className="tf-regime")
                    ], className="tf-item")
                )
            
            return grid_items
        
        @app.callback(
            Output('regime-history-chart', 'figure'),
            [Input('regime-data-store', 'children')]
        )
        def update_history_chart(data_json):
            """Update regime history chart"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            historical = data['historical']
            
            regime_history = historical.get('regime_history', [])
            if not regime_history:
                return go.Figure()
            
            df = pd.DataFrame(regime_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create regime timeline
            fig = go.Figure()
            
            # Map regimes to numeric values for visualization
            regime_map = {
                'bull_trend': 3,
                'sideways': 2,
                'bear_trend': 1,
                'high_volatility': 0,
                'crisis': -1,
                'unknown': 1.5
            }
            
            df['regime_numeric'] = df['regime_type'].map(regime_map)
            
            # Add regime areas
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['regime_numeric'],
                mode='lines',
                line=dict(width=0),
                fill='tozeroy',
                fillcolor='rgba(100,100,100,0.2)',
                showlegend=False
            ))
            
            # Add confidence overlay
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['confidence'],
                mode='lines',
                name='Confidence',
                yaxis='y2',
                line=dict(color='orange', width=2)
            ))
            
            # Add transition markers
            transitions = historical.get('transitions', [])
            for transition in transitions:
                fig.add_vline(
                    x=transition['timestamp'],
                    line_width=1,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"{transition['from_regime']}→{transition['to_regime']}"
                )
            
            fig.update_layout(
                xaxis_title="Time",
                yaxis=dict(
                    title="Regime",
                    tickmode='array',
                    tickvals=list(regime_map.values()),
                    ticktext=list(regime_map.keys())
                ),
                yaxis2=dict(
                    title="Confidence",
                    overlaying='y',
                    side='right',
                    range=[0, 1]
                ),
                height=300,
                margin=dict(l=50, r=50, t=20, b=50)
            )
            
            return fig
        
        @app.callback(
            Output('stability-chart', 'figure'),
            [Input('regime-data-store', 'children')]
        )
        def update_stability_chart(data_json):
            """Update stability scores chart"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            current = data['current']
            
            stability_scores = current.get('stability_scores', {})
            
            if not stability_scores:
                return go.Figure()
            
            regimes = list(stability_scores.keys())
            scores = list(stability_scores.values())
            
            fig = go.Figure(go.Bar(
                x=scores,
                y=regimes,
                orientation='h',
                marker_color=['green' if s > 0.7 else 'orange' if s > 0.4 else 'red' 
                             for s in scores]
            ))
            
            fig.update_layout(
                xaxis_title="Stability Score",
                xaxis_range=[0, 1],
                height=200,
                margin=dict(l=100, r=20, t=20, b=40)
            )
            
            return fig
        
        @app.callback(
            Output('alert-feed', 'children'),
            [Input('regime-data-store', 'children')]
        )
        def update_alert_feed(data_json):
            """Update alert feed"""
            if not data_json:
                raise PreventUpdate
            
            data = json.loads(data_json)
            current = data['current']
            
            alerts = current.get('active_alerts', [])
            
            if not alerts:
                return html.Div("No recent alerts", className="no-alerts")
            
            alert_items = []
            for alert in alerts[-5:]:  # Show last 5 alerts
                severity_class = f"alert-{alert['severity']}"
                
                alert_items.append(
                    html.Div([
                        html.Div([
                            html.Span(alert['time'].split('T')[1][:8], 
                                     className="alert-time"),
                            html.Span(alert['severity'].upper(), 
                                     className=f"alert-severity {severity_class}")
                        ], className="alert-header"),
                        html.Div(alert['message'], className="alert-message")
                    ], className="alert-item")
                )
            
            return alert_items
    
    def _get_confidence_color(self, confidence: float) -> str:
        """Get color based on confidence level"""
        if confidence > 0.8:
            return "#00cc88"
        elif confidence > 0.6:
            return "#ffcc00"
        elif confidence > 0.4:
            return "#ff9933"
        else:
            return "#ff3366"

# ================================================================================
# CSS STYLES
# ================================================================================

REGIME_PANEL_CSS = """
.regime-dashboard-panel {
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.panel-header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.panel-header {
    margin: 0;
    color: #333;
}

.last-update {
    font-size: 12px;
    color: #666;
}

.section-header {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 10px;
    color: #444;
}

.current-regime-container {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 20px;
    margin-bottom: 30px;
}

.regime-display {
    padding: 20px;
    background: white;
    border-radius: 8px;
    text-align: center;
}

.regime-type {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 10px;
}

.regime-details {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.regime-duration {
    font-size: 12px;
    color: #999;
}

.timeframe-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 20px;
}

.tf-item {
    background: white;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
}

.tf-label {
    font-size: 12px;
    color: #666;
    margin-bottom: 5px;
}

.tf-regime {
    font-size: 14px;
    font-weight: 600;
}

.alert-feed {
    max-height: 200px;
    overflow-y: auto;
    background: white;
    border-radius: 4px;
    padding: 10px;
}

.alert-item {
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

.alert-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}

.alert-time {
    font-size: 12px;
    color: #666;
}

.alert-severity {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 3px;
}

.alert-info {
    background: #e3f2fd;
    color: #1976d2;
}

.alert-warning {
    background: #fff3e0;
    color: #f57c00;
}

.alert-critical {
    background: #ffebee;
    color: #c62828;
}

.alert-message {
    font-size: 13px;
    color: #333;
}
"""
